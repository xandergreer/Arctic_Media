# Android SDK Setup Helper Script
# This script helps you configure the Android SDK location for building the Fire TV app

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Android SDK Configuration Helper" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check existing ANDROID_HOME
$androidHome = [Environment]::GetEnvironmentVariable("ANDROID_HOME", "User")
if (-not $androidHome) {
    $androidHome = [Environment]::GetEnvironmentVariable("ANDROID_HOME", "Machine")
}
if (-not $androidHome) {
    $androidHome = [Environment]::GetEnvironmentVariable("ANDROID_SDK_ROOT", "User")
}
if (-not $androidHome) {
    $androidHome = [Environment]::GetEnvironmentVariable("ANDROID_SDK_ROOT", "Machine")
}

if ($androidHome -and (Test-Path "$androidHome\platform-tools\adb.exe")) {
    Write-Host "[OK] Found Android SDK at: $androidHome" -ForegroundColor Green
    Write-Host ""
    Write-Host "Creating local.properties file..." -ForegroundColor Yellow
    
    $localPropertiesPath = "android\local.properties"
    $sdkPath = $androidHome -replace '\\', '\\'
    "sdk.dir=$sdkPath" | Out-File -FilePath $localPropertiesPath -Encoding ASCII
    
    Write-Host "[OK] Configuration complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now build the APK with:" -ForegroundColor Cyan
    Write-Host "  .\build-and-deploy.ps1" -ForegroundColor White
    exit 0
}

# Try common locations
Write-Host "Searching for Android SDK..." -ForegroundColor Yellow
$possiblePaths = @(
    "$env:LOCALAPPDATA\Android\Sdk",
    "$env:USERPROFILE\AppData\Local\Android\Sdk",
    "C:\Users\$env:USERNAME\AppData\Local\Android\Sdk",
    "$env:LOCALAPPDATA\Android\Sdk",
    "C:\Android\Sdk"
)

$foundSdk = $null
foreach ($path in $possiblePaths) {
    if (Test-Path $path) {
        Write-Host "Checking: $path" -ForegroundColor Gray
        if (Test-Path "$path\platform-tools\adb.exe") {
            $foundSdk = $path
            break
        }
    }
}

if ($foundSdk) {
    Write-Host ""
    Write-Host "[OK] Found Android SDK at: $foundSdk" -ForegroundColor Green
    Write-Host ""
    Write-Host "Creating local.properties file..." -ForegroundColor Yellow
    
    $localPropertiesPath = "android\local.properties"
    $sdkPath = $foundSdk -replace '\\', '\\'
    "sdk.dir=$sdkPath" | Out-File -FilePath $localPropertiesPath -Encoding ASCII
    
    Write-Host "[OK] Configuration complete!" -ForegroundColor Green
    Write-Host ""
    Write-Host "SDK location saved to: $localPropertiesPath" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "You can now build the APK with:" -ForegroundColor Cyan
    Write-Host "  .\build-and-deploy.ps1" -ForegroundColor White
    exit 0
}

# Not found - provide instructions
Write-Host "[X] Android SDK not found" -ForegroundColor Red
Write-Host ""
Write-Host "You need to install the Android SDK to build the app." -ForegroundColor Yellow
Write-Host ""
Write-Host "Option 1: Install Android Studio (Recommended)" -ForegroundColor Cyan
Write-Host "  Download: https://developer.android.com/studio" -ForegroundColor White
Write-Host "  - Includes Android SDK automatically" -ForegroundColor Gray
Write-Host "  - SDK location: %LOCALAPPDATA%\Android\Sdk" -ForegroundColor Gray
Write-Host ""
Write-Host "Option 2: Install Standalone SDK Command Line Tools" -ForegroundColor Cyan
Write-Host "  Download: https://developer.android.com/tools#command-tools" -ForegroundColor White
Write-Host ""
Write-Host "Option 3: If you already have Android SDK installed elsewhere:" -ForegroundColor Cyan
Write-Host "  1. Find your SDK location" -ForegroundColor White
Write-Host "  2. Create android\local.properties file with:" -ForegroundColor White
Write-Host "     sdk.dir=C:\\Path\\To\\Your\\Android\\Sdk" -ForegroundColor Gray
Write-Host ""
Write-Host "After installing, run this script again:" -ForegroundColor Yellow
Write-Host "  .\setup-android-sdk.ps1" -ForegroundColor White
Write-Host ""

# Prompt for manual entry
Write-Host ""
$manualPath = Read-Host "Enter your Android SDK path manually (or press Enter to download Android Studio)"
if ($manualPath -and (Test-Path $manualPath)) {
    if (Test-Path "$manualPath\platform-tools\adb.exe") {
        $localPropertiesPath = "android\local.properties"
        $sdkPath = $manualPath -replace '\\', '\\'
        "sdk.dir=$sdkPath" | Out-File -FilePath $localPropertiesPath -Encoding ASCII
        
        Write-Host ""
        Write-Host "[OK] Configuration saved!" -ForegroundColor Green
        Write-Host "You can now build with: .\build-and-deploy.ps1" -ForegroundColor Cyan
        exit 0
    } else {
        Write-Host "X Invalid SDK path (adb.exe not found)" -ForegroundColor Red
        Write-Host "The SDK must contain platform-tools\adb.exe" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host ""
    Write-Host "Android SDK not found. You have two options:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Option 1: Install Android Studio (Recommended)" -ForegroundColor Cyan
    Write-Host "  1. Download: https://developer.android.com/studio" -ForegroundColor White
    Write-Host "  2. Install with default settings" -ForegroundColor White
    Write-Host "  3. SDK will be at: %LOCALAPPDATA%\Android\Sdk" -ForegroundColor Gray
    Write-Host "  4. Run this script again after installation" -ForegroundColor White
    Write-Host ""
    Write-Host "Option 2: Install Command Line Tools Only" -ForegroundColor Cyan
    Write-Host "  1. Download: https://developer.android.com/tools#command-tools" -ForegroundColor White
    Write-Host "  2. Extract to a folder (e.g., C:\Android\Sdk)" -ForegroundColor White
    Write-Host "  3. Run this script again and enter the path" -ForegroundColor White
    Write-Host ""
    
    $openStudio = Read-Host "Open Android Studio download page now? (Y/N)"
    if ($openStudio -eq 'Y' -or $openStudio -eq 'y') {
        Start-Process "https://developer.android.com/studio"
    }
    
    exit 1
}

