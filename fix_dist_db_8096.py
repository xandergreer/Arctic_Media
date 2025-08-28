#!/usr/bin/env python3
"""
Set the server to use port 8096 as requested
"""

import sqlite3
import os

def set_port_8096():
    """Set server to use port 8096"""
    print("=== Setting Server to Port 8096 ===")
    
    db_path = "dist/arctic.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Set server settings for port 8096
        server_settings = {
            "server_host": "0.0.0.0",
            "server_port": 8096,
            "external_access": True
        }
        
        # Update server settings
        cursor.execute("""
            INSERT OR REPLACE INTO server_settings (key, value) 
            VALUES (?, ?)
        """, ("server", str(server_settings)))
        
        conn.commit()
        print("✅ Server settings updated!")
        print(f"   Host: {server_settings['server_host']}")
        print(f"   Port: {server_settings['server_port']}")
        print(f"   External Access: {server_settings['external_access']}")
        
        conn.close()
        
        print("\n🔧 Next Steps:")
        print("1. Run ArcticMedia.exe from the dist folder")
        print("2. It will start on 0.0.0.0:8096")
        print("3. Access at http://localhost:8096")
        print("4. Your port forwarding for 8096 will work!")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    set_port_8096()
