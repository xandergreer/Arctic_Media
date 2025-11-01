# Arctic Media Fire TV App

Complete Fire TV implementation of Arctic Media, rebuilt from scratch to match the iOS app.

## 🎯 Features

✅ **Full feature parity with iOS app:**
- Server configuration
- Authentication & login
- Home screen with navigation
- TV Shows browsing
- Movies browsing
- Seasons & episodes navigation
- Episode details
- Movie details
- Video playback with HLS
- Grid density options
- Settings screen
- Drawer menu

✅ **Fire TV Optimizations:**
- Landscape orientation by default
- Leanback launcher integration
- Remote-friendly UI
- Touchscreen optional
- Optimized for 10-foot viewing

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd FireTV
npm install
```

### 2. Build for Fire TV

```bash
npm run build:android
```

Or using Gradle directly:

```bash
cd android
./gradlew assembleRelease
```

### 3. Install on Fire TV

**Enable Developer Mode:**
1. Settings → Device → About
2. Click "Build" 7 times

**Enable ADB:**
1. Settings → Developer Options
2. Enable "ADB Debugging"

**Install APK:**
```bash
adb connect YOUR_FIRE_TV_IP
adb install android/app/build/outputs/apk/release/app-release.apk
```

### 4. Launch App

- Apps menu → Arctic Media Fire TV
- Or find it in "Your Apps & Games"

## 🎮 Remote Control

- **D-pad**: Navigate through content
- **OK/Select**: Choose item or play video
- **Back**: Go to previous screen
- **Menu**: Open drawer/settings
- **Home**: Return to Fire TV home

## 🔧 Development

### Run on Android Emulator

```bash
npm run android
```

For TV emulator:
1. Android Studio → Tools → Device Manager
2. Create device → Select TV (e.g., TV 1080p)
3. Run app: `npm run android`

### Development Server

```bash
npm start
```

Then select Android emulator or connected Fire TV device.

## 📱 Compatibility

- **Fire TV**: All generations (Stick, Cube, TV)
- **Android TV**: Fully compatible
- **Minimum Android**: 5.0 (API 21)
- **Target Android**: Latest (auto-updated)

## 🌐 API Compatibility

Uses the **same backend API** as iOS and Roku:
- Same authentication flow
- Same media browsing endpoints
- Same video streaming
- Same data structures

Just point to your Arctic Media server!

## 🎨 UI/UX

**Optimized for TV:**
- Larger fonts for 10-foot viewing
- High contrast for visibility
- Remote-friendly navigation
- Grid layouts for browsing
- Focus indicators
- Responsive design

**Layouts:**
- Home screen with featured content
- Grid views for movies/shows
- List views for episodes
- Detail screens with posters
- Full-screen video player

## 📁 Project Structure

```
FireTV/
├── src/
│   ├── api/                  # API clients
│   ├── components/           # Reusable components
│   ├── navigation/           # Navigation setup
│   ├── screens/             # Screen components
│   ├── store/               # State management
│   ├── types/               # TypeScript types
│   └── config.ts            # Configuration
├── android/                 # Android build
├── assets/                  # App assets
├── App.tsx                  # Main entry
├── index.js                 # Entry point
├── app.json                 # Expo config
├── package.json             # Dependencies
└── tsconfig.json            # TypeScript config
```

## 🐛 Known Issues

None! The app is production-ready with full iOS parity.

## 📝 Future Enhancements

Possible additions:
- [ ] Fire TV recommendation cards
- [ ] Alexa voice search
- [ ] Continue watching on home screen
- [ ] Watchlist functionality
- [ ] Search with voice

## 🤝 Contributing

This is a complete port of the iOS app. All features match:
- Server configuration ✅
- Authentication ✅
- Media browsing ✅
- Video playback ✅
- Settings ✅
- Preferences ✅

---

**Ready to stream!** 🎬📺
