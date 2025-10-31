#!/usr/bin/env python3
"""Quick setup script to create minimal user and library for testing scanner."""

import asyncio
import sys
from pathlib import Path
from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker
from app.database import get_engine
from app.models import User, Library
import hashlib

async def setup_test_data():
    """Create minimal test user and library."""
    try:
        # Get async engine and convert to sync
        async_engine = get_engine()
        db_url = str(async_engine.url)
        if db_url.startswith("sqlite+aiosqlite://"):
            db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")
        
        # Create sync engine
        sync_engine = create_engine(db_url, echo=False)
        Session = sessionmaker(bind=sync_engine)
        
        with Session() as session:
            # Check if admin user exists
            existing_user = session.execute(select(User).where(User.email == "admin@test.com")).scalar_one_or_none()
            if not existing_user:
                # Create admin user
                admin_user = User(
                    email="admin@test.com",
                    username="admin",
                    password_hash=hashlib.sha256("admin123".encode()).hexdigest(),
                    role="admin"
                )
                session.add(admin_user)
                session.flush()
                print(f"Created admin user: {admin_user.email}")
            else:
                admin_user = existing_user
                print(f"Using existing admin user: {admin_user.email}")
            
            # Check if test library exists
            existing_lib = session.execute(select(Library).where(Library.name == "Test Movies")).scalar_one_or_none()
            if not existing_lib:
                # Create test movie library
                test_lib = Library(
                    owner_user_id=admin_user.id,
                    name="Test Movies",
                    slug="test-movies",
                    type="movie",
                    path="f:/test_movies"  # Adjust this path as needed
                )
                session.add(test_lib)
                session.flush()
                print(f"Created test library: {test_lib.name} -> {test_lib.path}")
            else:
                print(f"Using existing library: {existing_lib.name} -> {existing_lib.path}")
            
            session.commit()
            print("✓ Setup complete - you can now test scanning")
            
    except Exception as e:
        print(f"Setup failed: {e}")
        return False
    return True

if __name__ == "__main__":
    success = asyncio.run(setup_test_data())
    sys.exit(0 if success else 1)
