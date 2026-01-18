import requests
from requests.auth import HTTPDigestAuth
import re

ROKU_IP = "192.168.1.139"
USER = "rokudev"
PASS = "Titanfall1"

def check_status():
    url = f"http://{ROKU_IP}/"
    print(f"Checking {url}...")
    try:
        r = requests.get(url, auth=HTTPDigestAuth(USER, PASS), timeout=10)
        if r.status_code == 200:
            print("Successfully connected to Roku Dev Interface.")
            if "Arctic Media V3" in r.text:
                print("PASSED: 'Arctic Media V3' is listed clearly in the web interface.")
            elif "Delete" in r.text:
                print("WARNING: A dev channel IS installed, but 'Arctic Media V3' title not found?")
                print(r.text[:500])
            else:
                print("ERROR: No dev channel appears to be installed.")
        else:
            print(f"Failed to connect. Status: {r.status_code}")
    except Exception as e:
        print(f"Connection Error: {e}")

def launch_app():
    # POST /launch/dev
    url = f"http://{ROKU_IP}:8060/launch/dev"
    print(f"Attempting to launch dev channel via ECP ({url})...")
    try:
        r = requests.post(url, timeout=5)
        if r.status_code == 200:
            print("Launch command sent successfully.")
        else:
            print(f"Launch failed. Status: {r.status_code}")
    except Exception as e:
        print(f"Launch Error: {e}")

if __name__ == "__main__":
    check_status()
    launch_app()
