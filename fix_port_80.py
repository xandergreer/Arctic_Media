#!/usr/bin/env python3
"""
Change server port to 80 for SSL compatibility
"""

import sqlite3

def change_to_port_80():
    """Change server to use port 80"""
    print("=== Changing Server to Port 80 ===")
    
    try:
        conn = sqlite3.connect('dist/arctic.db')
        cursor = conn.cursor()
        
        # Update server settings to use port 80
        server_settings = {
            "server_host": "0.0.0.0",
            "server_port": 80,
            "external_access": True
        }
        
        # Update remote settings to use standard ports
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
        print("✅ Server settings updated!")
        print(f"   Server Port: {server_settings['server_port']}")
        print(f"   Public URL: {remote_settings['public_base_url']}")
        
        conn.close()
        
        print("\n🔧 Next Steps:")
        print("1. Update your router port forwarding:")
        print("   - External Port: 80 → Internal Port: 80")
        print("   - External Port: 443 → Internal Port: 80")
        print("2. Restart ArcticMedia.exe")
        print("3. Access via: https://arcticmedia.space")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    change_to_port_80()
