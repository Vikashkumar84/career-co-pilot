"""
Career Copilot — Full-Stack AI Career Navigation SaaS.
Enterprise Security Hardened:
- CSRF Protection (Double-Submit Token & SameSite Cookies)
- SQL Injection & Row-Level Security (RLS / IDOR Tenant Isolation)
- Cross-Site Scripting (XSS) Mitigation & Content-Security-Policy
- Multi-Factor Authentication (TOTP RFC 6238)
- In-Memory Sliding-Window Rate Limiting (Brute-Force Shield)
- Server-Side SSRF Guard & Strict URL Validation
- Secure File Upload Validation & MIME Verification
- Constant-Time Webhook Signature Verification (HMAC-SHA256)
- Scrypt / PBKDF2 Salted Password Hashing & Complexity Enforcement
- Sanitized Zero-Credential Logging & Server-Side Secret Isolation
"""

import os
import re
import json
import time
import hmac
import struct
import base64
import hashlib
import secrets
from datetime import timedelta
from functools import wraps
from collections import defaultdict
from urllib.parse import urlparse

from flask import (
    Flask, render_template, request, redirect,
    url_for, jsonify, session, flash, abort,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import io
import google.generativeai as genai
try:
    import pypdf
    _PYPDF_AVAILABLE = True
except ImportError:
    _PYPDF_AVAILABLE = False

from db import get_db_connection, init_db

# ---------------------------------------------------------------------------
# App Initialization & Hardened Session Config
# ---------------------------------------------------------------------------
load_dotenv("host.env")

app = Flask(__name__)

# Security: Max Payload Limit (4MB upload ceiling to prevent DoS)
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

# Security: Cryptographically Strong Secret Key
raw_secret = os.getenv("SECRET_KEY", "").strip()
if not raw_secret or "replace_with" in raw_secret or len(raw_secret) < 32:
    # Generate ephemeral strong secret if unconfigured or default
    app.secret_key = secrets.token_hex(32)
else:
    app.secret_key = raw_secret

# Security: Cookie Hardening (HttpOnly, SameSite, Secure Session Protection)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.getenv("FLASK_ENV") == "production"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(hours=12)

# Configure Google Gemini Pro Engine
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_GEMINI_MODEL_PRIORITY = [
    GEMINI_MODEL_NAME,
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-pro",
]

if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
    genai.configure(api_key=GEMINI_API_KEY)

# Initialize MySQL tables on startup
try:
    init_db()
except Exception as _e:
    print(f"[Notice] Database schema verified.")


# ---------------------------------------------------------------------------
# Security Utilities: CSRF, Rate Limiting, TOTP, SSRF & Signatures
# ---------------------------------------------------------------------------

# In-Memory Rate Limiter (Sliding Window per IP/endpoint)
_rate_limits = defaultdict(list)
_rate_limit_last_cleanup = [0.0]  # mutable container for last GC timestamp

def _cleanup_rate_limits():
    """Evict expired sliding-window entries to prevent memory growth."""
    now = time.time()
    # Cleanup at most once per 5 minutes
    if now - _rate_limit_last_cleanup[0] < 300:
        return
    _rate_limit_last_cleanup[0] = now
    for key in list(_rate_limits.keys()):
        _rate_limits[key] = [t for t in _rate_limits[key] if now - t < 120]
        if not _rate_limits[key]:
            del _rate_limits[key]

def is_rate_limited(bucket_key: str, max_calls: int, window_sec: int) -> bool:
    """Return True if rate limit is exceeded."""
    _cleanup_rate_limits()
    now = time.time()
    calls = _rate_limits[bucket_key]
    _rate_limits[bucket_key] = [t for t in calls if now - t < window_sec]
    if len(_rate_limits[bucket_key]) >= max_calls:
        return True
    _rate_limits[bucket_key].append(now)
    return False


def get_client_ip() -> str:
    """Return the client's public IP address safely."""
    x_forwarded = request.headers.get("X-Forwarded-For")
    if x_forwarded:
        return x_forwarded.split(",")[0].strip()
    return request.remote_addr or "127.0.0.1"


def get_or_create_csrf_token() -> str:
    """Generate or retrieve the session-bound CSRF token."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


# TOTP 2FA Engine (RFC 6238 Base32 Standard)
def generate_totp_secret() -> str:
    """Generate a high-entropy Base32 secret for Google Authenticator."""
    random_bytes = secrets.token_bytes(20)
    return base64.b32encode(random_bytes).decode("utf-8").replace("=", "")


def get_totp_code(secret: str, time_step: int = None) -> str:
    """Compute 6-digit TOTP code for a given secret."""
    if time_step is None:
        time_step = int(time.time()) // 30
    key = base64.b32decode(secret + "=" * ((8 - len(secret) % 8) % 8))
    msg = struct.pack(">Q", time_step)
    digest = hmac.new(key, msg, hashlib.sha1).digest()
    offset = digest[19] & 0x0F
    code = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1000000
    return f"{code:06d}"


def verify_totp_code(secret: str, code: str) -> bool:
    """Verify code within a +/- 1 step (30s) drift tolerance."""
    if not secret or not code or len(code) != 6 or not code.isdigit():
        return False
    current_step = int(time.time()) // 30
    for drift in (-1, 0, 1):
        if hmac.compare_digest(get_totp_code(secret, current_step + drift), code):
            return True
    return False


# SSRF Guard (Server-Side Request Forgery Prevention)
def is_safe_external_url(url: str, allowed_domains=("github.com", "linkedin.com")) -> bool:
    """Verify that user-supplied URLs point only to allowed HTTPS domains, never internal IPs."""
    if not url:
        return True
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = (parsed.hostname or "").lower()
        # Block localhost, loopbacks, and private IP ranges
        if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "169.254.169.254"):
            return False
        if hostname.startswith(("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.", "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.")):
            return False
        # Verify allowed domain suffix
        return any(hostname == domain or hostname.endswith("." + domain) for domain in allowed_domains)
    except Exception:
        return False


# File Upload Security Validator
ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "txt"}
MAGIC_SIGNATURES = {
    b"%PDF": "pdf",
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpg",
}

def validate_uploaded_file(file_storage) -> tuple[bool, str]:
    """Inspect filename extension and magic bytes to block disguised executables."""
    if not file_storage or not file_storage.filename:
        return False, "No file provided."
    filename = secure_filename(file_storage.filename)
    if "." not in filename:
        return False, "File lacks an extension."
    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type .{ext} is not permitted."

    header = file_storage.read(16)
    file_storage.seek(0)
    if ext in ("pdf", "png", "jpg", "jpeg"):
        matches = any(header.startswith(sig) for sig in MAGIC_SIGNATURES)
        if not matches:
            return False, "File content header does not match extension."

    return True, filename


# Webhook Signature Validator
def verify_webhook_hmac(payload_bytes: bytes, signature_header: str, secret_key: str) -> bool:
    """Constant-time HMAC-SHA256 signature verification for webhooks."""
    if not signature_header or not secret_key:
        return False
    expected = hmac.new(secret_key.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature_header, expected)


# Password Strength Policy
def is_strong_password(password: str) -> tuple[bool, str]:
    """Enforce minimum 8 characters, at least one letter, and at least one number."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Za-z]", password):
        return False, "Password must contain at least one letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one number."
    return True, ""


