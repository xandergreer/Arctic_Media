# Arctic Media Mobile App Setup Guide

This guide will help you set up the Arctic Media React Native mobile app for Fire TV and Android devices.

## Prerequisites

- Node.js 18+ installed on your Windows machine
- Android Studio with Android SDK
- Your Arctic Media server running and accessible on your local network

## Quick Setup

### 1. Update Server Configuration

Edit `IOS/src/config.ts` and update the server IP address:

```typescript
export const CONFIG = {
  // Update this to match your Arctic Media server IP and port
  SERVER_URL: 'http://YOUR_SERVER_IP:8085',
  API_BASE: 'http://YOUR_SERVER_IP:8085/api',
  // ... rest of config
};
```

**Important**: Replace `YOUR_SERVER_IP` with your actual Arctic Media server's IP address on your local network.

### 2. Install Dependencies

```bash
npm install
```

### 3. Test on Android Emulator

```bash
npx react-native run-android
```

### 4. Build APK for Fire TV

```bash
cd android
./gradlew assembleRelease
```

The APK will be created at: `android/app/build/outputs/apk/release/app-release.apk`

## Fire TV Installation

1. **Enable Developer Options**:
   - Go to Settings > Device > About
   - Click "Build" 7 times to enable developer options

2. **Enable ADB**:
   - Go to Settings > Developer Options
   - Enable "ADB Debugging"

3. **Install APK**:
   - Use ADB: `adb install app-release.apk`
   - Or use a file manager app to install the APK

## Features

- **Authentication**: Login with your Arctic Media credentials
- **TV Shows**: Browse all TV series in your library
- **Seasons & Episodes**: Navigate through show content
- **Video Player**: Stream content using HLS (HTTP Live Streaming)
- **TV-Friendly UI**: Optimized for remote control navigation

## Troubleshooting

### Connection Issues
- Verify your server IP address in `IOS/src/config.ts`
- Ensure your Arctic Media server is running
- Check that your device can reach the server IP

### Build Issues
- Make sure Android Studio and SDK are properly installed
- Try cleaning the build: `cd android && ./gradlew clean`

### Video Playback Issues
- Verify HLS streaming is working on your server
- Check that the media files are accessible

## Customization

### Adding New Screens
1. Create a new screen in `IOS/src/screens/`
2. Add it to the navigation in `IOS/src/navigation/AppNavigator.tsx`
3. Update the types in `IOS/src/types/index.ts`

### Styling
- Colors and themes are defined in `IOS/src/config.ts`
- Use the CONFIG.THEME object for consistent styling

### API Integration
- Add new API functions in `IOS/src/api/`
- Follow the existing pattern for error handling and loading states

## Support

If you encounter issues:
1. Check the console logs for error messages
2. Verify your server configuration
3. Test the API endpoints directly in a browser

## Next Steps

- Add movie browsing functionality
- Implement search and filtering
- Add offline caching
- Push notifications for new content
- iOS app development
