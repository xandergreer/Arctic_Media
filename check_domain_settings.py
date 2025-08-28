#!/usr/bin/env python3
"""
Check current domain settings in the database
"""

import sqlite3
import ast

def check_settings():
    """Check current settings"""
    print("=== Current Database Settings ===")
    
    try:
        conn = sqlite3.connect('dist/arctic.db')
        cursor = conn.cursor()
        
        # Get all settings
        cursor.execute('SELECT key, value FROM server_settings')
        rows = cursor.fetchall()
        
        for row in rows:
            key, value = row
            print(f"\n{key}:")
            try:
                # Try to parse as dict
                parsed = ast.literal_eval(value)
                for k, v in parsed.items():
                    print(f"  {k}: {v}")
            except:
                print(f"  {value}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_settings()
