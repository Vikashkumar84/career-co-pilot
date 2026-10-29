# Career Copilot — AI-Powered Career Navigation SaaS

Career Copilot is a custom-coded SaaS application powered by **Google Gemini Pro** and backed by a persistent **MySQL database** (with automatic SQLite fallback). It dynamically diagnoses engineering skill gaps, generates milestone roadmaps, tracks user progress, and provides context-aware AI career advisory.

---

## 🌟 Key Features

1. **Google Gemini Pro Integration**:
   - Dynamic career analysis, skill gap extraction, and 6-step engineering roadmaps via `/api/analyze-career`.
   - Real-time AI Career Assistant chat via `/api/chat` using profile-aware system prompts.
   - Intelligent fallback calculation if API keys are offline or rate-limited.

2. **Persistent Database Architecture**:
   - Real MySQL database integration via `mysql.connector` using credentials in `host.env`.
   - Automatic database and table creation (`users`, `career_analyses`, `roadmap_steps`, `user_skills`, `chat_history`, `interview_progress`).
   - Seamless fallback to SQLite (`career_copilot.db`) if local MySQL server credentials are not yet configured.

3. **Secure User Authentication**:
   - Secure account registration and login with salted password hashing (`werkzeug.security`).
   - Flask session management and protected endpoints via `@login_required`.

4. **Bespoke SaaS Frontend**:
   - High-end SaaS UI with a refined Slate & Violet design system.
   - Zero demo notices or hardcoded template arrays — 100% dynamic rendering from database tables.
   - Interactive milestone checklist toggles with real-time AJAX state persistence.

---

## 🚀 Quick Start (Windows)

1. Open a terminal in this directory:
   ```powershell
   py -m pip install -r requirements.txt
   py app.py
   ```
   *(Or double-click **`START_WEBSITE.bat`**)*

2. Open your browser to:
   ```
   http://127.0.0.1:5000/
   ```

---

## ⚙️ Configuration (`host.env`)

Edit `host.env` to configure your MySQL connection and Gemini API key:

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=career_copilot
DB_USER=root
DB_PASSWORD=YourMySQLPassword

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-pro

SECRET_KEY=your_secure_random_secret_key
BUSINESS_NAME=Career Copilot
CONTACT_EMAIL=support@careercopilot.app
```

---

## 🧪 Automated Testing

To run the end-to-end automated verification suite:
```powershell
py test_app.py
```
This tests registration, login, dashboard metrics, Gemini analysis, roadmap toggles, chat endpoints, and profile updates.
