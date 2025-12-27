@echo off
echo ===============================================
echo     OSAGAMING CRM - Quick Start Launcher
echo ===============================================
echo.

echo Checking prerequisites...
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed or not in PATH
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
) else (
    echo ✅ Docker is installed
)

REM Check if Docker Compose is available
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not available
    echo Please install Docker Desktop which includes Docker Compose
    pause
    exit /b 1
) else (
    echo ✅ Docker Compose is available
)

echo.
echo Starting OSAGAMING CRM...
echo This may take a few minutes on first run.
echo.

REM Stop any existing containers
echo 🛑 Stopping existing containers (if any)...
docker-compose down

echo.
echo 🚀 Starting application containers...
docker-compose up -d

if %errorlevel% neq 0 (
    echo ❌ Failed to start containers
    echo Check the error messages above
    pause
    exit /b 1
)

echo.
echo ⏳ Waiting for services to start...
timeout /t 10 /nobreak >nul

echo.
echo ===============================================
echo ✅ OSAGAMING CRM is now running!
echo ===============================================
echo.
echo 🌐 Application URLs:
echo    Frontend:    http://localhost:8000
echo    API Docs:    http://localhost:8000/docs
echo    Health Check: http://localhost:8000/health
echo.
echo 🔑 Login Credentials:
echo    Email: admin@osagaming.com
echo    Password: password
echo.
echo 📋 Useful Commands:
echo    - View logs: docker-compose logs -f
echo    - Stop app: docker-compose down
echo    - Restart: docker-compose restart
echo.
echo 🔍 To view real-time logs, run:
echo    docker-compose logs -f
echo.
echo Press any key to open the application in your browser...
pause >nul

REM Try to open browser
start http://localhost:8000

echo.
echo ✅ Done! The application should now be open in your browser.
echo.
echo 💡 Pro Tips:
echo    - Check API documentation at http://localhost:8000/docs
echo    - View logs with: docker-compose logs -f
echo    - Stop with: docker-compose down
echo.
pause