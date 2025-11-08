# Quick Build Guide - Build IPA in 3 Steps

## Option 1: EAS Build (Works on Windows/Mac/Linux) ⭐ Recommended

### Step 1: Install EAS CLI
```bash
npm install -g eas-cli
```

### Step 2: Login
```bash
eas login
```

### Step 3: Build
```bash
cd IOS
eas build --platform ios
```

**That's it!** The build happens in the cloud. You'll get a download link for your IPA.

**Build Types:**
- `eas build --platform ios --profile preview` - For testing (Ad Hoc)
- `eas build --platform ios --profile production` - For App Store

---

## Option 2: Local Build (macOS Only)

### Step 1: Run the build script
```bash
cd IOS
# On macOS:
./build-ipa.sh

# On Windows (PowerShell):
.\build-ipa.ps1
```

### Step 2: Configure in Xcode
1. Xcode will open automatically
2. Select your project → Target → **Signing & Capabilities**
3. Enable **"Automatically manage signing"**
4. Select your **Team**

### Step 3: Build IPA
1. **Product → Archive**
2. **Distribute App**
3. Choose **Ad Hoc** (testing) or **App Store**
4. Export IPA

---

## Which Option Should You Choose?

- **Windows/Linux?** → Use **EAS Build** (Option 1)
- **macOS with Xcode?** → Use **Local Build** (Option 2)
- **Want it fastest?** → Use **EAS Build** (Option 1)

---

## Troubleshooting

### EAS Build Issues
- Make sure you're logged in: `eas login`
- Check your Apple Developer account is linked
- For App Store builds, you need a paid Apple Developer account ($99/year)

### Local Build Issues
- Make sure Xcode is installed: `xcode-select --install`
- Install CocoaPods: `sudo gem install cocoapods`
- If build fails, clean: `cd ios && pod deintegrate && pod install`

---

## Need Help?

See `BUILD_IPA_GUIDE.md` for detailed instructions.