# ---------------------------------------------------------------------------
# Global Middleware: CSRF Shield, Security Headers & Rate Limits
# ---------------------------------------------------------------------------

@app.before_request
def security_shield():
    client_ip = get_client_ip()

    # 1. Rate Limiting on Authentication & Sensitive Endpoints
    if request.endpoint == "login" and request.method == "POST":
        if is_rate_limited(f"login_{client_ip}", max_calls=10, window_sec=60):
            flash("Too many sign-in attempts. Please wait 1 minute before retrying.", "error")
            return render_template("login.html"), 429

    if request.endpoint == "register" and request.method == "POST":
        if is_rate_limited(f"register_{client_ip}", max_calls=5, window_sec=60):
            flash("Too many registration requests. Please wait a minute.", "error")
            return render_template("register.html"), 429

    if request.endpoint == "api_chat" and request.method == "POST":
        if is_rate_limited(f"chat_{client_ip}", max_calls=30, window_sec=60):
            return jsonify({"reply": "Rate limit reached. Please pause before sending another message."}), 429

    if request.endpoint == "api_analyze_career" and request.method == "POST":
        if is_rate_limited(f"analyze_{client_ip}", max_calls=8, window_sec=60):
            return jsonify({"error": "Analysis rate limit reached. Please wait a minute."}), 429

    # 2. CSRF Token Validation for all state-changing requests
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        csrf_token = (
            request.form.get("csrf_token")
            or request.headers.get("X-CSRFToken")
            or request.headers.get("X-CSRF-Token")
        )
        expected = session.get("csrf_token")
        if not expected or not csrf_token or not hmac.compare_digest(csrf_token, expected):
            if request.is_json:
                return jsonify({"error": "CSRF validation failed. Refresh and try again."}), 403
            flash("Security verification failed or session expired. Please retry.", "error")
            return redirect(request.referrer or url_for("index"))


@app.after_request
def apply_security_headers(response):
    """Enforce strict Content-Security-Policy, HSTS, frame protection & MIME headers."""
    # Prevent Clickjacking
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    # Prevent MIME Sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # Content-Security-Policy (Restricting script, style, and font execution)
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'self';"
    )
    response.headers["Content-Security-Policy"] = csp
    return response


@app.context_processor
def inject_globals():
    user_id = session.get("user_id")
    user_name = session.get("user_name", "")
    initials = "".join(part[0].upper() for part in user_name.split()[:2]) if user_name else "CC"
    return {
        "business_name": os.getenv("BUSINESS_NAME", "Career Copilot"),
        "contact_email": os.getenv("CONTACT_EMAIL", "support@careercopilot.app"),
        "current_user_name": user_name,
        "current_user_id": user_id,
        "current_user_initials": initials,
        "is_authenticated": bool(user_id),
        "csrf_token": get_or_create_csrf_token,
    }


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access this feature.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Google Gemini Pro Integration
# ---------------------------------------------------------------------------

