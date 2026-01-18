import socket
import time

IP = "192.168.1.139"
PORT = 8085

print(f"Connecting to Roku Logs at {IP}:{PORT}...")

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0) # Short timeout for connection
    s.connect((IP, PORT))
    print("Connected! Launching App...")
    
    # Launch via HTTP
    import requests
    try:
        requests.post(f"http://{IP}:8060/launch/dev", timeout=5)
        print("Launch signal sent.")
    except Exception as e:
        print(f"Launch failed: {e}")

    print("Listening for 20 seconds...")
    
    start = time.time()
    s.settimeout(0.5) # Short timeout for read loop
    
    while time.time() - start < 20:
        try:
            data = s.recv(4096)
            if data:
                print(data.decode('utf-8', 'ignore'), end='')
        except socket.timeout:
            continue
        except Exception as e:
            print(f"\nRead Error: {e}")
            break
            
    print("\nClosing connection.")
    s.close()
except Exception as e:
    print(f"Connection Failed: {e}")
    print("Make sure the Roku is on and Developer Mode is enabled.")
