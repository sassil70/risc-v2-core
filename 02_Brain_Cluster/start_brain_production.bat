@echo off
echo ==========================================
echo      RISC V2 BRAIN CLUSTER - REVEAL
echo ==========================================
echo.
echo [1/3] Checking Docker Connectivity...
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is NOT running! Please start Docker Desktop.
    pause
    exit /b
)
echo [OK] Docker is running.
echo.
echo [2/3] Starting Database Container...
docker-compose up -d alloydb
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start database.
    pause
    exit /b
)
echo [OK] Database is active.
echo.
echo [3/4] Setting up USB Connection (ADB Reverse Port 8001)...
adb reverse tcp:8001 tcp:8001
if %errorlevel% neq 0 (
    echo [WARNING] ADB Reverse failed. Is USB connected and Debugging ON?
)
echo [OK] USB Tunnel Active.
echo.
echo [4/4] Launching API Server (0.0.0.0:8001)...
echo.
echo      LISTENING FOR MOBILE CONNECTIONS...
echo.
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
pause
