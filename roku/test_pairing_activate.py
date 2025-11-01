#!/usr/bin/env python3
"""
Helper script to activate a pairing code from the command line.
Useful for testing when you can't use the web UI.

Usage:
    python test_pairing_activate.py USER_CODE
    python test_pairing_activate.py ABCD-1234 --url http://localhost:8085
"""
import requests
import sys
import argparse

def activate_pairing(user_code: str, server_url: str = "http://127.0.0.1:8085", cookies_file: str = None):
    """Activate a pairing code. Requires you to be logged in."""
    
    session = requests.Session()
    
    # Try to load cookies if provided
    if cookies_file:
        try:
            import http.cookiejar
            jar = http.cookiejar.MozillaCookieJar(cookies_file)
            jar.load(ignore_discard=True, ignore_expires=True)
            session.cookies = jar
        except:
            pass
    
    print(f"Activating pairing code: {user_code}")
    print(f"Server: {server_url}")
    
    # First, try to check if we're logged in
    try:
        resp = session.get(f"{server_url}/auth/me", timeout=5)
        if resp.status_code == 401:
            print("⚠ Warning: Not logged in. You need to:")
            print(f"  1. Visit {server_url}/login")
            print("  2. Log in to create a session")
            print("  3. Run this script again with --cookies cookies.txt")
            print("\nOr use the web UI at:", f"{server_url}/pair")
            return False
    except:
        pass
    
    # Activate pairing
    try:
        resp = session.post(
            f"{server_url}/pair/activate",
            json={"user_code": user_code.upper()},
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        print(f"✓ {data.get('message', 'Device authorized!')}")
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("✗ Not logged in. Visit the web UI to log in first.")
        elif e.response.status_code == 404:
            print("✗ Invalid code or code not found")
        elif e.response.status_code == 400:
            error_data = e.response.json()
            print(f"✗ Error: {error_data.get('detail', 'Unknown error')}")
        else:
            print(f"✗ HTTP {e.response.status_code}: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Activate a Roku pairing code")
    parser.add_argument("user_code", help="The pairing code (e.g., ABCD-1234)")
    parser.add_argument("--url", default="http://127.0.0.1:8085", help="Server URL")
    parser.add_argument("--cookies", help="Cookies file (from browser)")
    args = parser.parse_args()
    
    success = activate_pairing(args.user_code, args.url, args.cookies)
    sys.exit(0 if success else 1)

