# Quick Build Guide - Fire TV App

## 🚀 Fastest Way to Build

### Option 1: Use the Build Script (Recommended)

```powershell
cd FireTV
.\build-and-deploy.ps1
```

Or if you want to build and install in one step:
```powershell
.\build-and-deploy.ps1 -FireTVIP 192.168.1.100
```

Replace `192.168.1.100` with your Fire TV's IP address.

### Option 2: Manual Build

```powershell
cd FireTV\android
.\gradlew.bat assembleRelease
```

The APK will be at: `app\build\outputs\apk\release\app-release.apk`

---

## 📋 Prerequisites Checklist

Before building, make sure you have:

- [ ] **Java JDK 17+** installed
  - Download: https://adoptium.net/temurin/releases/
  - Or install Android Studio (includes Java + Android SDK)
  - Verify: `java -version`

- [ ] **Android SDK** (optional but recommended)
  - Comes with Android Studio
  - Or install standalone: https://developer.android.com/studio#command-tools

- [ ] **Node.js dependencies installed**
  - Already done ✓ (node_modules exists)

---

## 🔧 If Java is Not Installed

### Install Java JDK (Quick)

1. **Download Eclipse Temurin (OpenJDK)**
   - Visit: https://adoptium.net/temurin/releases/
   - Choose: Windows x64, JDK 17 or higher
   - Download and run installer

2. **Add Java to PATH**
   - The installer usually does this automatically
   - If not, add to PATH: `C:\Program Files\Eclipse Adoptium\jdk-XX.X.X.X-hotspot\bin`

3. **Verify Installation**
   ```powershell
   java -version
   ```

### Or Install Android Studio (Includes Everything)

1. **Download Android Studio**
   - Visit: https://developer.android.com/studio
   - Install with default settings
   - It includes Java JDK and Android SDK

2. **Set JAVA_HOME** (if needed)
   - Usually set automatically by Android Studio
   - Or set manually: `C:\Program Files\Android\Android Studio\jbr`

---

## 📱 Installing on Fire TV

### Step 1: Enable Developer Mode

1. On your Fire TV: **Settings → Device → About**
2. Click on **"Build"** 7 times
3. You'll see "You are now a developer!"

### Step 2: Enable ADB

1. **Settings → Developer Options**
2. Enable **"ADB Debugging"**
3. Note your Fire TV's IP address:
   - **Settings → Device → About → Network**
   - Write down the IP (e.g., `192.168.1.100`)

### Step 3: Install APK

**Option A: Using ADB (Recommended)**
```powershell
# Connect to Fire TV
adb connect 192.168.1.100

# Install APK
adb install -r FireTV\android\app\build\outputs\apk\release\app-release.apk
```

**Option B: Using the Build Script**
```powershell
cd FireTV
.\build-and-deploy.ps1 -FireTVIP 192.168.1.100
```

**Option C: Manual Transfer**
1. Copy APK to USB drive
2. Plug into Fire TV
3. Use a file manager app (like ES File Explorer) to install

---

## ✅ Verification

After building, verify the APK exists:
```
FireTV\android\app\build\outputs\apk\release\app-release.apk
```

File size should be approximately 20-50 MB.

---

## 🐛 Troubleshooting

### "Java not found"
- Install Java JDK 17+ from https://adoptium.net/
- Restart terminal after installation
- Verify: `java -version`

### "Gradle build failed"
- Make sure Java is installed and in PATH
- Try: `.\gradlew.bat clean` then rebuild
- Check internet connection (Gradle downloads dependencies)

### "ADB not found"
- Install Android Platform Tools
- Or use Android Studio (includes ADB)
- Or install manually: https://developer.android.com/tools/releases/platform-tools

### "Can't connect to Fire TV"
- Ensure Fire TV and PC are on the same network
- Verify IP address is correct
- Check that ADB debugging is enabled on Fire TV
- Firewall might be blocking ADB connection

### Build takes too long
- First build downloads Gradle and dependencies (5-10 minutes)
- Subsequent builds are faster (1-2 minutes)
- Ensure good internet connection

---

## 🎯 Quick Commands Reference

```powershell
# Build APK
cd FireTV\android
.\gradlew.bat assembleRelease

# Build and install in one step
cd FireTV
.\build-and-deploy.ps1 -FireTVIP YOUR_IP

# Connect to Fire TV
adb connect YOUR_IP

# Install APK
adb install -r path\to\app-release.apk

# View Fire TV logs
adb logcat | findstr "ArcticMedia"

# Uninstall app
adb uninstall com.arcticmedia.firetv
```

---

## 📝 Next Steps After Installation

1. Launch app from Fire TV Apps menu
2. Enter your Arctic Media server URL
3. Login with your credentials
4. Start streaming!

---

**Need help?** Check `BUILD_INSTRUCTIONS.md` for detailed information.

