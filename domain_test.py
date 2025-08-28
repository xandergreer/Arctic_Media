#!/usr/bin/env python3
"""
Test domain connectivity for arcticmedia.space
"""

import requests
import socket
import dns.resolver
import subprocess

def test_dns_resolution():
    """Test if arcticmedia.space resolves correctly"""
    print("=== DNS Resolution Test ===")
    
    try:
        # Resolve the domain
        answers = dns.resolver.resolve('arcticmedia.space', 'A')
        for answer in answers:
            print(f"✅ arcticmedia.space resolves to: {answer}")
        
        return str(answers[0])
    except Exception as e:
        print(f"❌ DNS resolution failed: {e}")
        return None

def get_public_ip():
    """Get your public IP address"""
    print("\n=== Public IP Check ===")
    
    try:
        response = requests.get('https://api.ipify.org', timeout=5)
        public_ip = response.text
        print(f"✅ Your public IP: {public_ip}")
        return public_ip
    except Exception as e:
        print(f"❌ Could not get public IP: {e}")
        return None

def test_port_connectivity(ip, port):
    """Test if port is accessible from outside"""
    print(f"\n=== Port Connectivity Test ({ip}:{port}) ===")
    
    try:
        # Test with telnet-like connection
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((ip, port))
        sock.close()
        
        if result == 0:
            print(f"✅ Port {port} is open on {ip}")
            return True
        else:
            print(f"❌ Port {port} is closed on {ip}")
            return False
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def test_http_access(domain, port):
    """Test HTTP access to the domain"""
    print(f"\n=== HTTP Access Test ===")
    
    urls_to_test = [
        f"http://{domain}:{port}",
        f"https://{domain}:{port}",
        f"http://{domain}",
        f"https://{domain}"
    ]
    
    for url in urls_to_test:
        try:
            response = requests.get(url, timeout=10, allow_redirects=False)
            print(f"✅ {url}: {response.status_code}")
            if response.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            print(f"❌ {url}: Connection refused")
        except requests.exceptions.SSLError:
            print(f"⚠️  {url}: SSL error (expected for HTTP)")
        except Exception as e:
            print(f"❌ {url}: {e}")
    
    return False

def check_router_config():
    """Check router port forwarding"""
    print("\n=== Router Configuration Check ===")
    
    print("🔧 Manual checks needed:")
    print("1. Access your router admin (usually 192.168.1.1)")
    print("2. Find 'Port Forwarding' section")
    print("3. Verify these rules exist:")
    print("   - External Port: 8096 → Internal Port: 8096")
    print("   - Internal IP: Your computer's IP (192.168.1.129)")
    print("   - Protocol: TCP")
    print("   - Status: Enabled")

def check_firewall():
    """Check Windows Firewall"""
    print("\n=== Windows Firewall Check ===")
    
    try:
        # Check if port 8096 is allowed
        result = subprocess.run(
            ['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=all'],
            capture_output=True, text=True, timeout=10
        )
        
        if '8096' in result.stdout:
            print("✅ Port 8096 found in firewall rules")
        else:
            print("⚠️  Port 8096 not found in firewall rules")
            print("   Adding firewall rule...")
            
            # Add firewall rule
            subprocess.run([
                'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                'name=Arctic Media 8096',
                'dir=in',
                'action=allow',
                'protocol=TCP',
                'localport=8096'
            ], capture_output=True)
            print("✅ Firewall rule added for port 8096")
            
    except Exception as e:
        print(f"❌ Firewall check failed: {e}")

def main():
    """Run all domain tests"""
    print("🌐 Arctic Media Domain Connectivity Test")
    print("=" * 50)
    
    domain = "arcticmedia.space"
    port = 8096
    
    # Test DNS resolution
    resolved_ip = test_dns_resolution()
    
    # Get public IP
    public_ip = get_public_ip()
    
    if resolved_ip and public_ip:
        print(f"\n📊 Comparison:")
        print(f"   DNS resolves to: {resolved_ip}")
        print(f"   Your public IP:  {public_ip}")
        
        if resolved_ip == public_ip:
            print("✅ DNS is correctly pointing to your public IP")
            
            # Test port connectivity
            if test_port_connectivity(public_ip, port):
                # Test HTTP access
                test_http_access(domain, port)
            else:
                print("\n🔧 Port 8096 is not accessible from outside")
                print("   This means port forwarding is not configured correctly")
                check_router_config()
        else:
            print("❌ DNS is not pointing to your current public IP")
            print("   Update your A record to point to:", public_ip)
    
    # Check firewall
    check_firewall()
    
    print("\n" + "=" * 50)
    print("🔧 Next Steps:")
    print("1. Verify port forwarding on your router")
    print("2. Check if your ISP blocks port 8096")
    print("3. Try a different port (like 80 or 443)")
    print("4. Consider using Cloudflare for easier setup")

if __name__ == "__main__":
    main()
