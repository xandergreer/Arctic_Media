@echo off
echo Building Arctic Media Executable...
echo.

REM Clean previous builds
echo Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist\ArcticMedia.exe" del /q "dist\ArcticMedia.exe"

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

