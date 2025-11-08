@echo off
echo ========================================
echo Arctic Media iOS Build - Starting Now!
echo ========================================
echo.

cd /d "%~dp0"

echo Step 1: Checking EAS CLI...
eas --version
if errorlevel 1 (
    echo EAS CLI not found. Installing...
    npm install -g eas-cli
)

echo.
echo Step 2: Logging in to Expo...
eas whoami
if errorlevel 1 (
    echo Please login to Expo...
    eas login
)

echo.
echo Step 3: Starting iOS Build...
echo.
echo This will:
echo - Build your app in the cloud
echo - Generate an IPA file
echo - Give you a download link
echo.
echo Build type: Preview (for testing on devices)
echo.

pause

eas build --platform ios --profile preview

echo.
echo ========================================
echo Build Started!
echo ========================================
echo.
echo Check the build status at: https://expo.dev/accounts/arctic1720/projects/arctic-media/builds
echo.
echo When the build completes, you'll get a download link for the IPA!
echo.
pause


