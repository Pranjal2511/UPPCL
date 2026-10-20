@echo off
setlocal
title UPPCL CSV Report Generator

cd /d "%~dp0"

echo ==========================================
echo      UPPCL CSV REPORT GENERATOR
echo ==========================================
echo.

if not exist "app.py" (
    echo ERROR: app.py was not found.
    echo Keep this BAT file in the same folder as app.py.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Creating Python virtual environment...
    python -m venv .venv
    if errorlevel 1 goto error
)

echo Activating virtual environment...
call ".venv\Scripts\activate.bat"
if errorlevel 1 goto error

echo Checking/installing required packages...
python -m pip install -r requirements.txt
if errorlevel 1 goto error

echo.
echo Starting the local dashboard...
echo When Streamlit shows a Local URL, open it in your browser.
echo Keep this window open while using the dashboard.
echo.
python -m streamlit run app.py
if errorlevel 1 goto error

goto end

:error
echo.
echo ERROR: The dashboard could not start. Read the message above.
pause
exit /b 1

:end
pause
