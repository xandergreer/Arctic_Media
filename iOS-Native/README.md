# Arctic Media - Native iOS App

A native Swift iOS app for accessing your Arctic Media server.

## Features

- ✅ Server configuration and validation
- ✅ User authentication
- ✅ Browse TV shows and movies
- ✅ View seasons and episodes
- ✅ Video playback with AVKit (HLS streaming)
- ✅ Modern SwiftUI interface
- ✅ Persistent authentication

## Setup

### Prerequisites

- macOS with Xcode 14+ installed
- iOS 16.0+ deployment target
- Apple Developer account (for device testing)

### Installation

1. **Open the project:**
   ```bash
   cd iOS-Native
   open ArcticMedia.xcodeproj
   ```

2. **Configure signing:**
   - Select the project in Xcode
   - Go to "Signing & Capabilities"
   - Select your development team
   - Xcode will automatically manage signing

3. **Build and run:**
   - Select a simulator or connected device
   - Press `Cmd + R` to build and run

## Project Structure

```
ArcticMedia/
├── ArcticMediaApp.swift      # App entry point
├── ContentView.swift         # Root view with navigation logic
├── Models/                   # Data models
│   ├── User.swift
│   ├── MediaItem.swift
│   ├── TVShow.swift
│   └── ServerConfig.swift
├── Managers/                 # State management
│   └── AuthManager.swift
├── Services/                 # API client
│   └── APIService.swift
└── Views/                    # SwiftUI views
    ├── ServerConfigView.swift
    ├── LoginView.swift
    ├── MainTabView.swift
    ├── HomeView.swift
    ├── TVShowsView.swift
    ├── MoviesView.swift
    ├── PlayerView.swift
    └── SettingsView.swift
```

## API Integration

The app connects to your Arctic Media server using the following endpoints:

- `POST /auth/login` - User authentication
- `GET /auth/me` - Get current user
- `GET /api/movies` - List movies
- `GET /api/tv` - List TV shows
- `GET /api/tv/seasons` - Get seasons for a show
- `GET /api/tv/episodes` - Get episodes for a season
- `GET /stream/{itemId}/master.m3u8` - HLS streaming URL

## Building for Distribution

### Development Build

1. In Xcode, select **Product → Archive**
2. Wait for the build to complete
3. Click **Distribute App**
4. Choose **Development** or **Ad Hoc** distribution
5. Export the IPA

### App Store Build

1. Archive the app as above
2. Select **App Store Connect** distribution
3. Upload to App Store Connect
4. Submit for review in App Store Connect

## Requirements

- iOS 16.0+
- Swift 5.9+
- Xcode 14+

## Notes

- The app uses HLS streaming for video playback
- Authentication tokens are stored securely in UserDefaults
- Server URLs are persisted between app launches
- The app automatically handles authentication state

## Troubleshooting

### Build Errors

- Make sure you've selected a development team in Signing & Capabilities
- Clean build folder: **Product → Clean Build Folder** (Shift + Cmd + K)

### Connection Issues

- Verify your server URL is correct
- Check that your device/simulator can reach the server
- Ensure the server is running and accessible

### Video Playback Issues

- Verify HLS streaming is enabled on your server
- Check that the media files are accessible
- Ensure network connectivity is stable

