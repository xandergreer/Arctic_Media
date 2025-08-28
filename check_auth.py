#!/usr/bin/env python3
"""
Authentication troubleshooting script for Arctic Media
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database import init_db, get_db
from app.models import User
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

async def check_auth_status():
    """Check authentication status and database"""
    print("=== Arctic Media Authentication Check ===")
    
    # Initialize database
    await init_db()
    
    # Get database session
    async for db in get_db():
        try:
            # Check if any users exist
            user_count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
            print(f"Total users in database: {user_count}")
            
            if user_count == 0:
                print("❌ No users found in database!")
                print("   You need to register a user first.")
                print("   Visit: http://YOUR_IP:8000/register")
                return
            
            # List all users
            users = (await db.execute(select(User))).scalars().all()
            print("\n📋 Users in database:")
            for user in users:
                admin_status = " (Admin)" if getattr(user, 'is_admin', False) else ""
                print(f"   - {user.username} ({user.email}){admin_status}")
            
            print(f"\n✅ Database is accessible and contains {user_count} user(s)")
            print("\n🔧 Troubleshooting steps:")
            print("1. Make sure you're using the correct username/email")
            print("2. Make sure you're using the correct password")
            print("3. Try logging in with username OR email")
            print("4. Check if the server is accessible from your device")
            print("5. Try accessing: http://YOUR_IP:8000/login")
            
        except Exception as e:
            print(f"❌ Database error: {e}")
        finally:
            break

if __name__ == "__main__":
    asyncio.run(check_auth_status())
