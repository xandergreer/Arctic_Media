# Building IPA in Xcode - Step by Step Guide

This guide walks you through building an IPA file from your Expo React Native app using Xcode.

## Prerequisites

1. **macOS** (required for iOS development)
2. **Xcode** installed (latest version recommended)
3. **Xcode Command Line Tools**: `xcode-select --install`
4. **CocoaPods** installed: `sudo gem install cocoapods`
5. **Node.js 18+** installed
6. **Apple Developer Account** (free account works for testing, paid account required for App Store distribution)

## Step 1: Install Dependencies

```bash
cd IOS
npm install
```

## Step 2: Generate Native iOS Project

Expo apps need to be "prebuilt" to generate native iOS project files:

```bash
npx expo prebuild --platform ios
```

This will create an `ios/` directory with the native Xcode project.

## Step 3: Install CocoaPods Dependencies

```bash
cd ios
pod install
cd ..
```

## Step 4: Open Project in Xcode

```bash
open ios/arctic-media.xcworkspace
```

**Important**: Always open the `.xcworkspace` file, NOT the `.xcodeproj` file (CocoaPods requires the workspace).

## Step 5: Configure Code Signing in Xcode

1. In Xcode, select your project in the navigator (left sidebar)
2. Select the **arctic-media** target
3. Go to **Signing & Capabilities** tab
4. Check **"Automatically manage signing"**
5. Select your **Team** (your Apple Developer account)
6. Xcode will automatically create a provisioning profile

**Note**: If you see errors:
- Make sure you're signed into Xcode with your Apple ID (Xcode → Settings → Accounts)
- For App Store distribution, you need a paid Apple Developer account
- For testing on your device, a free account works

## Step 6: Configure Bundle Identifier (if needed)

The bundle identifier is already set to `com.arcticmedia.app` in `app.json`. If you need to change it:

1. In Xcode, go to **General** tab
2. Update **Bundle Identifier** to match your Apple Developer account
3. It should be unique (e.g., `com.yourname.arcticmedia`)

## Step 7: Select Build Target

1. At the top of Xcode, next to the play button, select:
   - **Any iOS Device (arm64)** for a generic device build
   - Or select your connected iPhone/iPad for device-specific build
   - Or select a simulator for testing

## Step 8: Build the IPA

### Option A: Build for Device (Ad Hoc Distribution)

1. In Xcode, go to **Product → Archive**
2. Wait for the build to complete
3. The **Organizer** window will open
4. Select your archive
5. Click **Distribute App**
6. Select **Ad Hoc** (for testing on registered devices)
7. Follow the wizard to export the IPA

### Option B: Build for App Store

1. Same steps as above, but select **App Store Connect** instead of Ad Hoc
2. You'll need a paid Apple Developer account for this

### Option C: Build for Development (Fastest Testing)

1. Connect your iPhone via USB
2. Select your device in Xcode
3. Click the **Play** button (▶️) or press `Cmd + R`
4. The app will install and run on your device

## Step 9: Export IPA Location

After distribution, the IPA will be saved to:
- Default location: `~/Desktop/` or a location you choose during export
- You can also find it in Xcode Organizer → Archives

## Troubleshooting

### "No such module 'ExpoModulesCore'"
```bash
cd ios
pod install
cd ..
```

### "Code signing is required"
- Make sure you've selected a Team in Signing & Capabilities
- Try cleaning build folder: **Product → Clean Build Folder** (Shift + Cmd + K)

### "Provisioning profile not found"
- In Xcode, go to **Signing & Capabilities**
- Uncheck and recheck **"Automatically manage signing"**
- Select your Team again

### Build fails with CocoaPods errors
```bash
cd ios
pod deintegrate
pod install
cd ..
```

### "Command PhaseScriptExecution failed"
- Open Xcode → Preferences → Locations
- Make sure **Command Line Tools** is set to your Xcode version

## Alternative: Use EAS Build (Cloud Build)

If you prefer cloud-based building (easier, no Mac required for building):

```bash
# Install EAS CLI
npm install -g eas-cli

# Login to Expo
eas login

# Build for iOS
eas build --platform ios
```

This will build your app in the cloud and give you a download link for the IPA.

## Next Steps

After building your IPA:
1. **Test on device**: Install via TestFlight or ad-hoc distribution
2. **Submit to App Store**: Use Xcode Organizer → Distribute App → App Store Connect
3. **Enterprise Distribution**: If you have an enterprise account, you can distribute internally

## Important Notes

- The first build takes longer (downloading dependencies, compiling)
- Make sure your Apple Developer account is active
- For App Store submission, you'll need to create an App Store Connect record first
- Keep your signing certificates secure and backed up


