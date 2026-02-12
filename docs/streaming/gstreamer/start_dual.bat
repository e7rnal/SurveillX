@echo off
REM SurveillX Dual-Mode Client Launcher
REM Captures webcam once and sends to BOTH servers simultaneously.

set SERVER=surveillx.duckdns.org
set CAMERA=0

echo ===================================
echo  SurveillX Dual-Mode Streaming
echo ===================================
echo.
echo Sending camera frames to both servers:
echo   - JPEG WebSocket (port 8443)
echo   - FastRTC        (port 8080)
echo.
echo Press Ctrl+C to stop.
echo.

python client_dual.py --server %SERVER% --camera %CAMERA%
pause
