#!/usr/bin/env python3
"""Update test library to use TV directory and test scanner."""

import os
import asyncio
from sqlalchemy import select, create_engine, update
from sqlalchemy.orm import sessionmaker
from app.database import get_engine
from app.models import Library
from app.scanner import scan_tv_library_sync

async def test_tv_scanner():
    """Test TV scanner with real directory."""
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
            # Update the test library to point to TV directory
            library = session.execute(select(Library).where(Library.name == "Test TV")).scalar_one_or_none()
            if library:
                library.path = "F:/TV"
                library.type = "tv"
                library.name = "Test TV"
                session.commit()
                print(f"📁 Updated library: {library.name} -> {library.path}")
            else:
                print("❌ No test library found")
                return False
            
            print(f"📂 Path exists: {os.path.exists(library.path)}")
            
            # Count some files in the directory
            if os.path.exists(library.path):
                file_count = 0
                for root, dirs, files in os.walk(library.path):
                    file_count += len([f for f in files if f.lower().endswith(('.mp4', '.mkv', '.avi', '.mov'))])
                    if file_count > 100:  # Stop counting after 100 for performance
                        break
                print(f"📹 Found ~{file_count}+ video files")
            
            # Run the scanner
            results = scan_tv_library_sync(
                session=session,
                library=library,
                library_name=library.name,
                library_type=library.type,
                library_id=library.id
            )
            
            print(f"📊 Scan results: {results}")
            print("✓ TV Scanner test completed successfully")
            return True
            
    except Exception as e:
        print(f"❌ TV Scanner test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_tv_scanner())
    exit(0 if success else 1)
