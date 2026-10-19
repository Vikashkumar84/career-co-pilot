# Career Copilot — run and preview your website

**Do not use VS Code Live Preview / Live Server on `templates/index.html`.**
This project uses Flask and Jinja2 templates. Opening the HTML file directly shows template code (for example `{% for ... %}`) and can break styling and navigation. The Flask server renders those templates correctly.

## Windows — easiest method
1. Extract the ZIP archive.
2. Open the inner `career-copilot` folder that contains `app.py`, `templates`, and `static`.
3. Double-click **START_WEBSITE.bat** (requires Python 3 and an internet connection to install Flask the first time).
4. Your browser should open **http://127.0.0.1:5000/** automatically. If it does not, copy that link into Chrome/Edge.
5. Keep the terminal window open while browsing. To stop the site, press **Ctrl+C**.

## Run in the VS Code terminal (Windows)
1. In VS Code, use **File → Open Folder**, and select the folder containing `app.py`.
2. Use **Terminal → New Terminal**.
3. Run:

```powershell
py -m pip install -r requirements.txt
py app.py
```

4. Wait for `Running on http://127.0.0.1:5000`; then Ctrl+click the link or open it in the browser.

If `py` isn't recognized, use `python` instead.

## macOS / Linux
From the project directory:

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

Then visit **http://127.0.0.1:5000/**.

## Troubleshooting
- **Raw `{% ... %}` text, plain HTML:** You're still viewing a template file directly. Close Live Preview and open `http://127.0.0.1:5000/` instead.
- **No CSS or icons:** Confirm you are using the Flask URL rather than `file:///...`; check internet connectivity for the external Bootstrap and Font Awesome libraries.
- **`ModuleNotFoundError: No module named 'flask'`:** Install dependencies from the folder with `requirements.txt` using the commands above.
- **Port 5000 is already in use:** Stop the other app occupying that port; then run Career Copilot again.
- **Page won't open:** Keep the terminal open and check for a Python error message. You cannot access this local link from another person's computer without deployment.

## Where to find the 20 requested compliance fixes
See `README_COMPLIANCE.md` and `THIRD_PARTY_AUDIT.md`. Policy pages, consent banner, accessibility and transparency improvements are included. Business identity, age-verification, and any future real database/email/payment integrations still require action before a public launch.

**Note:** Career Copilot is currently a demonstration. Login/registration do not persist user accounts, and recommendation and chat responses are example data rather than live AI predictions.
