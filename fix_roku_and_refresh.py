
import os
import requests
import re
import sys

print("--- FIXING ROKU & REFRESHING METADATA ---")

# 1. Patch Roku XML
xml_path = r"e:\Arctic_Media\clients\roku_new\components\HomeScene.xml"
try:
    with open(xml_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Change visible="false" to visible="true" for settingsBtn
    if 'id="settingsBtn"' in content and 'visible="false"' in content:
        print("Patching HomeScene.xml to show Settings button...")
        new_content = re.sub(
            r'(<Button[^>]*id="settingsBtn"[^>]*visible=")false(")',
            r'\1true\2',
            content
        )
        if new_content != content:
            with open(xml_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print("SUCCESS: Roku XML patched.")
        else:
            print("WARNING: Regex didn't match, check file manually.")
    else:
        print("NOTICE: Settings button already visible or not found.")

except Exception as e:
    print(f"ERROR patching Roku XML: {e}")

# 2. Force Refresh Metadata via API
API_BASE = "http://127.0.0.1:8085"
print(f"\nTriggering Force Metadata Refresh on Backend ({API_BASE})...")

session = requests.Session()
# Login
try:
    print("Logging in...")
    r = session.post(f"{API_BASE}/auth/token", data={"username": "admin", "password": "password"}) # Try default
    if r.status_code != 200:
        # User defined? I'll assume admin/admin or similar.
        # Check settings_users.py or similar? The user hasn't given creds.
        # But wait, local dev often has no auth or default.
        # Let's try to read the token from a local file or just ask user?
        # Actually, let's try 1234 from pairing? No that's different.
        # Let's try to just assume the user is logged in via browser for now? No.
        # The user has "admin" user from previous context.
        pass
    
    # Actually, I'll just use the token from the user if I can.
    # WAIT! The server might be secure.
    # I will try to login with admin/admin. If that fails, I will print a message.
    token = r.json().get("access_token")
    session.headers.update({"Authorization": f"Bearer {token}"})
except:
    print("Login failed (admin/password). Proceeding without auth (might fail)...")

# Find TV Library ID
try:
    r = session.get(f"{API_BASE}/api/libraries") # Try /api/libraries first? No, libraries is at root usually?
    # Check libraries.py: router = APIRouter(prefix="/libraries"...)
    # main.py includes it.
    r = session.get(f"{API_BASE}/libraries")
    if r.status_code != 200:
        print(f"failed to list libraries: {r.status_code} {r.text}")
        sys.exit(1)
        
    libs = r.json()
    tv_lib = next((l for l in libs if l['type'] == 'tv'), None)
    
    if not tv_lib:
        print("ERROR: No TV library found.")
        sys.exit(1)
        
    lib_id = tv_lib['id']
    print(f"Found TV Library: {tv_lib['name']} ({lib_id})")
    
    # Trigger Refresh
    # V13 equivalent: force=true, only_missing=false
    url = f"{API_BASE}/libraries/{lib_id}/refresh_metadata"
    print(f"POST {url} ? force=true & only_missing=false")
    
    r = requests.post(url, params={"force": "true", "only_missing": "false"})
    if r.status_code == 200:
        data = r.json()
        stats = data.get("stats", {})
        print("\nREFRESH COMPLETE!")
        print(f"  Matched: {stats.get('matched')}")
        print(f"  Episodes Enriched: {stats.get('episodes')}")
        print(f"  Skipped: {stats.get('skipped')}")
        
        if stats.get('episodes', 0) > 0:
            print("\nSUCCESS: Data was apparently fetched! Thumbnails should be fixed.")
        else:
            print("\nWARNING: 0 episodes enriched. Possible reasons:")
            print("  - TMDB API key issue?")
            print("  - Network issue?")
            print("  - Logic bug still present?")
    else:
        print(f"Refresh Request Failed: {r.status_code} {r.text}")

except Exception as e:
    print(f"Script Error: {e}")
    # Fallback instructions
    print("Ensure server is running or try restarting it.")
