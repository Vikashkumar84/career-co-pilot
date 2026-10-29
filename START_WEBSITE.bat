@echo off
title Career Copilot — AI SaaS Platform
echo ======================================================================
echo           Career Copilot — Powered by Google Gemini Pro
echo ======================================================================
echo.

if exist "C:\Users\vikash kumar\AppData\Local\Programs\Python\Python313\python.exe" (
    "C:\Users\vikash kumar\AppData\Local\Programs\Python\Python313\python.exe" app.py
) else (
    python app.py
)

pause
