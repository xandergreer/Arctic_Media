# Fix: Build/Archive Buttons Disabled

## Quick Checks

### 1. Check for Build Errors
- Look at the **Issue Navigator** (left sidebar, exclamation mark icon)
- Any **red errors** will prevent building
- Fix errors first, then try again

### 2. Check Scheme Selection
- Top toolbar: Make sure your **scheme** is selected
- Should say "ArcticMedia" (or your app name)
- If it says "No Scheme" → Create one:
  - Click scheme selector → "New Scheme..."
  - Select your target
  - Click OK

### 3. Check Target Selection
- Click your **project** in navigator (blue icon at top)
- Select your **target** (ArcticMedia)
- Make sure it's not grayed out or missing

### 4. Verify Signing
- With project selected, go to **"Signing & Capabilities"** tab
- Make sure **"Automatically manage signing"** is checked
- Select your **Team**
- If you see red errors here, fix them first

## Step-by-Step Fix

### Step 1: Check Project Navigator
```
Left Sidebar should show:
📁 ArcticMedia (blue icon)
  📁 ArcticMedia (yellow folder)
    📄 ArcticMediaApp.swift
    📄 ContentView.swift
    etc...
```

### Step 2: Select the Project
1. Click the **blue project icon** at the top of navigator
2. You should see project settings in the main area
3. If nothing shows, the project might not be loaded correctly

### Step 3: Check Target
1. Under "TARGETS", click **"ArcticMedia"**
2. Make sure it's not grayed out
3. Check **"General"** tab:
   - Bundle Identifier should be set
   - Deployment Target should be iOS 16.0+

### Step 4: Check for Missing Files
1. Look for any **red file names** in the navigator
2. Red = file missing or not found
3. Right-click → "Delete" then re-add the file

### Step 5: Clean Everything
1. **Product → Clean Build Folder** (`Shift + Cmd + K`)
2. Quit Xcode completely
3. Reopen the project
4. Wait for indexing to finish (bottom right)

## Common Issues

### Issue: "No Scheme"
**Fix:**
1. Click scheme selector (top left)
2. "New Scheme..."
3. Select your target
4. Click OK

### Issue: Signing Errors
**Fix:**
1. Project → Target → Signing & Capabilities
2. Check "Automatically manage signing"
3. Select your Team
4. If still errors, check Bundle Identifier is unique

### Issue: Missing Files
**Fix:**
1. Red files in navigator = missing
2. Right-click → "Delete" (Remove Reference)
3. Right-click project → "Add Files to ArcticMedia..."
4. Re-add the files

### Issue: Xcode Stuck/Indexing
**Fix:**
1. Wait for indexing to finish (bottom right shows progress)
2. Or: **Product → Stop** (if build is running)
3. Or: Restart Xcode

## Nuclear Option: Recreate Project

If nothing works:

1. **Create new project:**
   - File → New → Project
   - iOS → App
   - Name: ArcticMedia
   - SwiftUI, Swift

2. **Add files:**
   - Right-click project → "Add Files..."
   - Select all files from `ArcticMedia/` folder
   - Make sure "Copy items" is checked
   - Add to target: ArcticMedia ✅

3. **Configure:**
   - Signing & Capabilities → Select Team
   - Build Settings → iOS Deployment Target: 16.0

## Quick Test

Try this to see what's wrong:

1. **Product → Clean Build Folder** (`Shift + Cmd + K`)
2. Look at the **Issue Navigator** (⚠️ icon in left sidebar)
3. Check for any **red errors**
4. Read the error messages - they'll tell you what's wrong

## Most Common Causes

1. **Missing files** (red in navigator)
2. **Signing errors** (no team selected)
3. **Build errors** (code issues)
4. **Scheme not set** (no scheme selected)
5. **Xcode indexing** (wait for it to finish)

## Still Stuck?

Check these in order:
- [ ] Project is selected (blue icon)
- [ ] Target exists and is selected
- [ ] Scheme is selected (top toolbar)
- [ ] No red errors in Issue Navigator
- [ ] Signing is configured (Team selected)
- [ ] All files are added to target
- [ ] Xcode finished indexing

Tell me what you see in the Issue Navigator - that will help diagnose! 🔍

