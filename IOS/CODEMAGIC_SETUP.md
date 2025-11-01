# Codemagic Setup for iOS Builds

This guide will help you set up Codemagic to automatically build iOS IPA files for your Arctic Media app.

## Prerequisites

1. **Codemagic Account**: Sign up at https://codemagic.io (free tier available)
2. **Expo Account**: Sign up at https://expo.dev (free tier available)
3. **Apple Developer Account**: Required for production builds (TestFlight/App Store)
   - Free tier allows TestFlight builds

## Setup Steps

### 1. Configure Codemagic Project

1. Go to https://codemagic.io and sign in
2. Click "Add application"
3. Connect your repository (GitHub/GitLab/Bitbucket)
4. Select the `IOS` folder or the repository root
5. Select the **codemagic.yaml** workflow file

### 2. Configure Environment Variables

In Codemagic UI, go to **Settings → Environment variables**, create these groups:

#### App Store Credentials (for production builds)
Create group: `app_store_credentials`

Add these variables:
- `APP_STORE_CONNECT_KEY_IDENTIFIER` - Your App Store Connect API Key ID
- `APP_STORE_CONNECT_ISSUER_ID` - Your App Store Connect Issuer ID
- `APP_STORE_CONNECT_PRIVATE_KEY` - Your App Store Connect private key (P8 file content)
- `APPLE_ID` - Your Apple ID email
- `APPLE_APP_SPECIFIC_PASSWORD` - App-specific password for your Apple ID

**How to get App Store Connect API Key:**
1. Go to https://appstoreconnect.apple.com
2. Users and Access → Keys → App Store Connect API
3. Create a new key with "App Manager" or "Admin" role
4. Download the .p8 file (only shown once!)
5. Copy the Key ID and Issuer ID

**How to create App-Specific Password:**
1. Go to https://appleid.apple.com
2. Sign in with your Apple ID
3. Security → App-Specific Passwords
4. Generate a new password

#### Expo Credentials (optional, for private packages)
Create group: `expo_credentials`

Add:
- `EXPO_TOKEN` - Your Expo access token (get from https://expo.dev/accounts/[username]/settings/access-tokens)

### 3. Configure EAS Build

In your local terminal:

```bash
cd IOS
npm install -g eas-cli
eas login
eas build:configure
```

This will:
- Create or update `eas.json`
- Ask about your Apple Developer account
- Set up signing certificates

**For TestFlight/App Store builds:**
- You'll need an Apple Developer account ($99/year)
- EAS will manage certificates automatically

**For ad-hoc/distribution builds:**
- Works with free Apple Developer account
- Can install on up to 100 devices

### 4. Update codemagic.yaml

Edit `IOS/codemagic.yaml` and update:
- Email recipients (line 50, 80): Replace `user@example.com` with your email
- Xcode version if needed (line 10): Check Codemagic's available versions

### 5. Start Your First Build

1. In Codemagic UI, click **"Start new build"**
2. Select the `ios-production` or `ios-preview` workflow
3. Click **"Start build"**
4. Monitor the build progress
5. Download the IPA from the build artifacts

## Build Profiles

The workflows support two build profiles:

### Production (`ios-production`)
- Uses `eas.json` production profile
- Creates signed IPA for App Store/TestFlight
- Requires Apple Developer account

### Preview (`ios-preview`)
- Uses `eas.json` preview profile
- Creates ad-hoc/distribution build
- Can install on registered devices

## Manual Build Alternative

You can also build manually using EAS CLI:

```bash
cd IOS
eas build --platform ios --profile production
```

Then download the IPA from the EAS dashboard: https://expo.dev/accounts/[username]/projects/arctic-media/builds

## Troubleshooting

### "EAS CLI not found"
- Make sure the `npm install -g eas-cli@latest` step runs
- Check Node.js version (20+ recommended)

### "No Apple Developer account"
- Use preview profile for ad-hoc builds
- Or sign up at https://developer.apple.com/programs/

### "Build fails with signing errors"
- Run `eas credentials` locally to set up certificates
- Make sure your Apple Developer account is configured

### "EXPO_TOKEN required"
- Only needed for private Expo packages
- Create token at https://expo.dev/accounts/[username]/settings/access-tokens
- Add to Codemagic environment variables

## What You Get

After a successful build:
- **IPA file**: Ready to install on iOS devices
- **Email notification**: Build status sent to your email
- **Download link**: Available in Codemagic dashboard
- **Automatic signing**: EAS handles all certificates

## Next Steps

1. Set up TestFlight distribution (optional)
2. Configure automatic builds on git push (webhook)
3. Add more build variants (development, staging, etc.)

## Resources

- Codemagic Docs: https://docs.codemagic.io
- EAS Build Docs: https://docs.expo.dev/build/introduction/
- Expo CLI: https://docs.expo.dev/workflow/expo-cli/

