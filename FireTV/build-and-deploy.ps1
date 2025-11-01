# Fire TV Build and Deploy Script
# This script builds the Arctic Media Fire TV app and optionally installs it on your Fire TV

param(
    [string]$FireTVIP = "",
    [switch]$BuildOnly = $false
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Arctic Media Fire TV - Build Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if we're in the right directory
if (-not (Test-Path "package.json")) {
    Write-Host "Error: package.json not found. Please run this script from the FireTV directory." -ForegroundColor Red
    exit 1
}

# Check for Java
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Try to find Java if not in PATH
$javaHome = [Environment]::GetEnvironmentVariable("JAVA_HOME", "User")
if (-not $javaHome) {
    $javaHome = [Environment]::GetEnvironmentVariable("JAVA_HOME", "Machine")
}
if (-not $javaHome) {
    # Try common installation locations
    $possiblePaths = @(
        "C:\Program Files\Microsoft\jdk-*",
        "C:\Program Files\Java\jdk-*",
        "C:\Program Files\Eclipse Adoptium\jdk-*",
        "C:\Program Files\Android\Android Studio\jbr"
    )
    
    foreach ($pathPattern in $possiblePaths) {
        $found = Get-ChildItem -Path $pathPattern -ErrorAction SilentlyContinue | 
                 Where-Object { Test-Path "$($_.FullName)\bin\java.exe" } | 
                 Select-Object -First 1 -ExpandProperty FullName
        if ($found) {
            $javaHome = $found
            break
        }
    }
}

# Set JAVA_HOME and add to PATH if found
if ($javaHome -and (Test-Path "$javaHome\bin\java.exe")) {
    $env:JAVA_HOME = $javaHome
    $env:PATH = "$javaHome\bin;$env:PATH"
    Write-Host "[OK] Java found at: $javaHome" -ForegroundColor Green
} else {
    Write-Host "[X] Java not found" -ForegroundColor Red
}

# Verify Java is accessible
$javaInstalled = $false
try {
    $javaVersion = java -version 2>&1
    if ($LASTEXITCODE -eq 0 -or $javaVersion) {
        $javaInstalled = $true
    }
} catch {
    Write-Host "[X] Java not accessible" -ForegroundColor Red
}

if (-not $javaInstalled) {
    Write-Host ""
    Write-Host "ERROR: Java JDK is required to build the APK!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install one of the following:" -ForegroundColor Yellow
    Write-Host "  1. Java JDK 17+ from https://adoptium.net/" -ForegroundColor White
    Write-Host "  2. Android Studio (includes Java + Android SDK)" -ForegroundColor White
    Write-Host "     Download: https://developer.android.com/studio" -ForegroundColor White
    Write-Host ""
    Write-Host "After installing Java:" -ForegroundColor Yellow
    Write-Host "  - Restart this terminal" -ForegroundColor White
    Write-Host "  - Verify with: java -version" -ForegroundColor White
    Write-Host ""
    exit 1
}

# Check for Android SDK configuration
$localPropertiesPath = "android\local.properties"
$androidSdkConfigured = $false

if (Test-Path $localPropertiesPath) {
    $androidSdkConfigured = $true
    Write-Host "[OK] Android SDK configured" -ForegroundColor Green
} else {
    Write-Host "[!] Android SDK not configured" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Run this script first to configure Android SDK:" -ForegroundColor Yellow
    Write-Host "  .\setup-android-sdk.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "Or create android\local.properties with:" -ForegroundColor Yellow
    Write-Host "  sdk.dir=C:\\Path\\To\\Android\\Sdk" -ForegroundColor White
    Write-Host ""
    
    # Try to run setup script automatically
    if (Test-Path "setup-android-sdk.ps1") {
        $response = Read-Host "Run setup script now? (Y/N)"
        if ($response -eq 'Y' -or $response -eq 'y') {
            & .\setup-android-sdk.ps1
            if (Test-Path $localPropertiesPath) {
                $androidSdkConfigured = $true
            }
        }
    }
    
    if (-not $androidSdkConfigured) {
        Write-Host "Cannot build without Android SDK configuration." -ForegroundColor Red
        exit 1
    }
}

# Navigate to android directory
Write-Host ""
Write-Host "Building APK..." -ForegroundColor Yellow
Push-Location android

try {
    # Clean previous builds
    Write-Host "Cleaning previous builds..." -ForegroundColor Gray
    & .\gradlew.bat clean 2>&1 | Out-Null
    
    # Build release APK
    Write-Host "Building release APK (this may take a few minutes)..." -ForegroundColor Yellow
    & .\gradlew.bat assembleRelease
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Build failed! Check the error messages above." -ForegroundColor Red
        Pop-Location
        exit 1
    }
    
    # Check if APK was created
    $apkPath = "app\build\outputs\apk\release\app-release.apk"
    
    if (Test-Path $apkPath) {
        $apkSize = (Get-Item $apkPath).Length / 1MB
        Write-Host ""
        Write-Host "[OK] Build successful!" -ForegroundColor Green
        Write-Host ""
        Write-Host "APK Location: $((Get-Location).Path)\$apkPath" -ForegroundColor Cyan
        Write-Host "APK Size: $([math]::Round($apkSize, 2)) MB" -ForegroundColor Cyan
        Write-Host ""
        
        if (-not $BuildOnly -and $FireTVIP -ne "") {
            Write-Host "Connecting to Fire TV at $FireTVIP..." -ForegroundColor Yellow
            
            # Check if ADB is available
            $adbInstalled = $false
            try {
                $adbVersion = adb version 2>&1
                if ($LASTEXITCODE -eq 0) {
                    $adbInstalled = $true
                }
            } catch {
                Write-Host "[X] ADB not found in PATH" -ForegroundColor Red
            }
            
            if ($adbInstalled) {
                Write-Host "Connecting to Fire TV..." -ForegroundColor Yellow
                adb connect $FireTVIP
                
                Write-Host "Installing APK..." -ForegroundColor Yellow
                $fullApkPath = (Resolve-Path $apkPath).Path
                adb install -r $fullApkPath
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Host ""
                    Write-Host "[OK] Successfully installed on Fire TV!" -ForegroundColor Green
                    Write-Host ""
                    Write-Host "You can now launch the app from your Fire TV's Apps menu." -ForegroundColor Cyan
                } else {
                    Write-Host ""
                    Write-Host "Installation failed. Try manually:" -ForegroundColor Yellow
                    Write-Host "  adb connect $FireTVIP" -ForegroundColor White
                    Write-Host "  adb install -r `"$fullApkPath`"" -ForegroundColor White
                }
            } else {
                Write-Host ""
                Write-Host "ADB not found. You can install manually:" -ForegroundColor Yellow
                Write-Host "  1. Enable Developer Options on Fire TV" -ForegroundColor White
                Write-Host "  2. Enable ADB Debugging" -ForegroundColor White
                Write-Host "  3. Copy APK to Fire TV and install" -ForegroundColor White
                Write-Host ""
                Write-Host "Or install Android Platform Tools and try again." -ForegroundColor White
            }
        } else {
            if (-not $BuildOnly) {
                Write-Host "To install on Fire TV:" -ForegroundColor Yellow
                Write-Host "  1. Enable Developer Options: Settings → Device → About → Click 'Build' 7 times" -ForegroundColor White
                Write-Host "  2. Enable ADB: Settings → Developer Options → ADB Debugging" -ForegroundColor White
                Write-Host "  3. Find Fire TV IP: Settings → Device → About → Network" -ForegroundColor White
                Write-Host "  4. Run: adb connect YOUR_FIRE_TV_IP" -ForegroundColor White
                Write-Host "  5. Run: adb install -r `"$((Resolve-Path $apkPath).Path)`"" -ForegroundColor White
                Write-Host ""
                Write-Host "Or run this script with -FireTVIP parameter:" -ForegroundColor Yellow
                Write-Host "  .\build-and-deploy.ps1 -FireTVIP 192.168.1.100" -ForegroundColor White
            }
        }
    } else {
        Write-Host ""
        Write-Host "Build completed but APK not found at expected location!" -ForegroundColor Red
        Pop-Location
        exit 1
    }
} catch {
    Write-Host ""
    Write-Host "Build error: $_" -ForegroundColor Red
    Pop-Location
    exit 1
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green

