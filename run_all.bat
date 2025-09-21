@echo off
REM =========================
REM Run Proofing System (Manager + Emulators + Dashboard)
REM =========================
setlocal

REM --- נתיב לפרויקט ---
cd /D "C:\Users\ytzha\Downloads\IOT_SMART_HOME-main\IOT_SMART_HOME-main"

REM --- הגדרת נתיב ל-Python מתוך ה-venv ---
set "VENV_PY=C:\Users\ytzha\Downloads\IOT_SMART_HOME-main\venv\Scripts\python.exe"

REM --- הפעלת Manager ---
start "Manager" cmd /k "%VENV_PY%" manager.py

REM --- הפעלת Emulators GUI ---
start "Emulators GUI" cmd /k "%VENV_PY%" emulators_gui.py

REM --- הפעלת Dashboard (אם אתה עוד משתמש ב-gui.py) ---
start "Dashboard" cmd /k "%VENV_PY%" proofing_dashboard.py

echo כל המערכת הופעלה. סגור חלונות כדי לעצור.
pause
