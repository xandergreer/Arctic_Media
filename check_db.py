#!/usr/bin/env python3
"""Check database state."""

import asyncio
from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker
from app.database import get_engine
from app.models import Library, User, MediaItem

async def check_db():
    """Check database contents."""
    async_engine = get_engine()
    db_url = str(async_engine.url).replace("sqlite+aiosqlite://", "sqlite://")
    sync_engine = create_engine(db_url)
    Session = sessionmaker(bind=sync_engine)
    
    with Session() as session:
        # Check users
        users = session.execute(select(User)).scalars().all()
        print(f"Users ({len(users)}):")
        for user in users:
            print(f"  {user.email} ({user.role})")
        
        # Check libraries  
        libraries = session.execute(select(Library)).scalars().all()
        print(f"\nLibraries ({len(libraries)}):")
        for lib in libraries:
            print(f"  {lib.name}: {lib.path} ({lib.type})")
        
        # Check media items
        items = session.execute(select(MediaItem)).scalars().all()
        print(f"\nMedia Items ({len(items)}):")
        for item in items[:5]:  # Show first 5
            print(f"  {item.title} ({item.kind})")
        if len(items) > 5:
            print(f"  ... and {len(items) - 5} more")

if __name__ == "__main__":
    asyncio.run(check_db())
