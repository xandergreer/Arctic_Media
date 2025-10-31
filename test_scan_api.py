#!/usr/bin/env python3
"""Diagnostic script to test scanner after .exe rebuild."""

import requests
import json
import time

def test_scan_api():
    """Test the scan API endpoint directly."""
    base_url = "http://localhost:8080"  # Adjust if your server runs on different port
    
    try:
        # First, let's check if the server is running
        print("🔍 Checking if server is running...")
        response = requests.get(f"{base_url}/", timeout=5)
        print(f"✓ Server is running (status: {response.status_code})")
        
        # Get libraries
        print("\n📚 Getting libraries...")
        auth = ("admin@test.com", "admin123")  # Adjust credentials if different
        
        # Try to login first (might be needed)
        login_data = {"email": "admin@test.com", "password": "admin123"}
        login_response = requests.post(f"{base_url}/auth/login", json=login_data, timeout=10)
        if login_response.status_code == 200:
            print("✓ Login successful")
            # Get session cookie
            session = requests.Session()
            session.cookies.update(login_response.cookies)
        else:
            print(f"⚠️ Login failed: {login_response.status_code}")
            session = requests.Session()
        
        # Get libraries list
        libs_response = session.get(f"{base_url}/libraries", timeout=10)
        if libs_response.status_code == 200:
            libraries = libs_response.json()
            print(f"✓ Found {len(libraries)} libraries")
            
            if libraries:
                # Test scanning the first library
                lib = libraries[0]
                lib_id = lib.get("id")
                lib_name = lib.get("name", "Unknown")
                
                print(f"\n🎬 Testing scan of library: {lib_name} (ID: {lib_id})")
                
                # Try background scan first
                scan_response = session.post(f"{base_url}/libraries/{lib_id}/scan?background=true", timeout=30)
                if scan_response.status_code == 200:
                    scan_result = scan_response.json()
                    print(f"✓ Background scan started: {scan_result}")
                    
                    if scan_result.get("job_id"):
                        job_id = scan_result["job_id"]
                        print(f"📊 Polling job {job_id}...")
                        
                        # Poll the job for up to 60 seconds
                        for i in range(60):
                            time.sleep(1)
                            job_response = session.get(f"{base_url}/jobs/{job_id}", timeout=10)
                            if job_response.status_code == 200:
                                job_data = job_response.json()
                                status = job_data.get("status", "unknown")
                                print(f"  Status: {status}")
                                
                                if status == "done":
                                    result = job_data.get("result", {})
                                    print(f"✅ Scan completed! Results: {result}")
                                    break
                                elif status == "failed":
                                    print(f"❌ Scan failed: {job_data.get('message', 'Unknown error')}")
                                    break
                            else:
                                print(f"⚠️ Failed to get job status: {job_response.status_code}")
                                break
                        else:
                            print("⏰ Scan timed out after 60 seconds")
                    
                else:
                    print(f"❌ Background scan failed: {scan_response.status_code}")
                    print(f"Response: {scan_response.text}")
                    
                    # Try synchronous scan as fallback
                    print("\n🔄 Trying synchronous scan...")
                    sync_scan_response = session.post(f"{base_url}/libraries/{lib_id}/scan", timeout=120)
                    if sync_scan_response.status_code == 200:
                        sync_result = sync_scan_response.json()
                        print(f"✅ Synchronous scan completed: {sync_result}")
                    else:
                        print(f"❌ Synchronous scan also failed: {sync_scan_response.status_code}")
                        print(f"Response: {sync_scan_response.text}")
            else:
                print("⚠️ No libraries found to test")
        else:
            print(f"❌ Failed to get libraries: {libs_response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure your .exe is running on localhost:8080")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Testing Arctic Media Scanner API")
    print("=" * 50)
    test_scan_api()
