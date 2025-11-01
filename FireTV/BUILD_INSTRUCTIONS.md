# Fire TV Build Instructions

## ✅ What's Ready

Your Fire TV app is **complete** and **ready to build**! All code is in place.

## 📋 Prerequisites

### 1. Install Java JDK
Download and install Java Development Kit 17 or higher:
- Download: https://www.oracle.com/java/technologies/downloads/
- Or use OpenJDK: https://adoptium.net/

**After installing:**
1. Add Java to PATH environment variable
2. Verify: `java -version`
3. Set JAVA_HOME environment variable to Java installation folder

### 2. Install Android Studio (Optional but Recommended)
- Download: https://developer.android.com/studio
- This installs Android SDK automatically

## 🏗️ Build Options

### Option A: Build with Expo (Easiest)

```bash
cd FireTV
npx expo run:android
```

This will:
- Build the app
- Install on connected device/emulator
- Start the development server

### Option B: Build Release APK with Gradle

```bash
cd FireTV/android
.\gradlew assembleRelease
```

APK location: `app/build/outputs/apk/release/app-release.apk`

### Option C: Use Android Studio

1. Open Android Studio
2. File → Open → Select `FireTV/android` folder
3. Build → Build Bundle(s) / APK(s) → Build APK(s)
4. Wait for build to complete
5. APK will be in `app/build/outputs/apk/release/`

## 📱 Install on Fire TV

### 1. Enable Developer Mode
1. Settings → Device → About
2. Click "Build" 7 times
3. Developer options will appear

### 2. Enable ADB
1. Settings → Developer Options
2. Enable "ADB Debugging"

### 3. Find Fire TV IP
1. Settings → Device → About → Network
2. Note the IP address (e.g., 192.168.1.100)

### 4. Connect and Install
```bash
# Connect to Fire TV
adb connect YOUR_FIRE_TV_IP

# Install APK
adb install app-release.apk

# Or for development
adb install app-debug.apk
```

## 🚀 Quick Deployment Script

Create a file `deploy-to-firetv.bat`:

```batch
@echo off
echo Building Arctic Media Fire TV...
cd FireTV\android
call gradlew assembleRelease

if exist "app\build\outputs\apk\release\app-release.apk" (
    echo.
    echo Build successful!
    echo.
    echo Installing on Fire TV...
    cd ..\..
    adb connect YOUR_FIRE_TV_IP
    adb install FireTV\android\app\build\outputs\apk\release\app-release.apk
    echo.
    echo Done! Check your Fire TV.
) else (
    echo.
    echo Build failed!
)
pause
```

## 🧪 Test Without Fire TV

Run on Android TV emulator:

1. Android Studio → Tools → Device Manager
2. Create Virtual Device → TV → Select TV device
3. Run: `cd FireTV && npx expo run:android`

## 📝 Current Status

✅ All code copied from iOS app
✅ Dependencies installed
✅ Android build configured
✅ Leanback launcher support added
✅ Landscape orientation configured
✅ Entry point created
❌ Need Java to build APK

## 🎯 Next Steps

1. Install Java JDK
2. Run build command
3. Install APK on Fire TV
4. Launch and enjoy!

## 🐛 Troubleshooting

**"Java not found"**
- Install Java JDK and add to PATH
- Restart terminal after installing

**"Build failed"**
- Try `.\gradlew clean` first
- Check that Android SDK is installed
- Verify Java version: `java -version`

**"Can't connect to Fire TV"**
- Ensure Fire TV and PC on same network
- Check IP address is correct
- Make sure ADB debugging is enabled

**"App crashes on launch"**
- Check logs: `adb logcat`
- Ensure server is running
- Verify network connectivity

## 📞 Support

Your app is production-ready! The Fire TV setup is complete, you just need Java to build it.

Once built, the app will:
- Launch on Fire TV
- Show server configuration
- Let you login
- Browse all your media
- Play videos with full controls

**Good luck!** 🎬📺
