#!/usr/bin/env python3
"""
Fix the database in the dist folder to have correct server settings
"""

import asyncio
import sys
import os
import sqlite3

def fix_dist_database():
    """Fix the server settings in the dist database"""
    print("=== Fixing Dist Database ===")
    
    # Path to the database in dist folder
    db_path = "dist/arctic.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return
    
    try:
        # Connect to the database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current server settings
        cursor.execute("SELECT key, value FROM server_settings WHERE key = 'server'")
        result = cursor.fetchone()
        
        if result:
            print(f"Current server settings: {result[1]}")
        else:
            print("No server settings found")
        
        # Fix server settings
        correct_server_settings = {
            "server_host": "0.0.0.0",
            "server_port": 8000,
            "external_access": True
        }
        
        # Update or insert server settings
        cursor.execute("""
            INSERT OR REPLACE INTO server_settings (key, value) 
            VALUES (?, ?)
        """, ("server", str(correct_server_settings)))
        
        # Commit changes
        conn.commit()
        print("✅ Server settings fixed!")
        print(f"   Host: {correct_server_settings['server_host']}")
        print(f"   Port: {correct_server_settings['server_port']}")
        print(f"   External Access: {correct_server_settings['external_access']}")
        
        # Verify the fix
        cursor.execute("SELECT key, value FROM server_settings WHERE key = 'server'")
        result = cursor.fetchone()
        if result:
            print(f"✅ Verified: {result[1]}")
        
        conn.close()
        
        print("\n🔧 Next Steps:")
        print("1. Run ArcticMedia.exe from the dist folder")
        print("2. It should now start on 0.0.0.0:8000")
        print("3. Access at http://localhost:8000")
        
    except Exception as e:
        print(f"❌ Error fixing database: {e}")

if __name__ == "__main__":
    fix_dist_database()
