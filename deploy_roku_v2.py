import os
import io
import zipfile
import requests
import sys

# Configuration
ROKU_IP = "192.168.1.139"
ROKU_USER = "rokudev"
ROKU_PASS = "Titanfall1"  # Updated via user input
SOURCE_DIR = "clients/roku_new"

def make_zip(source_dir):
    print(f"Zipping {source_dir}...")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                archive_name = os.path.relpath(file_path, source_dir)
                zip_file.write(file_path, archive_name)
    zip_buffer.seek(0)
    return zip_buffer

def deploy():
    print(f"Deploying to {ROKU_IP}...")
    zip_data = make_zip(SOURCE_DIR)
    
    url = f"http://{ROKU_IP}/plugin_install"
    files = {
        "mysubmit": (None, "Install"),
        "archive": ("bundle.zip", zip_data, "application/zip")
    }
    
    try:
        # Use DigestAuth as Roku often uses it
        from requests.auth import HTTPDigestAuth
        r = requests.post(
            url, 
            files=files, 
            auth=HTTPDigestAuth(ROKU_USER, ROKU_PASS),
            timeout=10
        )
        
        print(f"Response Status: {r.status_code}")
        print(r.text) # PRINT FULL RESPONSE
        
        if "Identical to previous version" in r.text:
            print("Success (Identical version).")
        elif "Install Success" in r.text:
            print("Success: App installed.")
        else:
            print("Deployment potentially failed.")
            import re
            errors = re.findall(r'<font color="red">(.*?)</font>', r.text, re.DOTALL)
            for err in errors:
                print(f"ROKU ERROR: {err.strip()}")
            if not errors:
                # Fallback: print body content roughly
                print("Raw Response Snippet:")
                print(r.text[:1000])
            
    except Exception as e:
        print(f"Deployment Error: {e}")

if __name__ == "__main__":
    deploy()
