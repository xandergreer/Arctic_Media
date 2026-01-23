@echo off
echo ========================================
echo Rebuilding Arctic Media Executable...
echo ========================================
echo.

REM Check if ArcticMedia.exe is running and stop it
echo Checking if ArcticMedia.exe is running...
tasklist /FI "IMAGENAME eq ArcticMedia.exe" 2>NUL | find /I /N "ArcticMedia.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo ArcticMedia.exe is running. Stopping it...
    taskkill /F /IM ArcticMedia.exe >NUL 2>&1
    timeout /t 2 /nobreak >NUL
    echo ArcticMedia.exe stopped.
) else (
    echo ArcticMedia.exe is not running.
)
echo.

REM Clean previous builds
echo Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist\ArcticMedia.exe" (
    if exist "dist\ArcticMedia.exe.old" del /q "dist\ArcticMedia.exe.old"
    move /y "dist\ArcticMedia.exe" "dist\ArcticMedia.exe.old" >NUL 2>&1
)
echo Clean complete.
echo.

REM Check if Python is available
echo Checking Python installation...
python --version >NUL 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11 or later and try again.
    pause
    exit /b 1
)
python --version
echo.

REM Install/update dependencies if needed
echo Installing/updating Python dependencies...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet
echo Dependencies installed.
echo.

REM Build with PyInstaller
echo Building with PyInstaller...
echo This may take a few minutes...
echo.
python -m PyInstaller ArcticMedia.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ========================================
    echo BUILD FAILED!
    echo ========================================
    echo Check the error messages above for details.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build successful!
echo Executable: dist\ArcticMedia.exe
echo ========================================
echo.
pause

