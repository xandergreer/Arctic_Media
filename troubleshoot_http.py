#!/usr/bin/env python3
"""
Troubleshooting script for HTTP request issues
"""

import requests
import socket
import subprocess
import sys

def check_server_status():
    """Check if the server is running and accessible"""
    print("=== HTTP Request Troubleshooting ===")
    
    # Check if server is running
    try:
        # Try to connect to localhost:8085
        response = requests.get("http://localhost:8085/health", timeout=5)
        print(f"✅ Server is running: {response.status_code}")
        
        # Check server info
        if response.status_code == 200:
            data = response.json()
            print(f"   Service: {data.get('service', 'Unknown')}")
            print(f"   Status: {data.get('status', 'Unknown')}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server on localhost:8085")
        print("   Make sure ArcticMedia.exe is running")
        return False
    except Exception as e:
        print(f"❌ Error connecting to server: {e}")
        return False
    
    return True

def check_port_availability():
    """Check if port 8085 is available"""
    print("\n=== Port Availability Check ===")
    
    try:
        # Try to bind to port 8085
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', 8085))
        sock.close()
        
        if result == 0:
            print("✅ Port 8085 is in use (server is running)")
        else:
            print("❌ Port 8085 is not in use")
            print("   Server might not be running")
            
    except Exception as e:
        print(f"❌ Error checking port: {e}")

def check_network_connectivity():
    """Check network connectivity"""
    print("\n=== Network Connectivity ===")
    
    try:
        # Check local IP
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print(f"✅ Local IP: {local_ip}")
        
        # Check if we can bind to 0.0.0.0
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('0.0.0.0', 0))  # Bind to any available port
        sock.close()
        print("✅ Can bind to 0.0.0.0 (external access possible)")
        
    except Exception as e:
        print(f"❌ Network issue: {e}")

def check_firewall():
    """Check Windows Firewall status"""
    print("\n=== Firewall Check ===")
    
    try:
        # Check if port 8085 is allowed through firewall
        result = subprocess.run(
            ['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=all'],
            capture_output=True, text=True, timeout=10
        )
        
        if '8085' in result.stdout:
            print("✅ Port 8085 found in firewall rules")
        else:
            print("⚠️  Port 8085 not found in firewall rules")
            print("   Consider adding firewall rule for Arctic Media")
            
    except Exception as e:
        print(f"❌ Cannot check firewall: {e}")

def test_http_requests():
    """Test various HTTP requests"""
    print("\n=== HTTP Request Tests ===")
    
    test_urls = [
        "http://localhost:8085/",
        "http://localhost:8085/health",
        "http://localhost:8085/login",
        "http://127.0.0.1:8085/",
        "http://0.0.0.0:8085/"
    ]
    
    for url in test_urls:
        try:
            response = requests.get(url, timeout=5)
            print(f"✅ {url}: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"❌ {url}: Connection refused")
        except Exception as e:
            print(f"❌ {url}: {e}")

def main():
    """Run all checks"""
    print("🔍 Arctic Media HTTP Troubleshooting")
    print("=" * 50)
    
    # Run all checks
    check_port_availability()
    check_network_connectivity()
    check_firewall()
    
    if check_server_status():
        test_http_requests()
    
    print("\n" + "=" * 50)
    print("🔧 Common Solutions:")
    print("1. Make sure ArcticMedia.exe is running")
    print("2. Check if port 8085 is not used by another application")
    print("3. Try accessing http://localhost:8085 in browser")
    print("4. Check Windows Firewall settings")
    print("5. Restart the server if needed")

if __name__ == "__main__":
    main()
