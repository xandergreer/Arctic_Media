# Build IPA Script for Arctic Media iOS App
# This script helps you build an IPA file

Write-Host "=== Arctic Media iOS Build Script ===" -ForegroundColor Cyan
Write-Host ""

# Check if we're on Windows or Mac
$isMac = $false
if ($IsMacOS -or (Get-Command "sw_vers" -ErrorAction SilentlyContinue)) {
    $isMac = $true
}

if (-not $isMac) {
    Write-Host "Detected: Windows" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Since you're on Windows, you have two options:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Option 1: EAS Build (Cloud - Recommended for Windows)" -ForegroundColor Green
    Write-Host "  This builds your app in the cloud. No Mac needed!" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Option 2: Build on Mac" -ForegroundColor Green
    Write-Host "  If you have access to a Mac, you can build locally" -ForegroundColor Gray
    Write-Host ""
    
    $choice = Read-Host "Choose option (1 for EAS Cloud Build, 2 for Mac instructions)"
    
    if ($choice -eq "1") {
        Write-Host ""
        Write-Host "=== Setting up EAS Build ===" -ForegroundColor Cyan
        Write-Host ""
        
        # Check if EAS CLI is installed
        $easInstalled = Get-Command "eas" -ErrorAction SilentlyContinue
        if (-not $easInstalled) {
            Write-Host "Installing EAS CLI..." -ForegroundColor Yellow
            npm install -g eas-cli
        }
        
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Green
        Write-Host "1. Login to Expo: eas login" -ForegroundColor White
        Write-Host "2. Build for iOS: eas build --platform ios" -ForegroundColor White
        Write-Host "3. Choose build type: 'preview' (for testing) or 'production' (for App Store)" -ForegroundColor White
        Write-Host ""
        Write-Host "The build will happen in the cloud and you'll get a download link!" -ForegroundColor Green
        Write-Host ""
        
        $buildNow = Read-Host "Do you want to start the build now? (y/n)"
        if ($buildNow -eq "y" -or $buildNow -eq "Y") {
            Write-Host ""
            Write-Host "Starting EAS Build..." -ForegroundColor Cyan
            eas build --platform ios
        }
    } else {
        Write-Host ""
        Write-Host "=== Mac Build Instructions ===" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "On your Mac, run these commands:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "1. cd IOS" -ForegroundColor White
        Write-Host "2. npm install" -ForegroundColor White
        Write-Host "3. npx expo prebuild --platform ios" -ForegroundColor White
        Write-Host "4. cd ios && pod install && cd .." -ForegroundColor White
        Write-Host "5. open ios/arctic-media.xcworkspace" -ForegroundColor White
        Write-Host ""
        Write-Host "Then in Xcode:" -ForegroundColor Yellow
        Write-Host "- Select your team in Signing & Capabilities" -ForegroundColor White
        Write-Host "- Product > Archive" -ForegroundColor White
        Write-Host "- Distribute App > Ad Hoc or App Store" -ForegroundColor White
        Write-Host ""
    }
} else {
    Write-Host "Detected: macOS" -ForegroundColor Green
    Write-Host ""
    Write-Host "=== Setting up for Local Build ===" -ForegroundColor Cyan
    Write-Host ""
    
    # Check if dependencies are installed
    if (-not (Test-Path "node_modules")) {
        Write-Host "Installing dependencies..." -ForegroundColor Yellow
        npm install
    }
    
    # Check if native project exists
    if (-not (Test-Path "ios")) {
        Write-Host "Generating native iOS project..." -ForegroundColor Yellow
        npx expo prebuild --platform ios
    }
    
    # Install CocoaPods
    Write-Host "Installing CocoaPods dependencies..." -ForegroundColor Yellow
    Set-Location ios
    pod install
    Set-Location ..
    
    Write-Host ""
    Write-Host "=== Opening Xcode ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "Opening Xcode workspace..." -ForegroundColor Yellow
    
    if (Test-Path "ios/arctic-media.xcworkspace") {
        open ios/arctic-media.xcworkspace
        Write-Host ""
        Write-Host "Xcode should now be open!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next steps in Xcode:" -ForegroundColor Yellow
        Write-Host "1. Select your project > Target > Signing & Capabilities" -ForegroundColor White
        Write-Host "2. Enable 'Automatically manage signing' and select your Team" -ForegroundColor White
        Write-Host "3. Product > Archive to build" -ForegroundColor White
        Write-Host "4. Distribute App to export IPA" -ForegroundColor White
    } else {
        Write-Host "Workspace not found. Please run: npx expo prebuild --platform ios" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Done! Check BUILD_IPA_GUIDE.md for detailed instructions." -ForegroundColor Cyan


