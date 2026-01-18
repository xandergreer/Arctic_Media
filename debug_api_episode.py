
import sqlite3
import requests
import json
import os
import sys

# Ensure app imports work (for config if needed, but we can guess)
sys.path.append(os.getcwd())
from app.config import settings
from app.models import MediaItem

DB_PATH = "dist/arctic.db"
API_URL = "http://192.168.1.22:8085"

def check_api():
    print(f"Connecting to DB: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Find a season that definitely has enriched episodes
    c.execute("SELECT parent_id FROM media_items WHERE kind='episode' AND poster_url LIKE 'http%' LIMIT 1")
    row = c.fetchone()
    if not row:
        print("No enriched episodes found in DB!")
        return
        
    sid = row[0]
    print(f"Testing Season ID with known enriched episodes: {sid}")
    
    # Login
    s = requests.Session()
    try:
        r = s.post(f"{API_URL}/auth/token", data={"username":"admin", "password":"password"})
        if r.status_code != 200:
            print(f"Login failed: {r.status_code}")
        else:
            token = r.json().get("access_token")
            s.headers.update({"Authorization": f"Bearer {token}"})
            print("Login successful.")
    except Exception as e:
        print(f"Login error: {e}")
        return

    # Fetch Season
    try:
        r = s.get(f"{API_URL}/api/season/{sid}")
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            eps = data.get("episodes", [])
            print(f"Episodes found: {len(eps)}")
            for i, ep in enumerate(eps):
                p = ep.get("poster_url")
                t = ep.get("title")
                eid = ep.get("id")
                print(f"Ep {i}: {t} (ID: {eid}) -> poster_url: {p}")
                if p:
                    print("  Success! Found valid poster_url.")
                    return # Exit on first success
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    check_api()
