@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo   AI Resume Analyzer - Setup
echo ============================================

rem 1. Check Python
set PY=python
where python >nul 2>nul
if errorlevel 1 (
    where py >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Python was not found. Install Python 3.10+ from https://www.python.org/downloads/
        echo         and tick "Add python.exe to PATH" during installation.
        goto :fail
    )
    set PY=py -3
)
%PY% --version

rem 2. Create virtual environment
if not exist venv\Scripts\python.exe (
    echo Creating virtual environment...
    %PY% -m venv venv
    if errorlevel 1 goto :fail
) else (
    echo Virtual environment already exists.
)

rem 3. Use the virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 goto :fail

rem 4-5. Upgrade pip and install requirements
echo Upgrading pip...
python -m pip install --upgrade pip
echo Installing requirements (this may take a few minutes)...
python -m pip install -r requirements.txt
if errorlevel 1 goto :fail

rem 6. Required folders and .env
if not exist uploads mkdir uploads
if not exist data\vector_store mkdir data\vector_store
if not exist .env (
    copy .env.example .env >nul
    echo Created .env from .env.example - add your GEMINI_API_KEY there for AI features.
)

rem 7-8. Database + seed data
echo Initializing database and sample data...
python scripts\seed_data.py
if errorlevel 1 goto :fail

rem 9. RAG vector store
echo Building RAG vector store...
python scripts\build_rag.py
if errorlevel 1 goto :fail

echo.
echo [SUCCESS] Setup complete. Start the app with run.bat
pause
exit /b 0

:fail
echo.
echo [ERROR] Setup failed. Read the messages above, fix the problem and run setup.bat again.
pause
exit /b 1
