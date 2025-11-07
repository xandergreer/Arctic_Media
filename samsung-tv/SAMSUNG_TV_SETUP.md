# Samsung TV App - Quick Setup Guide

## ✅ What We've Built

A complete Samsung TV (Tizen) app for Arctic Media with:

- **Server Configuration** - Enter your Arctic Media server URL
- **Device Pairing** - Secure authentication using pairing codes
- **TV Shows Browsing** - Browse all series in your library
- **Seasons & Episodes** - Navigate through show content
- **HLS Video Streaming** - Stream content using HTTP Live Streaming
- **TV-Optimized UI** - Designed for Samsung TV remote control
- **Focus Navigation** - Visual focus indicators for easy navigation

## 📋 Prerequisites

1. **Samsung Tizen Studio**
   - Download from: https://developer.samsung.com/tizen
   - Install with TV SDK (via Package Manager)

2. **Samsung TV** (or Tizen TV Emulator)
   - For testing and deployment

3. **Arctic Media Server**
   - Running and accessible on your network

## 🚀 Quick Start

### Step 1: Install Tizen Studio

1. Download Tizen Studio from Samsung Developer Portal
2. Install with default settings
3. Open Tizen Studio → Tools → Package Manager
4. Install **TV Extension** and **TV SDK**

### Step 2: Import the Project

1. Open Tizen Studio
2. File → Import → Tizen → **Tizen Project**
3. Select the `samsung-tv` folder
4. Click Finish

### Step 3: Build the App

1. Right-click project in Project Explorer
2. Select **Build Project**
3. Wait for build to complete

### Step 4: Enable Developer Mode on TV

1. Press **Home** button on Samsung TV remote
2. Go to **Settings** → **General** → **External Device Manager** → **Device Manager**
3. Enable **Developer Mode**
4. Note your TV's IP address: **Settings** → **Network** → **Network Status**

### Step 5: Connect TV to Tizen Studio

1. In Tizen Studio, open **Device Manager** (Tools → Device Manager)
2. Click **Remote Device Manager**
3. Click **+** to add device
4. Enter TV's IP address
5. Click **Add**
6. TV should appear in device list

### Step 6: Install App on TV

1. Right-click project in Tizen Studio
2. **Run As** → **Tizen Web Application**
3. Select your TV from the device list
4. App will install and launch automatically

## 🎮 First Launch

1. **Enter Server URL**
   - Enter your Arctic Media server address
   - Example: `http://192.168.1.100:8085`
   - Press Enter or click Connect

2. **Pair Device**
   - A pairing code will appear on screen
   - Open your Arctic Media server in a browser
   - Go to `/pair` page
   - Enter the pairing code shown on TV
   - Click "Authorize Device"

3. **Start Browsing**
   - Once paired, you'll see your TV shows
   - Navigate with arrow keys
   - Press Enter to select
   - Enjoy streaming!

## 🎯 Remote Control

- **Arrow Keys** ↑↓←→ - Navigate
- **Enter** - Select/Activate
- **Back/Return** - Go back
- **Exit** - Close app

## 📁 Project Structure

```
samsung-tv/
├── config.xml          # Tizen app manifest
├── index.html          # Main HTML
├── icon.png            # App icon (192x192 - create this)
├── css/
│   └── styles.css      # TV-optimized styles
├── js/
│   ├── config.js       # Config & storage
│   ├── api.js          # API client
│   ├── navigation.js   # Remote control
│   └── app.js          # Main app logic
└── README.md           # Full documentation
```

## 🔧 Troubleshooting

### App Won't Install

- ✅ Verify Developer Mode is enabled on TV
- ✅ Check TV and computer are on same network
- ✅ Verify TV IP address is correct
- ✅ Try restarting TV and Tizen Studio
- ✅ Check firewall settings

### Can't Connect to Server

- ✅ Verify server URL format (no trailing slash)
- ✅ Check server is running
- ✅ Test server URL in browser on TV
- ✅ Check firewall allows connections on port 8085

### Video Won't Play

- ✅ Check HLS.js library is loaded (check browser console)
- ✅ Verify network connection speed
- ✅ Check server transcoding is working
- ✅ Try accessing stream URL directly in browser

### Navigation Issues

- ✅ Check JavaScript console for errors
- ✅ Verify focusable elements are present
- ✅ Try refreshing the app
- ✅ Ensure remote control is working

## 📦 Creating App Icon

Create a 192x192 PNG icon named `icon.png` in the `samsung-tv` folder.

You can use any image editor or online tool to create this icon.

## 🔐 Security Notes

- Pairing codes expire after 30 minutes
- Tokens are stored in localStorage
- All API requests use Bearer token authentication
- HLS streams are protected with token authentication

## 🎨 Customization

### Change Default Server URL

Edit `js/config.js`:
```javascript
Config.defaultServerUrl = 'http://your-server:8085';
```

### Customize Colors

Edit `css/styles.css`:
```css
/* Primary color */
.btn-primary {
    background: #00d4ff;  /* Change this */
}
```

## 📱 Next Steps

1. **Test on Real TV** - Deploy to your Samsung TV
2. **Add Movies Support** - Extend API calls for movies
3. **Add Search** - Implement search functionality
4. **Improve UI** - Customize styling further
5. **Add Features** - Favorites, watchlist, etc.

## 🆘 Need Help?

- Check the main README.md for detailed documentation
- Review Tizen Studio console for errors
- Check Arctic Media server logs
- Test API endpoints directly with curl/Postman

---

**Ready to stream! 🎉**

