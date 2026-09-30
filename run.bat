@echo off
setlocal
cd /d "%~dp0"
if not exist venv\Scripts\python.exe (
    echo [ERROR] Virtual environment not found. Please run setup.bat first.
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
echo ============================================
echo   AI Resume Analyzer
echo   App:      http://127.0.0.1:8000
echo   API docs: http://127.0.0.1:8000/docs
echo   Press CTRL+C to stop the server.
echo ============================================
uvicorn app.main:app --reload
pause
