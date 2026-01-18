
import sqlite3
import json
import requests
import os

DB_PATH = "e:/Arctic_Media/dist/arctic.db"
API_BASE = "http://127.0.0.1:8085/api"

print(f"--- DIAGNOSTIC V11 ---")

# 1. Find a valid target in DB
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

print("Searching DB for episode with valid 'still'...")
# We look for a string that contains "still" key pattern or just any JSON
c.execute("SELECT id, title, extra_json, poster_url FROM media_items WHERE kind='episode' AND extra_json LIKE '%still%' LIMIT 1")
row = c.fetchone()

if not row:
    print("CRITICAL: No episodes with 'still' found in DB via LIKE check.")
    # Fallback to any episode
    c.execute("SELECT id, title, extra_json, poster_url FROM media_items WHERE kind='episode' LIMIT 1")
    row = c.fetchone()

if not row:
    print("CRITICAL: No episodes found at all.")
    exit(1)

eid, title, extra_str, poster_col = row
print(f"TARGET FOUND: {title} ({eid})")
print(f"  DB Column Poster: {poster_col}")
print(f"  DB Column Extra (Raw): {extra_str}")

# Parse it locally to be sure
if extra_str:
    try:
        ej = json.loads(extra_str)
        print(f"  Local JSON Parse 'still': {ej.get('still')}")
        print(f"  Local JSON Parse 'poster': {ej.get('poster')}")
    except Exception as e:
        print(f"  Local JSON Parse Error: {e}")
else:
    print("  DB Extra is Empty/Null")

conn.close()

# 2. Query API
url = f"{API_BASE}/episode/{eid}"
print(f"\nQuerying API: {url}")
try:
    resp = requests.get(url)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        d = resp.json()
        print(f"API 'title': {d.get('title')}")
        print(f"API 'still': {d.get('still')}")
        print(f"API 'poster_url': {d.get('poster_url')}")
        print(f"API 'extra_json': {d.get('extra_json')}")
    else:
        print(f"Error: {resp.text}")
except Exception as e:
    print(f"API Request Failed: {e}")
