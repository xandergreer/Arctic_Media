# Arctic Media - Quick Setup Guide

## 🎯 For Executable Users

This guide is for users running the `ArcticMedia.exe` file.

## 📦 What You Get

- `ArcticMedia.exe` - The main application
- `arctic.db` - Database file (created automatically)
- `README.md` - This documentation

## 🚀 Getting Started

### Step 1: Run the Application
1. **Double-click** `ArcticMedia.exe`
2. **Wait** for the server to start (you'll see console output)
3. **Open** your browser to `http://localhost:8000`

### Step 2: Create Your Account
1. Click **"Register"** on the login page
2. Fill in your details:
   - Username: Choose any name
   - Email: Your email address
   - Password: Create a secure password
3. Click **"Register"**

### Step 3: Add Your Media
1. Go to **Settings** → **Libraries**
2. Click **"Add Library"**
3. Choose **Library Type**:
   - **Movies** - For movie collections
   - **TV Shows** - For TV series
4. Set **Library Path** to your media folder
5. Click **"Save"**

### Step 4: Scan Your Media
1. Click **"Scan Libraries"** in the Libraries section
2. Wait for the scan to complete
3. Your media will appear in the main interface

## 🌐 Accessing from Other Devices

### On Your Local Network
- **Find your IP address:**
  - Open Command Prompt
  - Type: `ipconfig`
  - Look for "IPv4 Address" (usually 192.168.x.x)
- **Access from other devices:**
  - `http://YOUR_IP:8000`
  - Example: `http://192.168.1.100:8000`

### From the Internet
1. **Configure your router:**
   - Access router admin (usually 192.168.1.1)
   - Find "Port Forwarding"
   - Forward port 8000 to your computer's IP
2. **Find your public IP:**
   - Visit `whatismyipaddress.com`
3. **Access remotely:**
   - `http://YOUR_PUBLIC_IP:8000`

## ⚙️ Configuration

### Change Port
1. Go to **Settings** → **Remote Access**
2. Change **Server Port** (e.g., 9000)
3. Click **"Save Changes"**
4. Click **"Restart Server"**

### Enable External Access
1. Go to **Settings** → **Remote Access**
2. Check **"Enable external access"**
3. Click **"Save Changes"**
4. Click **"Restart Server"**

### Custom Domain
1. Go to **Settings** → **Remote Access**
2. Set **"Public Base URL"** to your domain
3. Click **"Save Changes"**

## 🔧 Troubleshooting

### Application Won't Start
- **Check if port 8000 is in use:**
  - Try changing the port in settings
  - Or close other applications using port 8000

### Can't Access from Other Devices
- **Check Windows Firewall:**
  - Allow Arctic Media through firewall
  - Or temporarily disable firewall for testing

### Media Not Showing
- **Check folder permissions:**
  - Make sure the app can read your media folders
- **Run library scan:**
  - Go to Settings → Libraries → Scan Libraries

### Slow Performance
- **Check hardware acceleration:**
  - Go to Settings → Transcoder
  - Enable hardware acceleration if available

## 📱 Mobile Access

### Android/iOS
- Open your mobile browser
- Navigate to `http://YOUR_IP:8000`
- The interface is mobile-optimized

### Smart TV
- Most smart TVs have web browsers
- Navigate to `http://YOUR_IP:8000`
- Use your TV remote to navigate

## 🔒 Security Notes

- **Default access:** Local network only
- **Admin account:** Only you can access settings
- **No internet required:** Works completely offline
- **Your data:** Stored locally on your computer

## 📞 Need Help?

- **Check the main README.md** for detailed information
- **Look at the troubleshooting section** above
- **Restart the application** if you encounter issues
- **Check the console output** for error messages

---

**Enjoy your personal media server! 🎬**