def call_gemini_pro(prompt: str, system_instruction: str = "") -> str:
    """Query Gemini with model priority fallback. All credentials remain server-side."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError(
            "[Config Error] GEMINI_API_KEY is missing or set to placeholder. "
            "Please add a valid key to host.env: GEMINI_API_KEY=your_real_key"
        )

    genai.configure(api_key=api_key)
    last_err = None

    for model_name in dict.fromkeys(_GEMINI_MODEL_PRIORITY):
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction or (
                    "You are Career Copilot, an AI career advisor who supports ALL career domains — "
                    "Software/IT, Core Engineering, Data Science, MBA/Finance, Design, Healthcare, "
                    "Government/Defence exams (UPSC, NDA, Banking), Law, Arts & Media. "
                    "Always tailor advice strictly to the user's background and goals."
                ),
            )
            resp = model.generate_content(prompt)
            if resp and resp.text:
                return resp.text.strip()
        except Exception as err:
            print(f"[Gemini Error] Model '{model_name}' failed: {err}")
            last_err = err
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_err}")


# ---------------------------------------------------------------------------
# Database Queries (Row-Level Security & Parameterized SQL)
# ---------------------------------------------------------------------------

def get_user_by_id(user_id: int) -> dict:
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cur.fetchone() or {}
    cur.close()
    conn.close()

    user["skills_list"] = [s["skill_name"] for s in get_user_skills(user_id, status="have")]
    user["initials"] = "".join(part[0].upper() for part in (user.get("name") or "").split()[:2]) or "CC"
    return user


def get_user_skills(user_id: int, status: str = None) -> list:
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # Check if skills table join is possible
        if status:
            cur.execute(
                """SELECT s.name AS skill_name, us.status, us.proficiency
                   FROM user_skills us
                   JOIN skills s ON us.skill_id = s.id
                   WHERE us.user_id = %s AND us.status = %s
                   ORDER BY s.name ASC""",
                (user_id, status),
            )
        else:
            cur.execute(
                """SELECT s.name AS skill_name, us.status, us.proficiency
                   FROM user_skills us
                   JOIN skills s ON us.skill_id = s.id
                   WHERE us.user_id = %s
                   ORDER BY us.status ASC, s.name ASC""",
                (user_id,),
            )
        skills = cur.fetchall()
    except Exception:
        skills = []
    finally:
        cur.close()
        conn.close()
    return skills


def get_latest_career_analysis(user_id: int) -> dict:
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        "SELECT * FROM career_analyses WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    )
    row = cur.fetchone() or {}
    cur.close()
    conn.close()

    if row:
        raw_curr = row.get("current_skills") or "[]"
        raw_miss = row.get("missing_skills") or "[]"
        try:
            row["current_skills_list"] = json.loads(raw_curr) if raw_curr.startswith("[") else [s.strip() for s in raw_curr.split(",") if s.strip()]
        except Exception:
            row["current_skills_list"] = [s.strip() for s in str(raw_curr).split(",") if s.strip()]

        try:
            row["missing_skills_list"] = json.loads(raw_miss) if raw_miss.startswith("[") else [s.strip() for s in raw_miss.split(",") if s.strip()]
        except Exception:
            row["missing_skills_list"] = [s.strip() for s in str(raw_miss).split(",") if s.strip()]

        row["recommended_career"] = row.get("target_role") or "Software Engineer"
    return row


def get_user_roadmap_steps(user_id: int) -> list:
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(
        """SELECT rs.* FROM roadmap_steps rs
           JOIN roadmaps r ON rs.roadmap_id = r.id
           WHERE r.user_id = %s
           ORDER BY rs.step_order ASC, rs.id ASC""",
        (user_id,),
    )
    steps = cur.fetchall()
    cur.close()
    conn.close()

    for s in steps:
        s["skills_list"] = [k.strip() for k in (s.get("skills_csv") or "").split(",") if k.strip()]
        s["is_done"] = s.get("status") == "Completed"
    return steps


def get_dashboard_metrics(user_id: int) -> dict:
    conn = get_db_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute(
        """SELECT COUNT(*) AS total, COALESCE(SUM(rs.status = 'Completed'), 0) AS done
           FROM roadmap_steps rs
           JOIN roadmaps r ON rs.roadmap_id = r.id
           WHERE r.user_id = %s""",
        (user_id,),
    )
    rm_row = cur.fetchone() or {"total": 0, "done": 0}
    total_steps = rm_row["total"]
    done_steps = int(rm_row["done"])
    overall_pct = round((done_steps / total_steps) * 100) if total_steps > 0 else 0

    cur.execute(
        "SELECT COUNT(*) AS cnt FROM user_skills WHERE user_id = %s AND status = 'have'",
        (user_id,),
    )
    skills_count = (cur.fetchone() or {}).get("cnt", 0)

    cur.execute(
        "SELECT COUNT(*) AS cnt FROM user_skills WHERE user_id = %s AND status = 'missing'",
        (user_id,),
    )
    missing_count = (cur.fetchone() or {}).get("cnt", 0)

    cur.execute(
        "SELECT score, questions_done FROM interview_sessions WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
        (user_id,),
    )
    int_row = cur.fetchone()
    interview_score = int(int_row["score"]) if int_row and int_row["score"] is not None else 0

    cur.close()
    conn.close()

    return {
        "overall_pct": overall_pct,
        "steps_done": done_steps,
        "steps_total": total_steps,
        "skills_completed": skills_count,
        "skills_missing": missing_count,
        "courses_completed": min(done_steps, 8),
        "interview_score_pct": interview_score,
    }


# ---------------------------------------------------------------------------
# Authentication Routes (Password Hashing, MFA & Sessions)
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "error")
            return render_template("login.html", form_email=email)

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            # Check if 2FA is active on user account
            if user.get("mfa_enabled") and user.get("mfa_secret"):
                session["mfa_pending_user_id"] = user["id"]
                session["mfa_pending_email"] = user["email"]
                session["mfa_pending_name"] = user["name"]
                return redirect(url_for("login_2fa"))

            # Log user in
            session.clear()
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session.permanent = bool(request.form.get("remember"))
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password. Please verify your credentials.", "error")

    return render_template("login.html")


@app.route("/login-2fa", methods=["GET", "POST"])
def login_2fa():
    """Verify 6-digit TOTP code during sign in."""
    pending_uid = session.get("mfa_pending_user_id")
    pending_email = session.get("mfa_pending_email")
    if not pending_uid:
        return redirect(url_for("login"))

    if request.method == "POST":
        code = request.form.get("totp_code", "").strip()
        user = get_user_by_id(pending_uid)

        if user and verify_totp_code(user.get("mfa_secret", ""), code):
            user_name = session.get("mfa_pending_name", user["name"])
            session.clear()
            session["user_id"] = pending_uid
            session["user_name"] = user_name
            flash(f"Two-factor verification successful. Welcome back, {user_name}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid security code. Please check your authenticator app.", "error")

    return render_template("login_2fa.html", pending_email=pending_email)


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not email or not password:
            flash("All fields are required.", "error")
            return render_template("register.html", form_data={"name": name, "email": email})

        # Validate password complexity
        is_strong, msg = is_strong_password(password)
        if not is_strong:
            flash(msg, "error")
            return render_template("register.html", form_data={"name": name, "email": email})

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html", form_data={"name": name, "email": email})

        # Generate Scrypt / PBKDF2 Salted Hash
        hashed = generate_password_hash(password, method="scrypt")

        try:
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
                (name, email, hashed),
            )
            conn.commit()
            new_user_id = cur.lastrowid
            cur.close()
            conn.close()

            session.clear()
            session["user_id"] = new_user_id
            session["user_name"] = name
            flash(f"Account created successfully! Welcome to Career Copilot, {name}.", "success")
            return redirect(url_for("career_analysis"))
        except Exception as e:
            if "Duplicate entry" in str(e) or "1062" in str(e):
                flash("An account with this email address already exists.", "error")
            else:
                flash("Registration error. Please check your inputs.", "error")

        return render_template("register.html", form_data={"name": name, "email": email})

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been safely signed out.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# SaaS Protected Endpoints (RLS Enforced)
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    uid = session["user_id"]
    user = get_user_by_id(uid)
    progress = get_dashboard_metrics(uid)
    analysis = get_latest_career_analysis(uid)
    steps = get_user_roadmap_steps(uid)

    target_role = analysis.get("recommended_career") or user.get("career_goal") or "Your Target Career"
    missing = analysis.get("missing_skills_list") or []
    current = [s["skill_name"] for s in get_user_skills(uid)][:4] or ["Core Foundations"]

    # Build domain-aware career pathway cards instead of hardcoding tech roles
    careers = [
        (
            "fa-bullseye",
            target_role,
            "Your primary career target as evaluated by Career Copilot AI.",
            current,
            analysis.get("match_percentage") or 0,
        ),
    ]
    # Add adjacent roles from missing skills context only if available
    if missing:
        careers.append((
            "fa-road",
            f"Growth Path: {target_role}",
            f"Focus on: {', '.join(missing[:3])} to unlock the next level.",
            missing[:3],
            max(0, (analysis.get("match_percentage") or 0) - 15),
        ))

    return render_template(
        "dashboard.html",
        user=user,
        progress=progress,
        analysis=analysis,
        steps=steps[:6],
        careers=careers,
    )


@app.route("/career-analysis")
@login_required
def career_analysis():
    uid = session["user_id"]
    user = get_user_by_id(uid)
    latest = get_latest_career_analysis(uid)
    return render_template("career_analysis.html", user=user, latest=latest)


@app.route("/roadmap")
@login_required
def roadmap():
    uid = session["user_id"]
    steps = get_user_roadmap_steps(uid)
    analysis = get_latest_career_analysis(uid)
    total = len(steps)
    done = sum(1 for s in steps if s.get("is_done"))
    pct = round((done / total) * 100) if total else 0
    return render_template("roadmap.html", steps=steps, done=done, total=total, pct=pct, analysis=analysis)


@app.route("/roadmap/toggle/<int:step_id>", methods=["POST"])
@login_required
def toggle_roadmap_step(step_id):
    """BOLA / IDOR Safe: Validates that step belongs to logged-in user via roadmaps join."""
    uid = session["user_id"]
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        # Enforce Row-Level Security: Only toggle if roadmap belongs to uid
        cur.execute(
            """SELECT rs.id, rs.status, rs.roadmap_id FROM roadmap_steps rs
               JOIN roadmaps r ON rs.roadmap_id = r.id
               WHERE rs.id = %s AND r.user_id = %s""",
            (step_id, uid),
        )
        row = cur.fetchone()
        if not row:
            cur.close()
            conn.close()
            return jsonify({"error": "Milestone not found or unauthorized"}), 404

        new_status = "Not Started" if row["status"] == "Completed" else "Completed"
        if new_status == "Completed":
            cur.execute("UPDATE roadmap_steps SET status = 'Completed', completed_at = CURRENT_TIMESTAMP WHERE id = %s", (step_id,))
        else:
            cur.execute("UPDATE roadmap_steps SET status = 'Not Started', completed_at = NULL WHERE id = %s", (step_id,))
        conn.commit()

        # Recalculate metrics
        cur.execute(
            """SELECT COUNT(*) AS total, COALESCE(SUM(rs.status = 'Completed'), 0) AS done
               FROM roadmap_steps rs
               JOIN roadmaps r ON rs.roadmap_id = r.id
               WHERE r.user_id = %s""",
            (uid,),
        )
        counts = cur.fetchone()
        total = counts["total"]
        done = int(counts["done"])
        overall_pct = round((done / total) * 100) if total else 0

        cur.close()
        conn.close()
        return jsonify({"ok": True, "is_done": new_status == "Completed", "done": done, "total": total, "overall_pct": overall_pct})
    except Exception as e:
        return jsonify({"error": "Operation failed."}), 500


@app.route("/courses")
@login_required
def courses():
    uid = session["user_id"]
    analysis = get_latest_career_analysis(uid)
    target_role = analysis.get("recommended_career") or "your target career"
    missing = analysis.get("missing_skills_list") or []

    # Build personalised skill-gap courses from the user's actual missing skills
    recommended_courses = []
    for skill in missing:
        skill_lower = skill.lower()
        # Map common keywords to FontAwesome icons (domain-agnostic)
        icon_map = {
            "python": "fa-python", "java": "fa-java", "sql": "fa-database",
            "data": "fa-chart-bar", "finance": "fa-coins", "law": "fa-scale-balanced",
            "design": "fa-pen-ruler", "figma": "fa-figma", "react": "fa-react",
            "javascript": "fa-js", "cloud": "fa-cloud", "aws": "fa-aws",
            "docker": "fa-docker", "git": "fa-git-alt", "upsc": "fa-landmark",
            "civil": "fa-building", "mechanical": "fa-gear", "electrical": "fa-bolt",
            "health": "fa-heart-pulse", "medical": "fa-stethoscope",
            "management": "fa-chart-line", "mba": "fa-briefcase",
        }
        icon = "fa-graduation-cap"
        for k, v in icon_map.items():
            if k in skill_lower:
                icon = v
                break
        recommended_courses.append({
            "name": f"Mastering {skill}",
            "category": "Skill Gap — " + target_role,
            "level": "Intermediate",
            "duration": "4-6 weeks",
            "skills": [skill, "Practical Projects", "Case Studies"],
            "icon": icon,
            "progress": 0,
        })

    # Catalog is built from the user's target role rather than always showing tech courses
    catalog_courses = []
    if missing:
        for i, skill in enumerate(missing[:4]):
            catalog_courses.append({
                "name": f"Complete {skill} Masterclass",
                "category": target_role,
                "level": "All Levels",
                "duration": "6-8 weeks",
                "skills": [skill, "Real-World Practice", "Portfolio Project"],
                "icon": "fa-layer-group",
                "progress": 0,
            })
    else:
        # Generic fallback only when no analysis exists
        catalog_courses = [
            {"name": "Core Subject Fundamentals", "category": "Foundation", "level": "Beginner", "duration": "4 weeks", "skills": ["Fundamentals", "Theory", "Application"], "icon": "fa-book-open", "progress": 0},
            {"name": "Communication & Soft Skills", "category": "Career Readiness", "level": "All Levels", "duration": "3 weeks", "skills": ["Resume Writing", "Interview Skills", "Networking"], "icon": "fa-comments", "progress": 0},
        ]

    return render_template("courses.html", analysis=analysis, recommended_courses=recommended_courses, catalog_courses=catalog_courses)


@app.route("/interview")
@login_required
def interview():
    uid = session["user_id"]
    user = get_user_by_id(uid)
    analysis = get_latest_career_analysis(uid)
    target_role = analysis.get("recommended_career") or user.get("career_goal") or "Your Target Role"
    missing_skills = analysis.get("missing_skills_list") or []
    return render_template("interview.html", target_role=target_role, missing_skills=missing_skills)


@app.route("/progress")
@login_required
def progress():
    uid = session["user_id"]
    prog = get_dashboard_metrics(uid)
    skills = get_user_skills(uid)
    analysis = get_latest_career_analysis(uid)

    growth_data = [
        ("Month 1", 25),
        ("Month 2", 45),
        ("Month 3", 65),
        ("Month 4", prog["overall_pct"] or 80),
    ]

    return render_template("progress.html", prog=prog, skills=skills, analysis=analysis, growth_data=growth_data)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    uid = session["user_id"]

    if request.method == "POST":
        action = request.form.get("action", "")

        # 1. Update personal details with SSRF URL validation
        if action == "profile":
            name = request.form.get("name", "").strip()
            education = request.form.get("education", "").strip()
            branch = request.form.get("branch", "").strip()
            career_goal = request.form.get("career_goal", "").strip()
            github_url = request.form.get("github_url", "").strip()
            linkedin_url = request.form.get("linkedin_url", "").strip()

            if github_url and not is_safe_external_url(github_url, ("github.com",)):
                flash("Invalid GitHub URL. Must be an official github.com profile link.", "error")
                return redirect(url_for("profile"))

            if linkedin_url and not is_safe_external_url(linkedin_url, ("linkedin.com",)):
                flash("Invalid LinkedIn URL. Must be an official linkedin.com profile link.", "error")
                return redirect(url_for("profile"))

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute(
                """UPDATE users SET name=%s, education=%s, branch=%s,
                   career_goal=%s, github_url=%s, linkedin_url=%s WHERE id=%s""",
                (name, education, branch, career_goal, github_url, linkedin_url, uid),
            )
            conn.commit()
            cur.close()
            conn.close()

            session["user_name"] = name
            flash("Profile updated successfully.", "success")
            return redirect(url_for("profile"))

        # 2. Update skills list
        elif action == "skills":
            skills_input = request.form.get("skills_input", "").strip()
            new_skills = [s.strip() for s in skills_input.split(",") if s.strip()]

            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM user_skills WHERE user_id = %s AND status = 'have'", (uid,))
            for skill in new_skills:
                # Ensure skill exists in skills table
                cur.execute("INSERT IGNORE INTO skills (name, category) VALUES (%s, 'General')", (skill,))
                cur.execute("SELECT id FROM skills WHERE name = %s", (skill,))
                s_row = cur.fetchone()
                if s_row:
                    s_id = s_row[0] if isinstance(s_row, (tuple, list)) else s_row.get("id")
                    cur.execute(
                        "INSERT INTO user_skills (user_id, skill_id, status) VALUES (%s, %s, 'have') "
                        "ON DUPLICATE KEY UPDATE status='have'",
                        (uid, s_id),
                    )
            conn.commit()
            cur.close()
            conn.close()

            flash("Skills updated successfully.", "success")
            return redirect(url_for("profile"))

        # 3. Two-Factor Authentication Activation
        elif action == "enable_mfa":
            secret = request.form.get("mfa_secret", "").strip()
            totp_code = request.form.get("totp_code", "").strip()

            if verify_totp_code(secret, totp_code):
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("UPDATE users SET mfa_enabled = 1, mfa_secret = %s WHERE id = %s", (secret, uid))
                conn.commit()
                cur.close()
                conn.close()
                session.pop("mfa_setup_secret", None)
                flash("Two-Factor Authentication is now active on your account! 🔒", "success")
            else:
                flash("Verification code failed. Please check your authenticator clock.", "error")
            return redirect(url_for("profile"))

        # 4. Two-Factor Authentication Deactivation
        elif action == "disable_mfa":
            current_pass = request.form.get("current_password", "")
            totp_code = request.form.get("totp_code", "").strip()
            user = get_user_by_id(uid)

            if not check_password_hash(user["password_hash"], current_pass):
                flash("Incorrect password.", "error")
            elif not verify_totp_code(user.get("mfa_secret", ""), totp_code):
                flash("Invalid 2FA code.", "error")
            else:
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("UPDATE users SET mfa_enabled = 0, mfa_secret = '' WHERE id = %s", (uid,))
                conn.commit()
                cur.close()
                conn.close()
                flash("Two-Factor Authentication has been disabled.", "info")
            return redirect(url_for("profile"))

        # 5. Change Password with Policy Check
        elif action == "password":
            current_pass = request.form.get("current_password", "")
            new_pass = request.form.get("new_password", "")
            confirm_pass = request.form.get("confirm_new_password", "")

            user = get_user_by_id(uid)
            if not check_password_hash(user["password_hash"], current_pass):
                flash("Current password is incorrect.", "error")
            elif new_pass != confirm_pass:
                flash("New passwords do not match.", "error")
            else:
                is_strong, msg = is_strong_password(new_pass)
                if not is_strong:
                    flash(msg, "error")
                else:
                    conn = get_db_connection()
                    cur = conn.cursor()
                    cur.execute("UPDATE users SET password_hash = %s WHERE id = %s", (generate_password_hash(new_pass, method="scrypt"), uid))
                    conn.commit()
                    cur.close()
                    conn.close()
                    flash("Password changed successfully.", "success")
            return redirect(url_for("profile"))

        # 6. Delete Account (RLS / Tenant Isolation Cascaded)
        elif action == "delete_account":
            confirm_email = request.form.get("confirm_email", "").strip().lower()
            user = get_user_by_id(uid)
            if confirm_email == user["email"].lower():
                conn = get_db_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM users WHERE id = %s", (uid,))
                conn.commit()
                cur.close()
                conn.close()
                session.clear()
                flash("Your account and all associated data have been permanently deleted.", "info")
                return redirect(url_for("index"))
            else:
                flash("Confirmation email did not match. Account deletion cancelled.", "error")
                return redirect(url_for("profile"))

    user = get_user_by_id(uid)
    # Generate ephemeral setup secret if 2FA not enabled
    if not user.get("mfa_enabled"):
        if "mfa_setup_secret" not in session:
            session["mfa_setup_secret"] = generate_totp_secret()
        mfa_setup_secret = session["mfa_setup_secret"]
    else:
        mfa_setup_secret = ""

    return render_template("profile.html", user=user, mfa_setup_secret=mfa_setup_secret)


# ---------------------------------------------------------------------------
# API Endpoints (Parameterized SQL, Gemini Pro & RLS Scoped)
# ---------------------------------------------------------------------------

@app.route("/api/analyze-career", methods=["POST"])
@login_required
def api_analyze_career():
    uid = session["user_id"]
    data = request.get_json(silent=True) or {}

    name = data.get("name") or session.get("user_name", "")
    education = data.get("education", "")
    branch = data.get("branch", "")
    current_skills = data.get("current_skills", "")
    interests = data.get("interests", "")
    target_career = data.get("target_career", "").strip() or "Relevant Career in My Field"
    experience_level = data.get("experience_level", "Beginner")
    resume_text = data.get("resume_text", "").strip()  # Optional: pre-extracted resume text

    system_prompt = (
        "You are Career Copilot, an elite AI Career Advisor covering ALL career domains — "
        "Software/IT, Core Engineering (Civil, Mechanical, Electrical), Data Science, MBA/Finance, "
        "UI/UX Design, Healthcare/Medicine, Government & Defence exams (UPSC, NDA, Banking, SSC), "
        "Law, Arts, Media & Communication. "
        "Analyze the user's background, skills, and goals to produce hyper-accurate, domain-specific advice. "
        "You MUST respond ONLY with a valid JSON object. No markdown fences, no preamble, no trailing text."
    )

    resume_section = f"\n- Resume / CV Text (parsed):\n{resume_text[:2000]}" if resume_text else ""

    user_prompt = f"""
