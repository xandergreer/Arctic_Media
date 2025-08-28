#!/usr/bin/env python3
"""
Test script to verify remote access settings functionality
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database import init_db, get_db
from app.models import ServerSetting
from app.settings_api import DEFAULTS
from sqlalchemy import select, insert, update

async def test_remote_settings():
    """Test remote access settings functionality"""
    print("=== Testing Remote Access Settings ===")
    
    # Initialize database
    await init_db()
    
    # Get database session
    async for db in get_db():
        try:
            # Test 1: Check current settings
            print("\n1. Current Settings:")
            remote_settings = (await db.execute(
                select(ServerSetting).where(ServerSetting.key == "remote")
            )).scalars().first()
            
            server_settings = (await db.execute(
                select(ServerSetting).where(ServerSetting.key == "server")
            )).scalars().first()
            
            if remote_settings:
                print(f"   Remote settings: {remote_settings.value}")
            else:
                print("   No remote settings found (using defaults)")
                
            if server_settings:
                print(f"   Server settings: {server_settings.value}")
            else:
                print("   No server settings found (using defaults)")
            
            # Test 2: Set test settings
            print("\n2. Setting Test Configuration:")
            test_remote = {
                "enable_remote_access": True,
                "public_base_url": "https://myarctic.example.com",
                "port": 32400,
                "upnp": True,
                "allow_insecure_fallback": "ask"
            }
            
            test_server = {
                "server_host": "0.0.0.0",
                "server_port": 8000,
                "external_access": True
            }
            
            # Update remote settings
            if remote_settings:
                await db.execute(
                    update(ServerSetting)
                    .where(ServerSetting.key == "remote")
                    .values(value=test_remote)
                )
            else:
                await db.execute(
                    insert(ServerSetting).values(key="remote", value=test_remote)
                )
            
            # Update server settings
            if server_settings:
                await db.execute(
                    update(ServerSetting)
                    .where(ServerSetting.key == "server")
                    .values(value=test_server)
                )
            else:
                await db.execute(
                    insert(ServerSetting).values(key="server", value=test_server)
                )
            
            await db.commit()
            print("   ✅ Test settings saved successfully")
            
            # Test 3: Verify settings
            print("\n3. Verifying Settings:")
            remote_settings = (await db.execute(
                select(ServerSetting).where(ServerSetting.key == "remote")
            )).scalars().first()
            
            server_settings = (await db.execute(
                select(ServerSetting).where(ServerSetting.key == "server")
            )).scalars().first()
            
            print(f"   Remote: {remote_settings.value}")
            print(f"   Server: {server_settings.value}")
            
            # Test 4: Test server configuration loading
            print("\n4. Server Configuration Test:")
            if server_settings and server_settings.value:
                config = server_settings.value
                host = config.get("server_host", "127.0.0.1")
                port = config.get("server_port", 8000)
                external = config.get("external_access", False)
                
                print(f"   Host: {host}")
                print(f"   Port: {port}")
                print(f"   External Access: {'enabled' if external else 'disabled'}")
                
                if host == "0.0.0.0":
                    print("   ✅ External access is enabled")
                else:
                    print("   ⚠️  External access is disabled")
            
            print("\n✅ All tests completed successfully!")
            print("\n🔧 Next Steps:")
            print("1. Access the settings page at: http://localhost:8000/settings")
            print("2. Go to 'Remote Access' tab")
            print("3. Modify server port or host settings")
            print("4. Click 'Restart Server' to apply changes")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            break

if __name__ == "__main__":
    asyncio.run(test_remote_settings())
