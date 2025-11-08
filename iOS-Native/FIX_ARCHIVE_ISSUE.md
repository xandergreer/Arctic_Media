# Fix: Archive Button Grayed Out in Xcode

## Quick Fixes (Try These First)

### 1. Select Device Target (Most Common Issue)
- Look at the device selector in the toolbar (next to the play button)
- If it says "iPhone 15 Simulator" or any simulator → **This is the problem!**
- Click the device selector
- Choose **"Any iOS Device (arm64)"** or your connected iPhone
- Archive should now be enabled ✅

### 2. Check Scheme
- Click the scheme selector (next to device selector)
- Make sure your app scheme is selected (usually "ArcticMedia")
- If no scheme exists, create one:
  - Click scheme selector → "Edit Scheme..."
  - Make sure "Archive" is checked/enabled

### 3. Build First
- Sometimes you need to build before archiving
- Press `Cmd + B` to build
- Wait for build to complete
- Then try Archive again

### 4. Clean Build Folder
- **Product → Clean Build Folder** (or `Shift + Cmd + K`)
- Wait for it to finish
- Try Archive again

## Step-by-Step Fix

### Step 1: Check Device Selector
```
Toolbar: [Scheme] [Device] [Play Button]
         ↑        ↑
    Make sure   Must be device,
    correct    not simulator!
```

### Step 2: Verify Project Settings
1. Click your project in the navigator (left sidebar)
2. Select your target (ArcticMedia)
3. Go to **"General"** tab
4. Check **"Deployment Target"** is set (iOS 16.0+)
5. Go to **"Signing & Capabilities"**
6. Make sure a **Team** is selected
7. Enable **"Automatically manage signing"**

### Step 3: Check for Build Errors
1. Try building: `Cmd + B`
2. Check for any red errors in the issue navigator
3. Fix any errors first
4. Then try Archive

### Step 4: Verify Scheme
1. Click scheme selector (next to device)
2. Select **"Edit Scheme..."**
3. Go to **"Archive"** section
4. Make sure it's enabled/checked
5. Click **"Close"**

## Still Not Working?

### Check These:

1. **Is the project properly configured?**
   - File → Project Settings
   - Make sure project is valid

2. **Are you in the right workspace?**
   - If using CocoaPods, open `.xcworkspace` not `.xcodeproj`

3. **Is Xcode up to date?**
   - Xcode → About Xcode
   - Update if needed

4. **Restart Xcode**
   - Quit Xcode completely
   - Reopen the project
   - Try again

## Visual Guide

```
✅ CORRECT:
[ArcticMedia] [Any iOS Device (arm64)] [▶️]
              ↑
         Device selected = Archive enabled

❌ WRONG:
[ArcticMedia] [iPhone 15 Simulator] [▶️]
              ↑
         Simulator = Archive disabled
```

## Alternative: Build via Command Line

If Archive still doesn't work, use Terminal:

```bash
cd /path/to/iOS-Native

# Build archive
xcodebuild -project ArcticMedia.xcodeproj \
           -scheme ArcticMedia \
           -configuration Release \
           -archivePath ./build/ArcticMedia.xcarchive \
           archive
```

Then export:
```bash
xcodebuild -exportArchive \
           -archivePath ./build/ArcticMedia.xcarchive \
           -exportPath ./build \
           -exportOptionsPlist ExportOptions.plist
```

## Most Likely Solution

**99% of the time**, it's because you have a **simulator selected** instead of a device.

**Fix**: Click device selector → Choose "Any iOS Device (arm64)"

Try that first! 🎯