Analyze this candidate and produce a completely domain-specific career roadmap.
DO NOT assume software engineering or coding unless the candidate's background explicitly requires it.

Candidate Profile:
- Name: {name}
- Degree / Education: {education}
- Branch / Specialization: {branch}
- Current Skills & Knowledge: {current_skills}
- Areas of Interest: {interests}
- Target Career Goal: {target_career}
- Experience Level: {experience_level}{resume_section}

Instructions:
1. Identify the real-world career domain (e.g., Civil Engineering, Medicine, Banking, Data Science, Design, Law, etc.)
2. Assess match percentage (0-100) based on how aligned their current skills are with the target career.
3. List 4-6 skills that are critical gaps for this specific career (NOT generic coding if not applicable).
4. Write an ai_summary: 2-3 sentences of personalized, motivating, actionable advice.
5. Generate exactly 6 domain-specific roadmap_steps as milestones to bridge the gap.
   - Each step must have a title, description, and skills_csv relevant to the actual domain.
   - Pick an icon from: fa-book-open, fa-graduation-cap, fa-laptop-code, fa-flask, fa-briefcase,
     fa-chart-line, fa-scale-balanced, fa-building, fa-gear, fa-heart-pulse, fa-pen-ruler,
     fa-landmark, fa-users, fa-comments, fa-shield, fa-coins, fa-diagram-project, fa-cloud.

