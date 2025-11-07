# Arctic Media - Samsung TV App

A Tizen web application for Samsung Smart TVs to access your Arctic Media server.

## Features

✅ **Server Configuration** - Connect to any Arctic Media server  
✅ **Device Pairing** - Secure authentication using pairing codes  
✅ **TV Shows** - Browse all TV series in your library  
✅ **Seasons & Episodes** - Navigate through show content  
✅ **HLS Streaming** - Stream content using HTTP Live Streaming  
✅ **TV-Optimized UI** - Designed for remote control navigation  
✅ **Focus Navigation** - Visual focus indicators for easy navigation  

## Prerequisites

### For Development
- **Samsung Tizen Studio** - Download from [Samsung Developer Portal](https://developer.samsung.com/tizen)
- **Samsung TV** - For testing (or Tizen TV Emulator)
- **Arctic Media Server** - Running and accessible on your network

### For Deployment
- Samsung Developer Account (for app signing)
- Tizen Studio installed
- Your Arctic Media server URL

## Setup Instructions

### 1. Install Tizen Studio

1. Download Tizen Studio from: https://developer.samsung.com/tizen
2. Install with default settings
3. Install TV SDK (via Package Manager in Tizen Studio)

### 2. Configure the App

The app will prompt you to enter your server URL on first launch. Alternatively, you can set it in `js/config.js`:

```javascript
Config.defaultServerUrl = 'http://192.168.1.100:8085';
```

### 3. Build the App

#### Option A: Using Tizen Studio (Recommended)

1. Open Tizen Studio
2. File → Import → Tizen → Tizen Project
3. Select the `samsung-tv` folder
4. Right-click project → Build Project
5. Right-click project → Run As → Tizen Web Application

#### Option B: Using Command Line

```bash
# Install Tizen CLI (comes with Tizen Studio)
# Navigate to your project directory
cd samsung-tv

# Build the app
tizen build-web

# Package the app
tizen package -t wgt
```

### 4. Install on Samsung TV

#### Enable Developer Mode on Samsung TV

1. Press **Home** button on remote
2. Go to **Settings** → **General** → **External Device Manager** → **Device Manager**
3. Enable **Developer Mode**
4. Note your TV's IP address (Settings → Network)

#### Install via Tizen Studio

1. In Tizen Studio, right-click project
2. **Run As** → **Tizen Web Application**
3. Select your TV from the device list
4. The app will install and launch automatically

#### Install via Command Line

```bash
# Connect to TV
sdb connect <TV_IP_ADDRESS>

# Install app
tizen install -n arcticmedia.wgt
```

### 5. First Launch

1. **Enter Server URL** - Enter your Arctic Media server address (e.g., `http://192.168.1.100:8085`)
2. **Pair Device** - Enter the pairing code shown on TV at `/pair` page on your server
3. **Browse & Stream** - Start watching your media!

## Project Structure

```
samsung-tv/
├── config.xml          # Tizen app manifest
├── index.html          # Main HTML file
├── icon.png            # App icon (192x192)
├── css/
│   └── styles.css      # TV-optimized styles
├── js/
│   ├── config.js       # Configuration and storage
│   ├── api.js          # API client for Arctic Media
│   ├── navigation.js   # Remote control navigation
│   └── app.js          # Main application logic
└── README.md           # This file
```

## Remote Control Navigation

- **Arrow Keys** - Navigate between items
- **Enter** - Select/Activate item
- **Back/Return** - Go back or close video
- **Exit** - Exit application

## API Integration

The app uses the following Arctic Media API endpoints:

- `POST /api/pair/request` - Request pairing code
- `POST /api/pair/poll` - Poll for authorization
- `GET /api/tv/shows` - Get all TV shows
- `GET /api/tv/seasons?show_id=...` - Get seasons for a show
- `GET /api/tv/episodes?show_id=...&season=...` - Get episodes for a season
- `GET /stream/hls/{file_id}/master.m3u8` - Stream video

## Troubleshooting

### App Won't Install

- Ensure Developer Mode is enabled on TV
- Check TV and computer are on same network
- Verify TV IP address is correct
- Try restarting TV and Tizen Studio

### Can't Connect to Server

- Verify server URL is correct (no trailing slash)
- Check server is running and accessible
- Ensure firewall allows connections
- Try accessing server URL from browser on TV

### Video Won't Play

- Check HLS.js library is loaded (for non-native HLS support)
- Verify file ID is valid
- Check network connection speed
- Ensure server transcoding is working

### Navigation Not Working

- Ensure JavaScript is enabled
- Check browser console for errors
- Verify focusable elements are present
- Try refreshing the app

## Building for Production

### 1. Sign the App

1. Create certificate in Tizen Studio: **Tools** → **Certificate Manager**
2. Create new certificate profile
3. Sign your app with the certificate

### 2. Package for Distribution

```bash
tizen package -t wgt -s <certificate-profile-name>
```

### 3. Test on Multiple TVs

- Test on different Samsung TV models
- Verify remote control works correctly
- Test video playback quality
- Check UI scaling on different resolutions

## Advanced Configuration

### Custom Server URL

Edit `js/config.js` to set a default server URL:

```javascript
Config.defaultServerUrl = 'https://your-server.com';
```

### Custom Styling

Modify `css/styles.css` to customize the appearance.

### API Customization

Update `js/api.js` to add new endpoints or modify API calls.

## Limitations

- **HLS Support**: Requires HLS.js library for TVs without native HLS support
- **Screen Resolution**: Optimized for 1920x1080 (Full HD)
- **Network**: Requires stable network connection for streaming
- **Browser**: Uses Tizen WebKit browser engine

## Future Enhancements

- [ ] Movies browsing support
- [ ] Search functionality
- [ ] Favorites/Watchlist
- [ ] Continue watching
- [ ] Subtitle support
- [ ] Audio track selection
- [ ] Playback speed control
- [ ] 4K/UHD support

## Support

For issues or questions:
- Check Arctic Media server logs
- Review Tizen Studio console output
- Check browser console on TV (if accessible)

## License

Same as Arctic Media project.

