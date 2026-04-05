@echo off
title RISC V2 Brain Cluster
echo =========================================================
echo RISC V2 - Smart Surveyor Brain Cluster (Phase 5: Field Test)
echo =========================================================
echo.
echo IP Configuration: Listening on 0.0.0.0 (All Wi-Fi Interfaces)
echo Expected Port: 8002
echo Mobile Interface IP: 10.190.206.184
echo.
echo Starting FastAPI Server...
cd 02_Brain_Cluster
call venv\Scripts\activate
uvicorn main:app --host 0.0.0.0 --port 8002 --reload
pause
