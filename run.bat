@echo off
echo ==============================================
echo   Face Attendance System - VisionAttend AI
echo ==============================================
cd /d "%~dp0"

if exist "venv\Scripts\python.exe" (
    echo Starting server using virtual environment...
    venv\Scripts\python.exe app.py
) else (
    echo Virtual environment not found, attempting with system Python...
    python app.py
)
pause
