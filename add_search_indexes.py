#!/usr/bin/env python3
"""
Database migration script to add search performance indexes.
Run this script to add the title index for improved search performance.
"""

import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import get_engine

async def add_search_indexes():
    """Add database indexes to improve search performance."""
    engine = get_engine()

    try:
        async with engine.begin() as conn:
            print("Adding search performance indexes...")

            # Add index on title field for MediaItem table
            await conn.exec_driver_sql("""
                CREATE INDEX IF NOT EXISTS ix_media_item_title
                ON media_items (title);
            """)

            print("Search performance indexes added successfully!")
            print("Your search should now be much faster.")

    except Exception as e:
        print(f"Error adding indexes: {e}")
        print("You may need to add them manually in your database.")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(add_search_indexes())
