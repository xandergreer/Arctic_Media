@echo off
echo Building Arctic Media Executable...
echo.

REM Check if ArcticMedia.exe is running and kill it
echo Checking if ArcticMedia.exe is running...
tasklist /FI "IMAGENAME eq ArcticMedia.exe" 2>NUL | find /I /N "ArcticMedia.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo ArcticMedia.exe is running. Stopping it...
    taskkill /F /IM ArcticMedia.exe 2>NUL
    timeout /t 2 /nobreak >NUL
    echo ArcticMedia.exe stopped.
) else (
    echo ArcticMedia.exe is not running.
)

REM Clean previous builds
echo Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist\ArcticMedia.exe" del /q "dist\ArcticMedia.exe"

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>NUL
if errorlevel 1 (
    echo PyInstaller is not installed. Installing it now...
    pip install pyinstaller==6.15.0
    echo.
)

REM Ensure all dependencies are installed
echo Installing/updating Python dependencies...
pip install -r requirements.txt -q
echo.

REM Build using spec file
echo Building with PyInstaller...
python -m PyInstaller --clean --noconfirm ArcticMedia.spec

if exist "dist\ArcticMedia.exe" (
    echo.
    echo ==========================================
    echo Build successful!
    echo Executable: dist\ArcticMedia.exe
    echo ==========================================
) else (
    echo.
    echo ==========================================
    echo Build failed!
    echo ==========================================
)

pause

