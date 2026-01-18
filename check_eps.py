
import asyncio
from sqlalchemy import select
from app.database import get_sessionmaker
from app.models import MediaItem, MediaKind

async def check_episodes():
    SessionLocal = get_sessionmaker()
    async with SessionLocal() as db:
        q = select(MediaItem).where(MediaItem.kind == MediaKind.episode).limit(10)
        res = await db.execute(q)
        eps = res.scalars().all()
        
        print(f"Found {len(eps)} episodes")
        for e in eps:
            print(f"ID: {e.id}")
            print(f"  Title: '{e.title}'")
            print(f"  Kind: {e.kind}")
            # print(f"  ExtraJSON: {e.extra_json}")
            ej = e.extra_json or {}
            print(f"  EJ Name: '{ej.get('name')}'")
            print(f"  EJ Still: '{ej.get('still')}'")
            print(f"  PosterURL: '{e.poster_url}'")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(check_episodes())
