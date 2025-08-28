#!/usr/bin/env python3
"""
Reset the dist database to correct default settings
"""

import sqlite3
import os

def reset_dist_database():
    """Reset the database to correct default settings"""
    print("=== Resetting Dist Database to Defaults ===")
    
    db_path = "dist/arctic.db"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Default server settings (correct)
        default_server_settings = {
            "server_host": "0.0.0.0",
            "server_port": 8000,
            "external_access": True
        }
        
        # Default remote settings
        default_remote_settings = {
            "enable_remote_access": False,
            "public_base_url": "",
            "port": 32400,
            "upnp": True,
            "allow_insecure_fallback": "never"
        }
        
        # Update server settings
        cursor.execute("""
            INSERT OR REPLACE INTO server_settings (key, value) 
            VALUES (?, ?)
        """, ("server", str(default_server_settings)))
        
        # Update remote settings
        cursor.execute("""
            INSERT OR REPLACE INTO server_settings (key, value) 
            VALUES (?, ?)
        """, ("remote", str(default_remote_settings)))
        
        conn.commit()
        print("✅ Database reset to defaults!")
        print(f"   Server Host: {default_server_settings['server_host']}")
        print(f"   Server Port: {default_server_settings['server_port']}")
        print(f"   External Access: {default_server_settings['external_access']}")
        print(f"   Public URL: {default_remote_settings['public_base_url']}")
        
        conn.close()
        
        print("\n🔧 How it works:")
        print("1. Server always binds to 0.0.0.0:8000 by default")
        print("2. Set 'Public Base URL' in settings for custom domain")
        print("3. Change 'Server Port' if you want different port")
        print("4. Server will restart with new settings")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    reset_dist_database()
