# Arctic Media Server

A lightweight, self-hosted media streaming server built with FastAPI that provides HLS streaming with adaptive bitrate support, similar to Jellyfin/Emby but with a focus on simplicity and performance.

## Features

### 🎬 Media Streaming
- **HLS Streaming**: Native HLS support with fMP4 segments for modern browsers
- **Adaptive Bitrate (ABR)**: Multiple quality variants (Original, Remux, HD, SD, Mobile)
- **Fast Startup**: Remux-first approach with H.264 fallback for instant playback
- **Browser Compatibility**: Works with Chrome, Firefox, Safari, and Edge
- **Progressive Fallback**: MP4 fallback for older devices or HLS failures

### 🎮 Player Experience
- **Modern UI**: Clean, responsive interface with Plyr video controls
- **Quality Selection**: Manual quality switching in the player
- **Auto-Adaptive**: Automatic quality switching based on network conditions
- **Resume Support**: Remember playback position (coming soon)
- **Mobile Optimized**: Touch-friendly controls and mobile-optimized streaming

### 🏗️ Architecture
- **FastAPI Backend**: High-performance async Python framework
- **SQLAlchemy**: Robust database ORM with async support
- **ffmpeg Integration**: On-the-fly transcoding and remuxing
- **Security**: Token-based segment protection and session management
- **Scalable**: Designed for single-server deployment with room to grow

## Quick Start

### Prerequisites
- Python 3.11+
- ffmpeg (must be in PATH or set `FFMPEG_BIN` environment variable)
- Modern web browser

### Local Development
```bash
# Clone the repository
git clone <repository-url>
cd Arctic_Media

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up your media directory
export ARCTIC_MEDIA_ROOT=/path/to/your/media
export ARCTIC_TRANSCODE_DIR=/tmp/arctic_transcode

# Run the server
uvicorn app.main:app --reload
```

Visit `http://localhost:8000` to access the web interface.

## Deployment Options

### Docker (Recommended)

#### Using Docker Compose
```bash
# Clone and navigate to project
git clone <repository-url>
cd Arctic_Media

# Create media directory
mkdir media

# Start the service
docker-compose up -d

# Access at http://localhost:8000
```

#### Using Docker directly
```bash
# Build the image
docker build -t arctic-media .

# Run the container
docker run -d \
  --name arctic-media \
  -p 8000:8000 \
  -v /path/to/media:/app/data:ro \
  -v arctic-data:/app/data \
  -v arctic-transcode:/app/transcode \
  arctic-media
```

### Linux Systemd Service
```bash
# Copy service file
sudo cp scripts/arctic-media.service /etc/systemd/system/

# Create user and directories
sudo useradd --system --create-home arctic
sudo mkdir -p /opt/arctic-media/{data,transcode}
sudo chown -R arctic:arctic /opt/arctic-media

# Install application
sudo cp -r app /opt/arctic-media/
sudo cp run_server.py requirements.txt /opt/arctic-media/

# Enable and start service
sudo systemctl enable arctic-media
sudo systemctl start arctic-media
```

### Windows Service
```powershell
# Install NSSM first (https://nssm.cc/download)
# Run as Administrator
.\scripts\install-windows-service.ps1

# Or manually:
nssm install ArcticMedia "C:\ArcticMedia\.venv\Scripts\python.exe" "-m uvicorn app.main:app --host 0.0.0.0 --port 8000"
nssm set ArcticMedia AppDirectory "C:\ArcticMedia"
nssm set ArcticMedia Start SERVICE_AUTO_START
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ARCTIC_MEDIA_ROOT` | `""` | Path to your media library |
| `ARCTIC_TRANSCODE_DIR` | System temp | Directory for transcoded segments |
| `FFMPEG_BIN` | `"ffmpeg"` | Path to ffmpeg executable |
| `FFMPEG_PRESET` | `"veryfast"` | ffmpeg encoding preset |
| `HLS_SEG_DUR` | `2.0` | HLS segment duration in seconds |
| `SECRET_KEY` | Auto-generated | Secret key for sessions/tokens |

### ABR Quality Profiles

The server automatically creates multiple quality variants:

