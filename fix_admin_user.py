#!/usr/bin/env python3
"""
Fix the first user to have admin privileges
"""

import asyncio
from app.database import init_db, get_db
from app.models import User, UserRole

async def fix_admin_user():
    """Fix first user to have admin privileges"""
    print("🔧 Fixing First User Admin Privileges")
    print("=" * 50)
    
    # Initialize database
    await init_db()
    
    async for db in get_db():
        from sqlalchemy import select, func
        user_count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
        print(f"Current user count: {user_count}")
        
        if user_count == 0:
            print("ℹ️  No users exist yet")
            return
        
        # Get the first user (by creation date)
        first_user = (await db.execute(
            select(User).order_by(User.created_at.asc()).limit(1)
        )).scalar_one()
        
        print(f"First user: {first_user.username} ({first_user.email})")
        print(f"Current role: {first_user.role}")
        print(f"Current is_admin: {first_user.is_admin}")
        
        if first_user.role == UserRole.admin:
            print("✅ First user already has admin role!")
        else:
            print("🔧 Updating first user to admin role...")
            first_user.role = UserRole.admin
            db.add(first_user)
            await db.commit()
            await db.refresh(first_user)
            
            print(f"✅ Updated first user:")
            print(f"   Role: {first_user.role}")
            print(f"   is_admin: {first_user.is_admin}")
        
        # Show all users
        print("\n📋 All users:")
        users = (await db.execute(select(User).order_by(User.created_at.asc()))).scalars().all()
        for user in users:
            print(f"   {user.username} ({user.email}) - Role: {user.role} - Admin: {user.is_admin}")
        
        break

if __name__ == "__main__":
    asyncio.run(fix_admin_user())

