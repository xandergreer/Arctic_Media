# Arctic Media

A modern, self-hosted media server for your personal movie and TV show collection. Stream your media anywhere with a beautiful web interface.

## ✨ Features

- **🎬 Beautiful Interface** - Modern, responsive web UI
- **📱 Cross-Platform** - Works on desktop, tablet, and mobile
- **🔍 Smart Metadata** - Automatic movie/TV show info from TMDB
- **📺 HLS Streaming** - Adaptive streaming for any device
- **🌐 Remote Access** - Access your media from anywhere
- **⚡ Fast & Lightweight** - Built with FastAPI and SQLite
- **🔧 Easy Setup** - Single executable, no complex installation

## 🚀 Quick Start

### 1. Download & Run
1. Download `ArcticMedia.exe` from the releases
2. Double-click to run
3. Open your browser to `http://localhost:8000`

### 2. First Time Setup
1. **Register** - Create your admin account
2. **Add Libraries** - Point to your movie/TV folders
3. **Scan** - Let Arctic Media discover your media
4. **Enjoy** - Start streaming!

## 📁 Adding Your Media

### Supported Formats
- **Movies:** MP4, MKV, AVI, MOV, etc.
- **TV Shows:** Any video format
- **Subtitles:** SRT, VTT, ASS

### How It Works
- **Smart Scanning** - Arctic Media automatically detects and organizes your media
- **Metadata Matching** - Uses TMDB to get movie/show information, posters, and descriptions
- **Flexible Structure** - Works with any folder organization you prefer
- **Episode Detection** - Automatically identifies TV show episodes and seasons

## 🌐 Remote Access

Access your media from anywhere:

### Local Network
- Other devices on your network: `http://YOUR_IP:8000`
- Example: `http://192.168.1.100:8000`

### Internet Access
1. **Port Forwarding** (Router setup)
   - Forward port 8000 to your computer
   - Access via: `http://YOUR_PUBLIC_IP:8000`

2. **Custom Domain** (Optional)
   - Set up domain in settings
   - Access via: `https://yourdomain.com`

## ⚙️ Settings

### Server Configuration
- **Port:** Change default port (8000)
- **External Access:** Enable/disable network access
- **Custom Domain:** Set your own domain

### Libraries
- **Add/Remove:** Manage media folders
- **Scan:** Refresh media database
- **Metadata:** Configure TMDB settings

### Transcoder
- **Hardware Acceleration:** Enable GPU encoding
- **Quality Settings:** Adjust streaming quality
- **Format Support:** Configure codec preferences

## 🔧 Troubleshooting

### Can't Access from Other Devices?
1. Check Windows Firewall
2. Verify external access is enabled
3. Try different port in settings

### Media Not Showing?
1. Check folder permissions
2. Run library scan
3. Verify file formats are supported

### Streaming Issues?
1. Check FFmpeg installation
2. Try different quality settings
3. Verify network connection

## 📋 System Requirements

- **OS:** Windows 10/11
- **RAM:** 2GB minimum, 4GB recommended
- **Storage:** Space for your media + database
- **Network:** For remote access

## 🆘 Support

- **Issues:** Check the troubleshooting section
- **Features:** Request via GitHub issues
- **Community:** Join discussions on GitHub

## 📄 License

Arctic Media is open source software. See LICENSE file for details.

---

**Made with ❄️ for media lovers everywhere**