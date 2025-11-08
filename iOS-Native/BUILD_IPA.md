# Building IPA for Testing - Step by Step

## Method 1: Using Xcode GUI (Recommended)

### Step 1: Select Device Target
1. In Xcode toolbar, click the device selector (next to the play button)
2. Select **"Any iOS Device (arm64)"** or your connected iPhone/iPad
   - ⚠️ **Important**: You cannot build IPA for simulator, must use a real device target

### Step 2: Archive
1. Go to **Product → Archive**
   - Or press: `Cmd + Shift + B` (Build) then **Product → Archive**
2. Wait for the build to complete (first time takes longer)
3. The **Organizer** window will open automatically

### Step 3: Distribute App
1. In Organizer, select your archive (should be the latest one)
2. Click **"Distribute App"** button
3. Select **"Ad Hoc"** (for testing on registered devices)
4. Click **Next**

### Step 4: Distribution Options
1. Leave default options selected
2. Click **Next**

### Step 5: Signing
1. Choose **"Automatically manage signing"** (recommended)
2. Select your **Team** (Apple Developer account)
3. Click **Next**

### Step 6: Review & Export
1. Review the summary
2. Click **Export**
3. Choose save location (Desktop is good)
4. Click **Export**
5. ✅ **IPA file is now ready!**

## Method 2: Using Command Line (Faster)

### Build Archive
```bash
# In Terminal, navigate to your project
cd iOS-Native

# Build archive
xcodebuild -workspace ArcticMedia.xcworkspace \
           -scheme ArcticMedia \
           -configuration Release \
           -archivePath ./build/ArcticMedia.xcarchive \
           archive
```

### Export IPA
```bash
# Export IPA (requires export options plist)
xcodebuild -exportArchive \
           -archivePath ./build/ArcticMedia.xcarchive \
           -exportPath ./build \
           -exportOptionsPlist ExportOptions.plist
```

## Installing IPA on Device

### Option 1: Using Finder (macOS Catalina+)
1. Connect your iPhone/iPad via USB
2. Open **Finder**
3. Select your device in sidebar
4. Drag the IPA file to the device
5. Sync to install

### Option 2: Using Xcode
1. Connect device via USB
2. In Xcode: **Window → Devices and Simulators**
3. Select your device
4. Click **"+"** under "Installed Apps"
5. Select your IPA file
6. Click **Install**

### Option 3: Using TestFlight (Recommended for Testing)
1. Upload IPA to App Store Connect
2. Add testers in TestFlight
3. Testers install via TestFlight app

## Troubleshooting

### "No devices available"
- Connect a physical iOS device via USB
- Or select "Any iOS Device (arm64)" in device selector

### "Signing certificate not found"
- Go to **Signing & Capabilities** in Xcode
- Select your **Team**
- Enable **"Automatically manage signing"**

### "Provisioning profile not found"
- Xcode will create one automatically if "Automatically manage signing" is enabled
- Or create one manually in Apple Developer portal

### "Archive option is grayed out"
- Make sure you selected a device target (not simulator)
- Clean build folder: **Product → Clean Build Folder** (`Shift + Cmd + K`)

### "IPA won't install on device"
- Make sure device UDID is registered in your provisioning profile
- For Ad Hoc: Add device UDID in Apple Developer portal
- For Development: Device must be registered in your team

## Quick Checklist

- [ ] Selected device target (not simulator)
- [ ] Team selected in Signing & Capabilities
- [ ] Archive completed successfully
- [ ] Selected "Ad Hoc" distribution
- [ ] IPA exported to chosen location
- [ ] Device UDID registered (for Ad Hoc)

## IPA File Location

After export, your IPA will be in:
- The location you chose (usually Desktop)
- Or: `~/Library/Developer/Xcode/Archives/` (archives are stored here)

## Next Steps After Building

1. **Test on device**: Install IPA on your iPhone/iPad
2. **Share with testers**: Send IPA file (they need registered devices)
3. **Upload to TestFlight**: For easier distribution
4. **Submit to App Store**: When ready for production

---

**That's it!** Your IPA is ready for testing! 🎉

