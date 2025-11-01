# Quick Start Guide

## Prerequisites
- **Node.js 18+** installed ([Download here](https://nodejs.org/))
- **Expo Go app** on your iOS device ([App Store](https://apps.apple.com/app/expo-go/id982107779))

## Get the App Running

### 1. Install Dependencies
```bash
cd IOS
npm install
```

### 2. Start Expo Development Server
```bash
npx expo start
```

This will:
- Start the Metro bundler
- Show a QR code in your terminal
- Open a web interface at http://localhost:19002

### 3. Run on Your Device

**Option A: Use Expo Go (Easiest)**
1. Open the **Expo Go** app on your iPhone
2. Scan the QR code from the terminal
3. The app will load on your device!

**Option B: iOS Simulator (Mac only)**
1. Press `i` in the terminal after running `npx expo start`
2. This will open the iOS Simulator automatically

**Option C: Android Emulator**
1. Have Android Studio running with an emulator
2. Press `a` in the terminal after running `npx expo start`

## What You'll See

1. **Server Configuration Screen** - Enter your Arctic Media server URL
   - Examples: `arcticmedia.space` or `192.168.1.100:8000`
   
2. **Login Screen** - After connecting to server, login with your credentials

3. **Home Screen** - Browse your media library

4. **TV Shows** - Browse all TV series

5. **Video Player** - Stream episodes using HLS

## Troubleshooting

### "npm not found"
- Install Node.js from https://nodejs.org/
- Restart your terminal after installing

### "Port already in use"
- Expo uses port 19000 by default
- Kill the process: `npx expo start --port 19001`

### Connection Issues
- Make sure your Arctic Media server is running
- Check that your device is on the same network as the server
- Verify the server URL in the app matches your server's address

### Expo Go Compatibility
- Some native modules may require a development build
- If you get module errors, run: `npx expo prebuild` then use a dev build

## Next Steps

- Edit `src/config.ts` to change default server settings
- Customize screens in `src/screens/`
- Add features in `src/api/` for server communication

