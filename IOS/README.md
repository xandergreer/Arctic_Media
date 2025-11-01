# Arctic Media iOS App

React Native iOS app built with Expo for accessing your Arctic Media server.

## Setup

### Prerequisites
- Node.js 18+ installed
- Expo CLI (install with `npm install -g expo-cli` or use `npx expo`)

### Installation

1. **Install dependencies:**
   ```bash
   cd IOS
   npm install
   ```

2. **Configure server:**
   Edit `src/config.ts` and update the server URL:
   ```typescript
   export const CONFIG = {
     SERVER_URL: 'http://YOUR_SERVER_IP:8085',
     API_BASE: 'http://YOUR_SERVER_IP:8085/api',
     // ...
   };
   ```

3. **Start Expo development server:**
   ```bash
   npx expo start
   ```
   
   This will:
   - Start the Metro bundler
   - Show a QR code you can scan with the Expo Go app on your phone
   - Provide options to run on iOS simulator/emulator

## Development

### Running on Device

1. Install **Expo Go** app on your iOS device from the App Store
2. Scan the QR code shown when you run `npx expo start`
3. The app will load on your device

### Running on iOS Simulator

1. Install Xcode (Mac only)
2. Run `npx expo start --ios`
3. Expo will open the iOS Simulator automatically

### Running on Android

1. Have Android Studio installed with an emulator running
2. Run `npx expo start --android`

## Building

### Development Build
```bash
npx expo build:ios
```

### Production Build
```bash
eas build --platform ios
```

(Requires Expo Application Services account)

## Features

- 🔧 **Server Configuration**: Connect to any Arctic Media server
- 🔐 **Authentication**: Login with your Arctic Media credentials
- 📺 **TV Shows**: Browse all series in your library
- 📚 **Seasons**: Navigate through show seasons
- 🎬 **Episodes**: View episode lists
- ▶️ **Video Player**: Stream content using HLS
- 📱 **iOS Optimized**: Native iOS experience

## Project Structure

```
IOS/
├── App.tsx                 # Main app entry point
├── src/
│   ├── api/               # API client functions
│   ├── navigation/        # Navigation setup
│   ├── screens/          # Screen components
│   ├── store/            # State management (Zustand)
│   ├── types/            # TypeScript types
│   └── config.ts         # App configuration
├── app.json              # Expo configuration
├── package.json          # Dependencies
└── tsconfig.json         # TypeScript config
```

## Troubleshooting

### Connection Issues
- Verify server URL in `src/config.ts`
- Ensure Arctic Media server is running
- Check that device/simulator can reach the server

### Expo Go Compatibility
- Some native modules (like `react-native-video`) may require a custom development build
- If you encounter issues, run: `npx expo prebuild` then use development build

## Notes

- Uses Expo SDK ~50.0.0
- React Native 0.73.0
- React Navigation for navigation
- Zustand for state management

