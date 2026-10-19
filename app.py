"""
Career Copilot — Flask app scaffold.

This file wires up the frontend templates so the whole project runs
out of the box. Replace the placeholder logic (login/register/analyze)
with real database + Gemini API calls when the backend is built.

Run with:
    pip install flask
    python app.py
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify
import os

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024
@app.context_processor
def legal_details():
    return {'business_name': os.getenv('BUSINESS_NAME', ''), 'contact_email': os.getenv('CONTACT_EMAIL', '')}

LEGAL = {
 'privacy-policy': ('Privacy Policy', [('Data we process','This educational prototype displays information you enter in your browser. Demo registration and login do not create accounts or retain submissions in a database. Career analysis and chat text are sent to the Flask server only when used, and are not intentionally stored by the application.'),('Purpose and retention','Information entered into demo tools is used to create immediate on-screen sample responses. Server logs operated by your host may record technical information such as IP addresses and requests. Hosting retention settings must be reviewed before launch.'),('Third parties','The interface currently loads Bootstrap CSS and JavaScript from jsDelivr and Font Awesome CSS from cdnjs. Those providers may receive technical request data, including IP address. No marketing or analytics SDK is installed. No Gemini API call is made in this demo.'),('Choices and rights','Use the Data deletion page to clear the cookie preference stored on this device, and contact the project operator for any server-related privacy request once a contact is configured.'),('Children','This prototype does not ask for dates of birth or knowingly create profiles of children. It must not be deployed as a service directed at children without appropriate age-assurance and parent or guardian consent measures where required.'),('Contact','The operator must provide an actual business identity and a contact email before public launch.')]),
 'terms-of-service': ('Terms of Service', [('Purpose','Career Copilot is an educational demonstration with sample career analysis, example roadmaps and mock interview content. It does not promise job placement, outcomes or scoring accuracy.'),('Accounts','Registration and login screens are only a demo; submitting them does not create or authenticate an account.'),('Your responsibilities','Do not enter passwords, confidential, sensitive, or third-party information into the sample chat and analysis tools. Do not rely solely on the samples for education or employment decisions.'),('Availability and liability','The prototype is provided for educational evaluation, without guaranteed availability. Any real deployment needs jurisdiction-specific terms approved by its operator.'),('Contact','Contact details must be configured by the operator before any public offering.')]),
 'refund-policy': ('Refund Policy', [('No purchases','Career Copilot currently has no checkout, subscriptions, payments or paid services. Consequently there are no charges or refunds to process.'),('If paid features are introduced','Pricing, taxes and all applicable fees must be disclosed before payment, along with the real cancellation and refund rules and a support contact. This page must be updated before enabling payments.')]),
 'cookie-policy': ('Cookie Policy', [('Essential preference storage','This demo uses localStorage key cc-cookie-preference-v1 to remember whether you accepted or rejected optional cookies. It remains until you remove it using the Data deletion page or your browser settings.'),('Optional cookies','No analytics or marketing cookies are currently intentionally installed by this application. The Accept button does not activate tracking. Any future nonessential tracking must be disabled until consent and respect rejection.'),('Third-party resources','Content delivery networks for Bootstrap and Font Awesome receive browser requests and may process technical information. Check their policies or self-host these libraries before production.'),('Your choices','Reject optional and Accept optional are equally available. Use Cookie preferences in the footer to change your stored choice.')])
}
@app.route('/privacy-policy')
def privacy_policy(): return render_template('legal.html',heading=LEGAL['privacy-policy'][0],sections=LEGAL['privacy-policy'][1])
@app.route('/terms-of-service')
def terms(): return render_template('legal.html',heading=LEGAL['terms-of-service'][0],sections=LEGAL['terms-of-service'][1])
@app.route('/refund-policy')
def refund_policy(): return render_template('legal.html',heading=LEGAL['refund-policy'][0],sections=LEGAL['refund-policy'][1])
@app.route('/cookie-policy')
def cookie_policy(): return render_template('legal.html',heading=LEGAL['cookie-policy'][0],sections=LEGAL['cookie-policy'][1])
@app.route('/data-deletion')
def data_rights(): return render_template('data_rights.html')



@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # TODO: verify credentials against the database
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # TODO: create user record in the database
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/career-analysis")
def career_analysis():
    return render_template("career_analysis.html")


@app.route("/roadmap")
def roadmap():
    return render_template("roadmap.html")


@app.route("/courses")
def courses():
    return render_template("courses.html")


@app.route("/interview")
def interview():
    return render_template("interview.html")


@app.route("/progress")
def progress():
    return render_template("progress.html")


@app.route("/profile")
def profile():
    return render_template("profile.html")


# ---------------------------------------------------------------------------
# API endpoints — frontend JS already calls these via fetch(). Wire each one
# to the Gemini API + SQLite database; never hard-code the AI response.
# ---------------------------------------------------------------------------

@app.route("/api/analyze-career", methods=["POST"])
def api_analyze_career():
    data = request.get_json(silent=True) or {}
    # TODO: call Gemini API with `data`, parse the response, and return it.
    return jsonify({
        "recommended_career": data.get("target_career", "Web Developer"),
        "match_percentage": 82,
        "current_skills": data.get("current_skills", "").split(",") if data.get("current_skills") else [],
        "missing_skills": ["JavaScript", "React", "SQL"],
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "")
    # TODO: forward `user_message` to the Gemini API and return the real reply.
    return jsonify({"reply": f"Here's guidance based on: \"{user_message}\""})


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