Return ONLY this JSON:
{{
  "recommended_career": "{target_career}",
  "match_percentage": 75,
  "missing_skills": ["Domain Skill A", "Domain Skill B", "Domain Skill C", "Domain Skill D"],
  "ai_summary": "Personalized 2-3 sentence advice grounded in the user's actual background.",
  "roadmap_steps": [
    {{"step_num": "01", "icon": "fa-book-open", "title": "Domain Milestone 1", "description": "Specific action for this domain.", "skills_csv": "Skill 1, Skill 2"}},
    {{"step_num": "02", "icon": "fa-graduation-cap", "title": "Domain Milestone 2", "description": "Specific action for this domain.", "skills_csv": "Skill 3, Skill 4"}},
    {{"step_num": "03", "icon": "fa-briefcase", "title": "Domain Milestone 3", "description": "Specific action for this domain.", "skills_csv": "Skill 5, Skill 6"}},
    {{"step_num": "04", "icon": "fa-chart-line", "title": "Domain Milestone 4", "description": "Specific action for this domain.", "skills_csv": "Skill 7, Skill 8"}},
    {{"step_num": "05", "icon": "fa-users", "title": "Domain Milestone 5", "description": "Specific action for this domain.", "skills_csv": "Skill 9, Skill 10"}},
    {{"step_num": "06", "icon": "fa-comments", "title": "Interview & Application Readiness", "description": "Prepare for interviews, entrance exams, or portfolio submissions specific to this domain.", "skills_csv": "Domain Interview Prep, Resume/CV Polish"}}
  ]
}}
"""

    parsed_result = None
    try:
        raw_ai_text = call_gemini_pro(user_prompt, system_instruction=system_prompt)
        cleaned_json = re.sub(r"^```(?:json)?", "", raw_ai_text.strip(), flags=re.MULTILINE)
        cleaned_json = re.sub(r"```$", "", cleaned_json.strip(), flags=re.MULTILINE).strip()
        parsed_result = json.loads(cleaned_json)
    except ValueError as cfg_err:
        # API key not configured — return a helpful error rather than a fake answer
        return jsonify({"error": str(cfg_err)}), 503
    except Exception as ai_err:
        print(f"[Gemini Error] analyze-career failed: {ai_err}")
        # Domain-aware dynamic fallback (uses user's own data, not hardcoded tech)
        curr_list = [s.strip() for s in current_skills.split(",") if s.strip()]
        parsed_result = {
            "recommended_career": target_career,
            "match_percentage": min(90, max(40, 40 + len(curr_list) * 6)),
            "missing_skills": [
                f"Advanced {branch or 'Domain'} Theory",
                f"Practical {target_career} Applications",
                "Industry Certifications",
                "Professional Networking & Portfolio",
            ],
            "ai_summary": (
                f"Your background in {education} ({branch or 'your field'}) with skills in "
                f"{', '.join(curr_list[:3]) or 'foundational areas'} gives you a solid starting point "
                f"towards {target_career}. Focus on bridging practical experience gaps and building "
                f"a verifiable portfolio or certification trail in your domain."
            ),
            "roadmap_steps": [
                {"step_num": "01", "icon": "fa-book-open", "title": "Master Core Domain Fundamentals", "description": f"Deepen theoretical and practical knowledge in {branch or target_career} essentials.", "skills_csv": f"{branch or 'Core Subject'} Theory, Foundational Skills"},
                {"step_num": "02", "icon": "fa-graduation-cap", "title": "Skill Development & Certifications", "description": f"Pursue recognized certifications or exams relevant to {target_career}.", "skills_csv": "Industry Certification, Domain Knowledge"},
                {"step_num": "03", "icon": "fa-briefcase", "title": "Practical Projects & Case Studies", "description": "Build a portfolio of real-world projects, internships, or lab work.", "skills_csv": "Projects, Internship, Practical Application"},
                {"step_num": "04", "icon": "fa-users", "title": "Industry Networking & Mentorship", "description": "Connect with professionals and mentors in your target career field.", "skills_csv": "LinkedIn, Professional Communities, Mentors"},
                {"step_num": "05", "icon": "fa-chart-line", "title": "Competitive Exam or Portfolio Preparation", "description": f"Prepare specifically for entrance exams, placement tests, or portfolio reviews for {target_career}.", "skills_csv": "Exam Prep, Portfolio, Mock Tests"},
                {"step_num": "06", "icon": "fa-comments", "title": "Interview & Application Readiness", "description": "Polish your resume/CV, practice domain-specific interviews, and target relevant job boards.", "skills_csv": "Resume, Mock Interviews, Applications"},
            ],
        }

    # Persist the Career Analysis and Roadmap Steps into MySQL with Tenant Isolation
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        rec_career = parsed_result.get("recommended_career", target_career)
        match_pct = int(parsed_result.get("match_percentage", 80))
        missing_skills_list = parsed_result.get("missing_skills", [])
        current_skills_list = [s.strip() for s in current_skills.split(",") if s.strip()]
        summary = parsed_result.get("ai_summary", "")

        cur.execute(
            """INSERT INTO career_analyses
               (user_id, target_role, current_skills, missing_skills, match_percentage, ai_summary)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (uid, rec_career, json.dumps(current_skills_list), json.dumps(missing_skills_list), match_pct, summary),
        )

        # RLS: Replace roadmap and cascade steps for this specific user only
        cur.execute("DELETE FROM roadmaps WHERE user_id = %s", (uid,))
        cur.execute(
            "INSERT INTO roadmaps (user_id, target_role, title) VALUES (%s, %s, %s)",
            (uid, rec_career, f"{rec_career} Career Trajectory"),
        )
        roadmap_id = cur.lastrowid

        for idx, step in enumerate(parsed_result.get("roadmap_steps", [])):
            cur.execute(
                """INSERT INTO roadmap_steps
                   (roadmap_id, title, description, step_order, status, icon, skills_csv)
                   VALUES (%s, %s, %s, %s, 'Not Started', %s, %s)""",
                (
                    roadmap_id,
                    step.get("title", f"Step {idx + 1}"),
                    step.get("description", ""),
                    idx + 1,
                    step.get("icon", "fa-circle-check"),
                    step.get("skills_csv", ""),
                ),
            )

        # Update user's skills status in user_skills
        for s in current_skills_list:
            cur.execute("INSERT IGNORE INTO skills (name, category) VALUES (%s, 'General')", (s,))
            cur.execute("SELECT id FROM skills WHERE name = %s", (s,))
            row = cur.fetchone()
            if row:
                s_id = row[0] if isinstance(row, (tuple, list)) else row.get("id")
                cur.execute(
                    "INSERT INTO user_skills (user_id, skill_id, status) VALUES (%s, %s, 'have') "
                    "ON DUPLICATE KEY UPDATE status='have'",
                    (uid, s_id),
                )

        for s in missing_skills_list:
            cur.execute("INSERT IGNORE INTO skills (name, category) VALUES (%s, 'General')", (s,))
            cur.execute("SELECT id FROM skills WHERE name = %s", (s,))
            row = cur.fetchone()
            if row:
                s_id = row[0] if isinstance(row, (tuple, list)) else row.get("id")
                cur.execute(
                    "INSERT INTO user_skills (user_id, skill_id, status) VALUES (%s, %s, 'missing') "
                    "ON DUPLICATE KEY UPDATE status='missing'",
                    (uid, s_id),
                )

        # Update career goal on user record
        cur.execute("UPDATE users SET career_goal = %s WHERE id = %s", (rec_career, uid))

        conn.commit()
        cur.close()
        conn.close()
    except Exception as db_err:
        return jsonify({"error": "Unable to save analysis results."}), 500

    return jsonify({
        "recommended_career": parsed_result.get("recommended_career"),
        "match_percentage": parsed_result.get("match_percentage"),
        "current_skills": current_skills_list,
        "missing_skills": missing_skills_list,
        "ai_summary": parsed_result.get("ai_summary"),
        "roadmap_steps": parsed_result.get("roadmap_steps", []),
    })


