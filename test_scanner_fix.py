#!/usr/bin/env python3
"""Test scanner functionality with debug logging."""

import os
import asyncio
from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker
from app.database import get_engine
from app.models import Library
from app.scanner import scan_movie_library_sync

async def test_scanner():
    """Test scanner with debug mode enabled."""
    try:
        # Enable debug mode
        os.environ["SCANNER_DEBUG"] = "1"
        
        # Get sync engine
        async_engine = get_engine()
        db_url = str(async_engine.url)
        if db_url.startswith("sqlite+aiosqlite://"):
            db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")
        
        sync_engine = create_engine(db_url, echo=False)
        Session = sessionmaker(bind=sync_engine)
        
        with Session() as session:
            # Find the test library
            library = session.execute(select(Library).where(Library.name == "Test Movies")).scalar_one_or_none()
            if not library:
                print("❌ No test library found - run quick_setup.py first")
                return False
            
            print(f"📁 Testing scan of library: {library.name} -> {library.path}")
            print(f"📂 Path exists: {os.path.exists(library.path)}")
            
            # Run the scanner
            results = scan_movie_library_sync(
                session=session,
                library=library,
                library_name=library.name,
                library_type=library.type,
                library_id=library.id
            )
            
            print(f"📊 Scan results: {results}")
            print("✓ Scanner test completed successfully")
            return True
            
    except Exception as e:
        print(f"❌ Scanner test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_scanner())
    exit(0 if success else 1)
