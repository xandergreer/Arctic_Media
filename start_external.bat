@echo off
echo Starting Arctic Media with External Access...
echo.
echo This will allow connections from outside your local network.
echo Make sure you have configured port forwarding on your router!
echo.

REM Set environment variables for external access
set ARCTIC_HOST=0.0.0.0
set ARCTIC_PORT=8000

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Start the server
echo Starting server on %ARCTIC_HOST%:%ARCTIC_PORT%...
echo.
echo External access URL: http://YOUR_EXTERNAL_IP:8000
echo Local access URL: http://localhost:8000
echo.
echo Press Ctrl+C to stop the server
echo.

python run_server.py

pause
