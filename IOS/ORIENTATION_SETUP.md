# Landscape Mode Setup Guide

## Current Status

Your app is configured to support landscape orientation. The video player should work in both portrait and landscape modes.

## Option 1: Manual Rotation (Works with Expo Go)

Even without automatic orientation locking, you can:
1. **Manually rotate your device** when viewing videos
2. The app will rotate to landscape automatically based on device orientation
3. This works because `app.json` has `"orientation": "default"` and iOS infoPlist allows landscape orientations

## Option 2: Automatic Landscape Locking (Requires Development Build)

For automatic landscape locking when videos play, you need a **development build** that includes the `expo-screen-orientation` native module.

### Building with EAS (Recommended for Windows)

Since you're on Windows and can't build iOS locally:

1. **Install EAS CLI:**
   ```bash
   npm install -g eas-cli
   ```

2. **Login to Expo account:**
   ```bash
   eas login
   ```
   (Create a free account if needed)

3. **Build development build for iOS:**
   ```bash
   cd IOS
   eas build --profile development --platform ios
   ```

4. **Install on device:**
   - EAS will provide a download link
   - Install the `.ipa` file on your iOS device using:
     - TestFlight (if you have Apple Developer account)
     - Or install directly via EAS (follow the provided instructions)

5. **Run the development client:**
   ```bash
   npx expo start --dev-client
   ```

### What This Does

- Creates an iOS app with all native modules included
- `expo-screen-orientation` will work properly
- Videos will automatically lock to landscape when playing
- Unlocks when you exit the player

## Testing Manual Rotation

1. Start your app: `npx expo start`
2. Navigate to a video and start playing
3. **Rotate your device** to landscape
4. The video should rotate automatically

If manual rotation works but you want automatic locking, follow Option 2 above.

## Troubleshooting

### "Orientation not working"
- Check that your device's orientation lock is OFF
- Verify `app.json` has `"orientation": "default"`
- Try manually rotating the device

### "expo-screen-orientation module not found"
- You're using Expo Go (limited native modules)
- Switch to a development build (Option 2 above)
- Or use manual rotation (Option 1)

### "EAS Build failed"
- Make sure you're logged in: `eas login`
- Check that `eas.json` exists in the `IOS` directory
- Verify your Apple Developer account is set up (for production builds)

## Current Configuration

Your `app.json` is already configured correctly:
- ✅ `"orientation": "default"` - allows rotation
- ✅ iOS `infoPlist` includes landscape orientations
- ✅ `expo-screen-orientation` plugin is added

The code will automatically lock to landscape once you have a development build installed.