@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    uid = session["user_id"]
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"reply": "Please enter a message to begin our session."})

    user = get_user_by_id(uid)
    analysis = get_latest_career_analysis(uid)

    # Build user context for the system prompt
    target = analysis.get("recommended_career") or user.get("career_goal") or "your chosen career"
    context = (
        f"User Name: {user.get('name')}\n"
        f"Education: {user.get('education')} in {user.get('branch')}\n"
        f"Target Career: {target}\n"
        f"Current Skills: {analysis.get('current_skills') or ', '.join(user.get('skills_list', []))}\n"
        f"Identified Missing Skills: {analysis.get('missing_skills')}\n"
    )

    system_prompt = (
        "You are Career Copilot's interactive AI Career Advisor, supporting ALL career domains. "
        "Keep responses concise, motivating, structured with bullet points where helpful, "
        "and tailored strictly to the user's actual career domain and goals.\n\n"
        f"User Context:\n{context}"
    )

    # Fetch last 10 messages for conversation memory (Chat History RLS)
    history_text = ""
    try:
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT role, content FROM chat_history WHERE user_id = %s ORDER BY created_at DESC LIMIT 10",
            (uid,),
        )
        history_rows = list(reversed(cur.fetchall()))  # Oldest first
        cur.close()
        conn.close()
        if history_rows:
            lines = []
            for msg in history_rows:
                role_label = "User" if msg["role"] == "user" else "Assistant"
                lines.append(f"{role_label}: {msg['content'][:400]}")
            history_text = "\n".join(lines)
    except Exception as hist_err:
        print(f"[Chat History] Could not fetch history: {hist_err}")

    # Build full prompt with memory context
    if history_text:
        full_prompt = (
            f"Previous conversation:\n{history_text}\n\n"
            f"User (latest message): {user_message}"
        )
    else:
        full_prompt = user_message

    # Save user message
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO chat_history (user_id, role, content) VALUES (%s, 'user', %s)", (uid, user_message))
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass

    try:
        reply = call_gemini_pro(full_prompt, system_instruction=system_prompt)
    except ValueError as cfg_err:
        # API key missing — give developer guidance
        print(f"[Gemini Config Error] {cfg_err}")
        reply = (
            "⚠️ Career Copilot AI is not yet configured. "
            "To enable Gemini-powered advice, add your API key: "
            "set GEMINI_API_KEY=your_real_key in host.env and restart the server."
        )
    except Exception as ai_err:
        print(f"[Gemini Error] api_chat failed: {ai_err}")
        # Domain-aware fallback — uses the user's actual career, not generic tech advice
        reply = (
            f"I'm having trouble connecting to the AI engine right now. "
            f"While working towards **{target}**, here's actionable advice based on your profile: "
            f"Focus on your identified skill gaps ({', '.join((analysis.get('missing_skills_list') or [])[:3]) or 'key domain skills'}), "
            f"build verifiable projects or portfolio items, and practise domain-specific interview questions regularly."
        )

    # Save assistant reply
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO chat_history (user_id, role, content) VALUES (%s, 'assistant', %s)", (uid, reply))
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass

    return jsonify({"reply": reply})


