# Career Copilot - online deployment (Render)

This repo is a **Flask educational prototype**. Registration/login do NOT authenticate users, and career scores/chat are examples. Do not invite users to submit real passwords or sensitive data. Check legal contact details before public use.

## First-time setup

1. Open the inner **career-copilot/** directory, the one containing `app.py` and `requirements.txt`.
2. Create a GitHub repository. Upload **all files inside this directory** to the **root** of that repository (or keep them nested and set Render's Root Directory to `career-copilot`). GitHub web interface: **Add file > Upload files > Commit changes**. Do **not** upload `.env`, database files, or secrets.
3. Visit https://dashboard.render.com > **New > Web Service**, connect GitHub, and choose the repo.
4. Choose **Python 3** runtime, **Free** instance if available, **Build Command** `pip install -r requirements.txt`, **Start Command** `gunicorn app:app --bind 0.0.0.0:$PORT`. If repo's root contains the outer folder, set **Root Directory** to `career-copilot`.
5. Click **Deploy Web Service** and wait for status **Live**. The service receives a public HTTPS `*.onrender.com` address.

The optional `render.yaml` can be used for infrastructure-as-code / Render Blueprint deployment, but manual web service setup is easiest to understand.

## Important platform notes

- Render Free sleeps after inactivity and takes time to wake up.
- **SQLite files and uploads on Free Render storage are not persistent.** If you later add real accounts/data, use a separately hosted persistent SQL database (e.g. PostgreSQL), with database credentials kept in Render environment variables. Free Render Postgres has its own expiry limitations.
- This archive doesn't implement real account authentication, an SQL DB or Gemini AI. Hosting it does not enable those features.
- Use the Render Logs tab if a deployment fails. Check that `requirements.txt` is found and the start command references `app:app`.

## Local run, Windows PowerShell

```powershell
py -m pip install -r requirements.txt
py app.py
```

Then open http://127.0.0.1:5000/ locally.
