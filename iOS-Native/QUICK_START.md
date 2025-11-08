# Quick Start - Native iOS App

## 🚀 Get Started in 5 Minutes

### Step 1: Create Xcode Project

1. Open **Xcode**
2. **File → New → Project**
3. Choose **iOS → App**
4. Settings:
   - Name: `ArcticMedia`
   - Interface: **SwiftUI**
   - Language: **Swift**
5. Save to: `iOS-Native/` folder

### Step 2: Add Files

1. In Xcode, right-click your project
2. **Add Files to "ArcticMedia"...**
3. Select the `ArcticMedia` folder
4. Make sure **"Create groups"** is checked
5. Click **Add**

### Step 3: Configure Project

1. Select project in navigator
2. Go to **Signing & Capabilities**
3. Select your **Team**
4. Enable **"Automatically manage signing"**

### Step 4: Build & Run

1. Select a simulator or device
2. Press **`Cmd + R`**
3. App should launch! 🎉

## 📱 First Launch

1. Enter your server URL (e.g., `http://192.168.1.100:8000`)
2. Tap **Connect**
3. Enter your username/password
4. Start browsing!

## 🏗️ Project Structure

All files are in `ArcticMedia/`:

- **App Files**: `ArcticMediaApp.swift`, `ContentView.swift`
- **Models**: `Models/` folder
- **Services**: `Services/APIService.swift`
- **Managers**: `Managers/AuthManager.swift`
- **Views**: `Views/` folder

## ✅ What's Included

- ✅ Server configuration
- ✅ User authentication
- ✅ TV shows browsing
- ✅ Movies browsing
- ✅ Video playback (HLS)
- ✅ Settings screen

## 🐛 Troubleshooting

### "No such module" errors
- Make sure all files are added to the target
- Clean build: **Product → Clean Build Folder**

### Signing errors
- Select your team in Signing & Capabilities
- Make sure bundle identifier is unique

### Build fails
- Check iOS deployment target is 16.0+
- Verify all Swift files compile without errors

## 📦 Building IPA

1. **Product → Archive**
2. **Distribute App**
3. Choose distribution method
4. Export IPA

That's it! You now have a native iOS app! 🎊

