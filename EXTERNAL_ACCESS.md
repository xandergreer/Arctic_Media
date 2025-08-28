# External Access Guide for Arctic Media

## Overview
This guide covers how to access Arctic Media from outside your local network.

## Method 1: Port Forwarding (Recommended for Home Use)

### Step 1: Find Your External IP
```bash
# Visit whatismyipaddress.com or run:
curl ifconfig.me
```

### Step 2: Configure Router Port Forwarding
1. **Access your router admin panel** (usually http://192.168.1.1 or http://10.0.0.1)
2. **Find Port Forwarding section** (may be called "Virtual Server" or "Port Mapping")
3. **Add a new rule:**
   - **External Port:** 8000 (or any port you prefer)
   - **Internal IP:** Your server's local IP (e.g., 192.168.1.100)
   - **Internal Port:** 8000
   - **Protocol:** TCP
   - **Status:** Enabled

### Step 3: Configure Arctic Media for External Access
```bash
# Set environment variables for external access
set ARCTIC_HOST=0.0.0.0
set ARCTIC_PORT=8000

# Or create a .env file:
echo ARCTIC_HOST=0.0.0.0 > .env
echo ARCTIC_PORT=8000 >> .env
```

### Step 4: Access from External Network
```
http://YOUR_EXTERNAL_IP:8000
```

## Method 2: Reverse Proxy with Nginx (Advanced)

### Install Nginx
```bash
# Windows (using Chocolatey)
choco install nginx

# Or download from nginx.org
```

### Configure Nginx
Create `C:\nginx\conf\sites-available\arctic-media`:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # or your IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for live features
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Enable Site
```bash
# Copy to sites-enabled
copy C:\nginx\conf\sites-available\arctic-media C:\nginx\conf\sites-enabled\

# Test configuration
nginx -t

# Reload nginx
nginx -s reload
```

## Method 3: Cloudflare Tunnel (Most Secure)

### Step 1: Install Cloudflare Tunnel
```bash
# Download from https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
```

### Step 2: Authenticate
```bash
cloudflared tunnel login
```

### Step 3: Create Tunnel
```bash
cloudflared tunnel create arctic-media
```

### Step 4: Configure Tunnel
Create `~/.cloudflared/config.yml`:
```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: ~/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: arctic-media.your-domain.com
    service: http://localhost:8000
  - service: http_status:404
```

### Step 5: Run Tunnel
```bash
cloudflared tunnel run arctic-media
```

## Method 4: VPN Access (Most Secure for Personal Use)

### Option A: Tailscale (Recommended)
1. **Install Tailscale** on your server and devices
2. **Join the same network** on all devices
3. **Access via Tailscale IP:** `http://YOUR_TAILSCALE_IP:8000`

### Option B: WireGuard
1. **Set up WireGuard server** on your network
2. **Configure clients** to connect to your network
3. **Access via local IP** as if you were on the same network

## Security Considerations

### 1. Firewall Configuration
```bash
# Windows Firewall - Allow inbound connections
netsh advfirewall firewall add rule name="Arctic Media" dir=in action=allow protocol=TCP localport=8000
```

### 2. Authentication
- Arctic Media already has user authentication
- Consider using HTTPS for external access
- Use strong passwords for admin accounts

### 3. Network Security
- **Port Forwarding:** Only forward necessary ports
- **VPN:** Most secure option for personal use
- **Cloudflare Tunnel:** Best for public access with security

## SSL/HTTPS Setup

### Using Let's Encrypt with Nginx
```bash
# Install Certbot
choco install certbot

# Get certificate
certbot --nginx -d your-domain.com

# Auto-renewal
certbot renew --dry-run
```

### Using Cloudflare SSL
1. **Add your domain to Cloudflare**
2. **Set DNS records** to point to your server
3. **Enable SSL/TLS encryption** in Cloudflare dashboard

## Troubleshooting

### Common Issues

1. **Can't access from external network:**
   - Check router port forwarding
   - Verify Windows Firewall settings
   - Test with `telnet YOUR_IP 8000`

2. **Connection timeout:**
   - ISP may be blocking port 8000
   - Try different port (8080, 9000, etc.)
   - Check if server is running on 0.0.0.0:8000

3. **Slow streaming:**
   - Check upload bandwidth
   - Consider using VPN for better routing
   - Optimize transcoding settings

### Testing External Access
```bash
# Test from external network
curl -I http://YOUR_EXTERNAL_IP:8000

# Check if port is open
nmap -p 8000 YOUR_EXTERNAL_IP
```

## Recommended Setup for Different Use Cases

### Home Network Only
- Use VPN (Tailscale/WireGuard)
- No port forwarding needed
- Maximum security

### Family/Friends Access
- Cloudflare Tunnel
- Easy setup, good security
- Works behind NAT/firewalls

### Public Access
- Nginx reverse proxy + Let's Encrypt
- Full control over domain
- Professional setup

### Development/Testing
- Port forwarding
- Quick setup
- Good for temporary access
