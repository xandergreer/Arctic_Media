#!/usr/bin/env python3
"""
Test script to simulate Roku app pairing flow.
This helps verify the backend pairing endpoints without needing a physical Roku device.
"""
import requests
import time
import sys

# Configuration
SERVER_URL = "http://127.0.0.1:8000"
if len(sys.argv) > 1:
    SERVER_URL = sys.argv[1]

print(f"Testing pairing flow against: {SERVER_URL}")
print("=" * 60)

# Step 1: Request pairing code
print("\n[1] Requesting pairing code...")
try:
    resp = requests.post(f"{SERVER_URL}/pair/request", timeout=5)
    resp.raise_for_status()
    data = resp.json()
    device_code = data["device_code"]
    user_code = data["user_code"]
    expires_in = data["expires_in"]
    interval = data["interval"]
    
    print(f"✓ Got pairing codes:")
    print(f"  User Code: {user_code}")
    print(f"  Device Code: {device_code[:20]}... (hidden)")
    print(f"  Expires in: {expires_in} seconds")
    print(f"  Poll interval: {interval} seconds")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

# Step 2: Show instructions
print(f"\n[2] Pairing instructions:")
print(f"  - Go to: {SERVER_URL}/pair")
print(f"  - Enter code: {user_code}")
print(f"  - Or run this in another terminal:")
print(f"    curl -X POST {SERVER_URL}/pair/activate -H 'Content-Type: application/json' -d '{{\"user_code\": \"{user_code}\"}}' -b cookies.txt -c cookies.txt")
print(f"\n  Waiting for authorization... (press Ctrl+C to cancel)")
print(f"  Polling every {interval} seconds...")

# Step 3: Poll for authorization
max_attempts = expires_in // interval + 1
attempt = 0
start_time = time.time()

while attempt < max_attempts:
    time.sleep(interval)
    attempt += 1
    
    elapsed = int(time.time() - start_time)
    remaining = max(0, expires_in - elapsed)
    remaining_min = remaining // 60
    remaining_sec = remaining % 60
    
    try:
        resp = requests.post(
            f"{SERVER_URL}/pair/poll",
            json={"device_code": device_code},
            timeout=5
        )
        
        if resp.status_code == 404:
            print(f"✗ Pairing not found (may have expired)")
            break
        elif resp.status_code == 400:
            error_data = resp.json()
            print(f"✗ Error: {error_data.get('detail', 'Unknown error')}")
            break
        elif resp.status_code == 500:
            error_data = resp.json()
            detail = error_data.get('detail', 'Unknown server error')
            print(f"✗ Server Error: {detail}")
            print(f"  This might indicate the server needs to be restarted.")
            break
        
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status", "unknown")
        
        print(f"  Attempt {attempt} | Status = {status} | Time remaining: {remaining_min}m {remaining_sec}s")
        
        if status == "authorized":
            print(f"\n[3] ✓ Authorized!")
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")
            expires_in = data.get("expires_in")
            
            if access_token:
                print(f"  Access Token: {access_token[:40]}... (truncated)")
            if refresh_token:
                print(f"  Refresh Token: {refresh_token[:40]}... (truncated)")
            print(f"  Expires in: {expires_in} seconds")
            print(f"\n✓ Pairing test completed successfully!")
            sys.exit(0)
        elif status == "pending":
            # Keep polling
            continue
        else:
            print(f"✗ Unexpected status: {status}")
            break
            
    except KeyboardInterrupt:
        print("\n\n✗ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Poll error: {e}")
        break

print(f"\n✗ Pairing timed out or failed after {attempt} attempts")
sys.exit(1)

