
import asyncio
import os
import sys

# Ensure app imports work
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

from app.database import init_db, get_sessionmaker
from app.metadata import enrich_library_sync, enrich_library
from sqlalchemy import select, func
from app.models import MediaItem, Library, MediaKind
from app.config import settings

async def force_refresh():
    print("--- DIRECT BACKEND FORCE REFRESH ---")
    await init_db()
    
    SessionLocal = get_sessionmaker()
    async with SessionLocal() as session:
        # 1. Find the TV Library
        print("Finding TV Library...")
        res = await session.execute(select(Library).where(Library.type == "tv"))
        lib = res.scalars().first()
        
        if not lib:
            print("ERROR: No TV library found in DB.")
            return
            
        print(f"Target Library: {lib.name} ({lib.id})")
        
        # DEBUG: Count items
        res = await session.execute(select(func.count()).select_from(MediaItem).where(MediaItem.library_id == lib.id))
        count = res.scalar()
        print(f"DEBUG: Library has {count} items total.")
        
        # 2. Get API Key
        api_key = settings.TMDB_API_KEY
        if not api_key:
            print("ERROR: TMDB_API_KEY is missing in settings.")
            return

        print(f"Using API Key: {api_key[:4]}...")
        
        async def prog(cur, total, item=None):
            if item:
                print(f"Processing: {item.title} ({item.kind}) ID={item.id}")
            await asyncio.sleep(0) # yield
        
        print("Starting FORCE enrichment for TV Library...")
        stats = await enrich_library(
            session, 
            api_key, 
            lib.id, 
            force=True,     # FORCE UPDATE
            only_missing=False, 
            progress_cb=prog
        )
        print("Enrichment Stats:", stats)
        print("\n--- RESULTS ---")
        print(f"Matched: {stats.get('matched')}")
        print(f"Enriched: {stats.get('enriched')} (This is the number of items updated)")
        print(f"Skipped: {stats.get('skipped')}")
        
        if stats.get('enriched', 0) > 0:
            print("\nSUCCESS! Changes made. Committing...")
            await session.commit()
            print("Done.")
        else:
            print("\nZero enriched? Check logs for API errors.")

if __name__ == "__main__":
    # Windows SelectorEventLoop policy fix if needed?
    # python 3.8+ on windows defaults to Proactor, which is fine for aiosqlite usually
    try:
        asyncio.run(force_refresh())
    except KeyboardInterrupt:
        pass
