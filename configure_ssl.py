#!/usr/bin/env python3
"""
Configure SSL settings for Arctic Media server
"""

import sqlite3
import os

def configure_ssl():
    """Configure SSL settings for arcticmedia.space"""
    print("🔒 Arctic Media SSL Configuration")
    print("=" * 50)
    
    # Get SSL certificate paths from user
    print("\n📋 SSL Certificate Setup:")
    print("You need to provide the paths to your SSL certificate files.")
    print("These are typically obtained from your domain provider or Let's Encrypt.")
    
    cert_file = input("\nEnter the path to your SSL certificate file (.crt or .pem): ").strip()
    key_file = input("Enter the path to your SSL private key file (.key): ").strip()
    
    # Validate files exist
    if not os.path.exists(cert_file):
        print(f"❌ Certificate file not found: {cert_file}")
        return
    
    if not os.path.exists(key_file):
        print(f"❌ Private key file not found: {key_file}")
        return
    
    print(f"✅ Certificate file found: {cert_file}")
    print(f"✅ Private key file found: {key_file}")
    
    # Update database
    try:
        conn = sqlite3.connect('dist/arctic.db')
        cursor = conn.cursor()
        
        # Update server settings with SSL configuration
        server_settings = {
            "server_host": "0.0.0.0",
            "server_port": 443,  # Standard HTTPS port
            "external_access": True,
            "ssl_enabled": True,
            "ssl_cert_file": cert_file,
            "ssl_key_file": key_file
        }
        
        # Update remote settings
        remote_settings = {
            "enable_remote_access": True,
            "public_base_url": "https://arcticmedia.space",
            "port": 32400,
            "upnp": True,
            "allow_insecure_fallback": "never"
        }
        
        # Update server settings
        cursor.execute("""
            INSERT OR REPLACE INTO server_settings (key, value) 
            VALUES (?, ?)
        """, ("server", str(server_settings)))
        
        # Update remote settings
        cursor.execute("""
            INSERT OR REPLACE INTO server_settings (key, value) 
            VALUES (?, ?)
        """, ("remote", str(remote_settings)))
        
        conn.commit()
        print("\n✅ SSL configuration saved!")
        print(f"   Server Port: {server_settings['server_port']}")
        print(f"   SSL Enabled: {server_settings['ssl_enabled']}")
        print(f"   Certificate: {server_settings['ssl_cert_file']}")
        print(f"   Private Key: {server_settings['ssl_key_file']}")
        print(f"   Public URL: {remote_settings['public_base_url']}")
        
        conn.close()
        
        print("\n🔧 Next Steps:")
        print("1. Update your router port forwarding:")
        print("   - External Port: 443 → Internal Port: 443")
        print("2. Restart ArcticMedia.exe")
        print("3. Access via: https://arcticmedia.space")
        print("\n⚠️  Note: Port 443 requires administrator privileges on Windows")
        print("   Run ArcticMedia.exe as administrator or use a different port")
        
    except Exception as e:
        print(f"❌ Error saving SSL configuration: {e}")

if __name__ == "__main__":
    configure_ssl()