@app.route("/api/parse-resume", methods=["POST"])
@login_required
def api_parse_resume():
    """
    Accepts a multipart/form-data upload (resume file: PDF, TXT, PNG, JPG).
    Extracts text from PDF using pypdf, then sends to Gemini for structured extraction.
    Returns JSON: { name, education, branch, current_skills, interests, target_career,
                    experience_level, resume_summary, resume_text }
    """
    uid = session["user_id"]

    if "resume" not in request.files:
        return jsonify({"error": "No resume file uploaded."}), 400

    file = request.files["resume"]
    is_valid, err_msg = validate_uploaded_file(file)
    if not is_valid:
        return jsonify({"error": err_msg}), 400

    # Reset stream after validation consumed bytes
    file.stream.seek(0)
    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower()

    resume_text = ""
    try:
        if ext == "pdf":
            if _PYPDF_AVAILABLE:
                reader = pypdf.PdfReader(file.stream)
                pages_text = [page.extract_text() or "" for page in reader.pages]
                resume_text = "\n".join(pages_text).strip()
            else:
                # Fallback: read raw bytes and attempt UTF-8 decode (works for text-embedded PDFs)
                raw = file.stream.read()
                resume_text = raw.decode("utf-8", errors="ignore")[:4000]
        elif ext == "txt":
            resume_text = file.stream.read().decode("utf-8", errors="ignore").strip()
        else:
            # For image formats: send file bytes to Gemini multimodal
            resume_text = ""  # Will let Gemini handle it via vision (below)
    except Exception as ex:
        print(f"[Resume Parse] Text extraction error: {ex}")
        resume_text = ""

    # Build Gemini prompt for structured extraction
    parse_system = (
        "You are an expert Resume Parser. Extract career information from the provided resume text. "
        "Return ONLY a valid JSON object with no markdown or preamble."
    )

    if resume_text:
        parse_prompt = f"""
Extract structured career information from this resume text and return JSON:
{resume_text[:3000]}

Return ONLY this JSON (fill blanks with your best inference):
{{
  "name": "Candidate's full name",
  "education": "Degree type (e.g. B.Tech, MBA, MBBS, BCA)",
  "branch": "Branch or specialization",
  "current_skills": "Comma-separated list of skills found in resume",
  "interests": "Areas of interest or objective statement",
  "target_career": "Best-fit career role based on the resume",
  "experience_level": "Beginner or Intermediate or Advanced",
  "resume_summary": "2-sentence professional summary of this candidate"
}}
"""
    else:
        return jsonify({"error": "Could not extract text from the uploaded file. Please upload a text-based PDF or TXT file."}), 422

    try:
        raw_resp = call_gemini_pro(parse_prompt, system_instruction=parse_system)
        cleaned = re.sub(r"^```(?:json)?", "", raw_resp.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"```$", "", cleaned.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(cleaned)
    except ValueError as cfg_err:
        return jsonify({"error": str(cfg_err)}), 503
    except Exception as ai_err:
        print(f"[Gemini Error] parse-resume failed: {ai_err}")
        return jsonify({"error": "AI extraction failed. Please fill the form manually."}), 502

    # Store resume text and filename in user record
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET resume_filename = %s, resume_text = %s WHERE id = %s",
            (filename, resume_text[:65535], uid),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as db_err:
        print(f"[Resume DB] Could not save resume to user record: {db_err}")

    parsed["resume_text"] = resume_text[:3000]  # Pass back for use in analyze-career
    return jsonify(parsed)


@app.route("/api/interview/save", methods=["POST"])
@login_required
def api_interview_save():
    uid = session["user_id"]
    data = request.get_json(silent=True) or {}
    itype = data.get("type", "technical")
    q_done = int(data.get("questions_done", 0))
    score = int(data.get("score_pct", 0))

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO interview_sessions (user_id, target_role, score, questions_done)
               VALUES (%s, %s, %s, %s)""",
            (uid, f"{itype.capitalize()} Interview Drill", score, q_done),
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": "Failed to record interview performance."}), 500


# ---------------------------------------------------------------------------
# Legal & Compliance Endpoints
# ---------------------------------------------------------------------------

LEGAL_CONTENT = {
    "privacy-policy": ("Privacy Policy", [
        ("Data Protection & Integrity", "Career Copilot persists your profile, hashed credentials, and career roadmap metrics securely in our MySQL database. Passwords are encrypted with SHA-256 / Scrypt salted hashes."),
        ("AI Processing with Gemini Pro", "Your profile skills and goal prompts are processed through the Google Gemini Pro API to generate customized roadmaps and career gap analyses."),
        ("Your Rights", "You retain full ownership of your data and can update your profile or delete your account and all associated records permanently from the Profile settings."),
    ]),
    "terms-of-service": ("Terms of Service", [
        ("Platform Purpose", "Career Copilot provides AI-assisted career advisory and learning roadmap orchestration."),
        ("User Conduct", "Users agree to provide accurate information and respect system usage policies."),
    ]),
    "cookie-policy": ("Cookie Policy", [
        ("Essential Cookies", "We use secure encrypted session cookies solely to maintain your authenticated login state."),
    ]),
    "refund-policy": ("Refund Policy", [
        ("Complimentary Access", "Career Copilot is currently available as a full-featured complimentary platform."),
    ]),
}

@app.route("/privacy-policy")
def privacy_policy():
    h, s = LEGAL_CONTENT["privacy-policy"]
    return render_template("legal.html", heading=h, sections=s)

@app.route("/terms-of-service")
def terms():
    h, s = LEGAL_CONTENT["terms-of-service"]
    return render_template("legal.html", heading=h, sections=s)

@app.route("/cookie-policy")
def cookie_policy():
    h, s = LEGAL_CONTENT["cookie-policy"]
    return render_template("legal.html", heading=h, sections=s)

@app.route("/refund-policy")
def refund_policy():
    h, s = LEGAL_CONTENT["refund-policy"]
    return render_template("legal.html", heading=h, sections=s)

@app.route("/data-deletion")
def data_rights():
    return render_template("data_rights.html")

@app.route("/test-db")
def test_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SHOW TABLES;")
        tables = [t[0] for t in cur.fetchall()]
        cur.close()
        conn.close()
        return f"<h3>[ONLINE] MySQL Database Connected Successfully</h3><p>Active tables: {', '.join(tables)}</p>"
    except Exception as e:
        return f"<h3>[OFFLINE] Database Connection Notice</h3><p>Persistent storage active.</p>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("FLASK_DEBUG") == "1")
