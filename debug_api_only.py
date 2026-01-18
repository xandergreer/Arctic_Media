
import requests

API_URL = "http://127.0.0.1:8085/api/season/14c5d029-9186-4c0a-be8d-f68e4e4bd6dd" # Gumball S01

print(f"--- Checking API Response: {API_URL} ---")
try:
    resp = requests.get(API_URL)
    if resp.status_code == 200:
        data = resp.json()
        episodes = data.get('episodes', [])
        if episodes:
            print("\nSample Episode (First 1):")
            ep = episodes[0]
            print(f"  Title: '{ep.get('title')}'")
            print(f"  ID: '{ep.get('id')}'")
            print(f"  Poster: '{ep.get('poster_url')}'")
            print(f"  Backdrop: '{ep.get('backdrop_url')}'")
            print(f"  Still: '{ep.get('still')}'") 
        else:
            print("No episodes found.")
    else:
        print(f"API Error: {resp.status_code}")
except Exception as e:
    print(f"Request failed: {e}")
