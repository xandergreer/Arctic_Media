#!/bin/bash
# Build IPA Script for Arctic Media iOS App (macOS)

echo "=== Arctic Media iOS Build Script ==="
echo ""

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Error: This script requires macOS for local iOS builds."
    echo ""
    echo "For Windows, use: build-ipa.ps1"
    echo "Or use EAS Build: eas build --platform ios"
    exit 1
fi

echo "Detected: macOS"
echo ""
echo "=== Setting up for Local Build ==="
echo ""

# Check if dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Check if native project exists
if [ ! -d "ios" ]; then
    echo "Generating native iOS project..."
    npx expo prebuild --platform ios
fi

# Install CocoaPods
echo "Installing CocoaPods dependencies..."
cd ios
pod install
cd ..

echo ""
echo "=== Opening Xcode ==="
echo ""
echo "Opening Xcode workspace..."

if [ -d "ios/arctic-media.xcworkspace" ]; then
    open ios/arctic-media.xcworkspace
    echo ""
    echo "Xcode should now be open!"
    echo ""
    echo "Next steps in Xcode:"
    echo "1. Select your project > Target > Signing & Capabilities"
    echo "2. Enable 'Automatically manage signing' and select your Team"
    echo "3. Product > Archive to build"
    echo "4. Distribute App to export IPA"
else
    echo "Workspace not found. Please run: npx expo prebuild --platform ios"
fi

echo ""
echo "Done! Check BUILD_IPA_GUIDE.md for detailed instructions."


