#!/usr/bin/env python3
"""Create a minimal working scanner test that bypasses all the complex background job stuff."""

import asyncio
import os
from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker
from app.database import get_engine
from app.models import Library
from app.scanner import scan_tv_library_sync, scan_movie_library_sync

async def test_direct_scan():
    """Test scanner directly without background jobs."""
    try:
        # Get database connection
        async_engine = get_engine()
        db_url = str(async_engine.url).replace("sqlite+aiosqlite://", "sqlite://")
        sync_engine = create_engine(db_url, echo=False)
        Session = sessionmaker(bind=sync_engine)
        
        with Session() as session:
            # Get the test library
            library = session.execute(select(Library)).scalar_one_or_none()
            if not library:
                print("❌ No library found in database")
                return False
            
            print(f"📁 Found library: {library.name} -> {library.path}")
            print(f"📂 Type: {library.type}")
            print(f"📂 Path exists: {os.path.exists(library.path)}")
            
            # Set debug mode
            os.environ["SCANNER_DEBUG"] = "1"
            
            # Run appropriate scanner
            if library.type == "movie":
                print("🎬 Running movie scanner...")
                results = scan_movie_library_sync(
                    session=session,
                    library=library,
                    library_name=library.name,
                    library_type=library.type,
                    library_id=library.id
                )
            elif library.type == "tv":
                print("📺 Running TV scanner...")
                results = scan_tv_library_sync(
                    session=session,
                    library=library,
                    library_name=library.name,
                    library_type=library.type,
                    library_id=library.id
                )
            else:
                print(f"❌ Unknown library type: {library.type}")
                return False
            
            print(f"📊 Scan results: {results}")
            print("✅ Direct scanner test completed!")
            return True
            
    except Exception as e:
        print(f"❌ Direct scanner test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_direct_scan())
    exit(0 if success else 1)
