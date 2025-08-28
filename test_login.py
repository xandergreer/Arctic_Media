#!/usr/bin/env python3
"""
Test login functionality for Arctic Media
"""

import requests
import json

def test_login():
    """Test login with the known user"""
    base_url = "http://192.168.1.129:8000"
    
    print("=== Testing Arctic Media Login ===")
    print(f"Server URL: {base_url}")
    
    # Test 1: Check if server is accessible
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"✅ Server health check: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot reach server: {e}")
        return
    
    # Test 2: Check login page
    try:
        response = requests.get(f"{base_url}/login", timeout=5)
        print(f"✅ Login page accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ Cannot access login page: {e}")
        return
    
    print("\n📋 Login Information:")
    print("Username: Arctic")
    print("Email: xandergreer03@gmail.com")
    print("Password: [your password]")
    
    print("\n🔗 Try these URLs from your other device:")
    print(f"Login: {base_url}/login")
    print(f"Register: {base_url}/register")
    print(f"Home: {base_url}/home")
    
    print("\n🔧 If you get 401 Unauthorized:")
    print("1. Double-check your password")
    print("2. Try both username and email")
    print("3. Clear browser cache/cookies")
    print("4. Try incognito mode")
    print("5. Check if devices are on same network")

if __name__ == "__main__":
    test_login()
