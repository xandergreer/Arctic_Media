
import sqlite3
import json
import asyncio
import os
import sys

# Ensure app imports work
if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())

from app.config import settings
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models import MediaItem, MediaKind

# Assume DB is at dist/arctic.db
DB_URL = "sqlite+aiosqlite:///dist/arctic.db"

async def trace_enrichment():
    print(f"--- TRACING ENRICHMENT (DB: {DB_URL}) ---")
    
    engine = create_async_engine(DB_URL)
    async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    
    async with async_session() as session:
        print("Loading all episodes...")
        res = await session.execute(select(MediaItem).where(MediaItem.kind == MediaKind.episode))
        episodes = res.scalars().all()
        print(f"Total Episodes found: {len(episodes)}")
        
        err_season_missing = 0
        err_show_missing = 0
        err_show_no_tmdb = 0
        valid_ready = 0
        
        print("\n--- Auditing Hierarchy ---")
        for idx, ep in enumerate(episodes):
            # Resolve Parent (Season)
            season = await session.get(MediaItem, ep.parent_id)
            if not season:
                err_season_missing += 1
                if err_season_missing <= 5: print(f"  [X] Ep '{ep.title}' missing Season ({ep.parent_id})")
                continue
                
            # Resolve Grandparent (Show)
            show = await session.get(MediaItem, season.parent_id)
            if not show:
                err_show_missing += 1
                if err_show_missing <= 5: print(f"  [X] Ep '{ep.title}' (S: {season.title}) missing Show ({season.parent_id})")
                continue
                
            # Check TMDB
            ej = show.extra_json or {}
            if not ej.get("tmdb_id"):
                err_show_no_tmdb += 1
                if err_show_no_tmdb <= 5: print(f"  [X] Ep '{ep.title}' Show '{show.title}' has NO TMDB ID")
                continue
            
            valid_ready += 1
            
        print("\n--- Audit Results ---")
        print(f"Total Episodes: {len(episodes)}")
        print(f"Season Missing: {err_season_missing}")
        print(f"Show Missing:   {err_show_missing}")
        print(f"Show No TMDB:   {err_show_no_tmdb}")
        print(f"Valid/Ready:    {valid_ready}")

if __name__ == "__main__":
    if os.getcwd() not in sys.path: sys.path.append(os.getcwd())
    import sys
    # Hack to allow imports from app.*
    # We need to run this from e:\Arctic_Media
    asyncio.run(trace_enrichment())
