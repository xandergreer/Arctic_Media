import asyncio
from sqlalchemy import select, func
from app.database import get_sessionmaker
from app.models import MediaItem, MediaKind

async def check_dashboard():
    SessionLocal = get_sessionmaker()
    async with SessionLocal() as db:
        # Check counts
        n_movies = (await db.execute(select(func.count()).where(MediaItem.kind == MediaKind.movie))).scalar()
        n_shows = (await db.execute(select(func.count()).where(MediaItem.kind == MediaKind.show))).scalar()
        
        print(f"Movies in DB: {n_movies}")
        print(f"Shows in DB: {n_shows}")
        
        if n_movies > 0:
            m = (await db.execute(select(MediaItem).where(MediaItem.kind == MediaKind.movie).limit(1))).scalar()
            print(f"Sample Movie: {m.title}")
            
            # Get files
            from app.models import MediaFile
            files = (await db.execute(select(MediaFile).where(MediaFile.media_item_id == m.id))).scalars().all()
            for f in files:
                print(f"  - File ID: {f.id}")
                print(f"  - Path (DB): {f.path}")
                
                # Resolve path logic from streaming code
                import os
                from pathlib import Path
                MEDIA_ROOT = Path(os.getenv("ARCTIC_MEDIA_ROOT", "")).expanduser()
                
                p = Path(f.path) if f.path else None
                if p:
                    final_path = p if p.is_absolute() or not MEDIA_ROOT else (MEDIA_ROOT / p)
                    print(f"  - Resolved Path: {final_path}")
                    print(f"  - Exists: {final_path.exists()}")
                else:
                    print("  - NO PATH FOUND")

        if n_shows > 0:
            s = (await db.execute(select(MediaItem).where(MediaItem.kind == MediaKind.show).limit(1))).scalar()
            print(f"Sample Show: {s.title} (Poster: {s.poster_url})")

if __name__ == "__main__":
    asyncio.run(check_dashboard())
