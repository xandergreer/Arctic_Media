Welcome to my passion project! I made my own self-hosted media server for managing personal movie and TV show collections. It lets you stream your media to any device through a web interface or Roku app (there may be more app support in the future).

Features

Web Interface - Responsive design that works on desktop and mobile.

Metadata - Automatically fetches posters and details from TMDB.

HLS Streaming - On-the-fly transcoding to ensure playback compatibility.

Written in Python/FastAPI using SQLite.

Portable - Runs as a single executable without installation.

Roku App - Ask me about it and I'll tell you how to easily sideload it onto your roku device



Quick Start

Download & Run
Download ArticMedia.exe from the Releases page. Run the executable. Open a browser to http://localhost:8085/login.
Setup
Create an admin account. Go to Settings > Libraries and add your movie/TV folders. Run a scan to populate your library. (scan all sometimes works but you might have to manually scan and refesh metadata if it didnt work for each folder)
Arctic Media supports most common video formats (MP4, MKV, AVI, etc.) and subtitles (SRT, VTT).
Points to note:

the server will scan the folders you give it permission to and it will automatically detect all movies and shows. Metadata is pulled from TMDB using filename matching. Errors can be fixed manually or by just entering the correct TMDB ID.

To access from other devices on your WiFi, use your computer's local IP: http://192.168.1.100:8085 (example)
To access from outside your network, you need to port forward port 8085 on your router to your computer's local IP. You can then connect via your public IP address. custom domains are also supported

Troubleshooting Connection Issues: Check that Windows Firewall isn't blocking the application. Missing Media: Ensure the application has read permissions for your folders and try rescanning. Playback Issues: Make sure FFmpeg is installed correctly (the app should handle this on first run). System Requirements: Windows 10/11 2GB RAM minimum, Sufficient storage for your media and the database file. License Open source. See LICENSE file for details.
