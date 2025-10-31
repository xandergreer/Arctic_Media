#!/usr/bin/env python3
"""
Simple test to see what happens when we call the scan endpoint directly.
This bypasses the web interface to test the API directly.
"""

import requests
import json
import time

def test_scan_endpoint():
    """Test the scan endpoint directly."""
    base_url = "http://localhost:8080"  # Adjust port if needed
    
    try:
        session = requests.Session()
        
        # First login
        login_data = {
            "email": "admin@test.com", 
            "password": "admin123"
        }
        
        print("🔐 Attempting login...")
        login_resp = session.post(f"{base_url}/auth/login", json=login_data, timeout=10)
        if login_resp.status_code == 200:
            print("✅ Login successful!")
        else:
            print(f"❌ Login failed: {login_resp.status_code}")
            print(f"Response: {login_resp.text}")
            return
        
        # Get libraries
        print("\n📚 Getting libraries...")
        libs_resp = session.get(f"{base_url}/libraries", timeout=10)
        if libs_resp.status_code == 200:
            libraries = libs_resp.json()
            print(f"✅ Found {len(libraries)} libraries")
            
            if not libraries:
                print("⚠️ No libraries to test")
                return
            
            # Test first library
            lib = libraries[0]
            lib_id = lib["id"]
            lib_name = lib["name"]
            
            print(f"\n🎬 Testing scan of: {lib_name}")
            
            # Try synchronous scan first (simpler)
            print("📡 Calling synchronous scan endpoint...")
            scan_resp = session.post(f"{base_url}/libraries/{lib_id}/scan", timeout=120)
            print(f"📊 Scan response status: {scan_resp.status_code}")
            
            if scan_resp.status_code == 200:
                result = scan_resp.json()
                print(f"✅ Scan successful! Result: {json.dumps(result, indent=2)}")
            else:
                error_text = scan_resp.text
                print(f"❌ Scan failed! Response: {error_text}")
            
            # Also try background scan
            print(f"\n🔄 Testing background scan...")
            bg_resp = session.post(f"{base_url}/libraries/{lib_id}/scan?background=true", timeout=30)
            print(f"📊 Background scan response status: {bg_resp.status_code}")
            
            if bg_resp.status_code == 200:
                bg_result = bg_resp.json()
                print(f"✅ Background scan queued: {json.dumps(bg_result, indent=2)}")
                
                if bg_result.get("job_id"):
                    job_id = bg_result["job_id"]
                    print(f"⏳ Polling job {job_id}...")
                    
                    # Poll for 30 seconds
                    for i in range(30):
                        time.sleep(1)
                        job_resp = session.get(f"{base_url}/jobs/{job_id}", timeout=10)
                        if job_resp.status_code == 200:
                            job_data = job_resp.json()
                            status = job_data.get("status", "unknown")
                            progress = job_data.get("progress", 0)
                            total = job_data.get("total", 0)
                            
                            print(f"  Status: {status} ({progress}/{total})")
                            
                            if status == "done":
                                result = job_data.get("result", {})
                                print(f"✅ Background scan completed: {json.dumps(result, indent=2)}")
                                break
                            elif status == "failed":
                                message = job_data.get("message", "Unknown error")
                                print(f"❌ Background scan failed: {message}")
                                break
                        else:
                            print(f"⚠️ Failed to poll job: {job_resp.status_code}")
                            break
                    else:
                        print("⏰ Background scan polling timed out")
            else:
                bg_error = bg_resp.text
                print(f"❌ Background scan failed: {bg_error}")
        else:
            print(f"❌ Failed to get libraries: {libs_resp.status_code}")
            print(f"Response: {libs_resp.text}")
                
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure ArcticMedia.exe is running on localhost:8080")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🧪 Testing Arctic Media Scan API")
    print("=" * 50)
    test_scan_endpoint()