| Profile | Resolution | Bitrate | Use Case |
|---------|------------|---------|----------|
| Original | 1920x1080 | 15 Mbps | High-end devices |
| Remux | 1920x1080 | 8 Mbps | Fast start, good quality |
| HD | 1280x720 | 4 Mbps | Standard streaming |
| SD | 854x480 | 2 Mbps | Bandwidth-friendly |
| Mobile | 640x360 | 1 Mbps | Mobile devices |

## API Endpoints

### Native HLS Endpoints
- `GET /stream/{item_id}/master.m3u8` - Master playlist with ABR variants
- `GET /stream/{item_id}/hls/{job_id}/index.m3u8` - Individual variant playlist
- `GET /stream/{item_id}/hls/{job_id}/init.mp4` - Initialization segment
- `GET /stream/{item_id}/hls/{job_id}/seg_*.m4s` - Media segments

### Jellyfin Compatibility
- `GET /Videos/{item_id}/master.m3u8` - Jellyfin-style master playlist
- `GET /Videos/{item_id}/hls/{job_id}/index.m3u8` - Variant playlist
- `GET /Videos/{item_id}/hls/{job_id}/{n}.m4s` - Segments

### Progressive Fallback
- `GET /stream/{file_id}/auto` - Progressive MP4 stream

## Development

### Project Structure
```
Arctic_Media/
├── app/
│   ├── streaming_hls.py    # HLS streaming engine
│   ├── main.py            # FastAPI application
│   ├── models.py          # Database models
│   ├── auth.py            # Authentication
│   └── static/js/
│       └── player.js      # Browser player logic
├── templates/             # Jinja2 templates
├── Dockerfile            # Docker configuration
├── docker-compose.yml    # Docker Compose setup
└── scripts/              # Deployment scripts
```

### Key Components

#### HLS Streaming Engine (`app/streaming_hls.py`)
- Manages ffmpeg transcoding jobs
- Generates master and variant playlists
- Handles segment authentication
- Implements ABR quality profiles

#### Player (`app/static/js/player.js`)
- Lazy-loads Hls.js for non-Safari browsers
- Handles quality switching
- Provides fallback to progressive MP4
- Integrates with Plyr controls

### Adding Features

#### Custom Quality Profiles
Edit `ABR_PROFILES` in `app/streaming_hls.py`:
```python
ABR_PROFILES = {
    QualityProfile.CUSTOM: {
        "name": "Custom",
        "vcodec": "h264",
        "acodec": "aac",
        "bandwidth": 3000000,
        "width": 1280,
        "height": 720,
        "crf": 24,
    }
}
```

#### Subtitle Support (Coming Soon)
- SRT/VTT subtitle conversion
- WebVTT delivery
- Burn-in for image-based subtitles

## Troubleshooting

### Common Issues

#### Black Screen, No Playback
1. Check browser console for errors
2. Verify ffmpeg is installed and accessible
3. Check network panel for failed segment requests
4. Try `?container=ts` parameter for older devices

#### Slow Startup
1. Reduce `HLS_SEG_DUR` to 1.5-2.0 seconds
2. Ensure remux path is working (check logs)
3. Consider faster ffmpeg preset (`ultrafast`)

#### High CPU Usage
1. Use `copy` codec when possible
2. Adjust `FFMPEG_PRESET` to `veryfast` or `superfast`
3. Limit concurrent transcoding jobs

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload --log-level debug
```

### Health Check
```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy", "service": "arctic-media"}
```

## Performance Tuning

### For High-Traffic Deployments
- Use reverse proxy (nginx/traefik) for SSL termination
- Consider CDN for static assets
- Monitor transcode directory size
- Use SSD storage for transcode cache

### For Low-End Hardware
- Set `FFMPEG_PRESET=ultrafast`
- Reduce `HLS_SEG_DUR` to 1.5
- Limit concurrent transcoding jobs
- Use fewer ABR variants

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

[Add your license here]

## Acknowledgments

- [Hls.js](https://github.com/video-dev/hls.js) - HLS playback in browsers
- [Plyr](https://plyr.io/) - Video player UI
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [ffmpeg](https://ffmpeg.org/) - Media processing
