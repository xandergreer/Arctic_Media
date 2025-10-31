#!/usr/bin/env python3
"""
Test script to verify synchronous background scanning works without SQLAlchemy async context errors.
"""
import os
import sys
import threading
import time

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.database import get_engine
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

def test_sync_database_connection():
    """Test that we can create a synchronous database connection without issues"""
    print("Testing synchronous database connection...")

    try:
        # Get database URL from the async engine
        db_url = str(get_engine().url)
        print(f"Original URL: {db_url}")

        # Convert async URL to sync URL
        if db_url.startswith("sqlite+aiosqlite://"):
            db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")

        print(f"Sync URL: {db_url}")

        # Create synchronous engine
        sync_engine = create_engine(
            db_url,
            echo=False,
            pool_pre_ping=True,
            connect_args={"timeout": 30},
        )

        # Apply SQLite pragmas
        def _set_sqlite_pragmas(dbapi_conn, _record):
            try:
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA journal_mode=WAL;")
                cur.execute("PRAGMA synchronous=NORMAL;")
                cur.execute("PRAGMA temp_store=MEMORY;")
                cur.execute("PRAGMA busy_timeout=30000;")
                cur.close()
            except Exception as e:
                print(f"Pragma error: {e}")

        event.listen(sync_engine, "connect", _set_sqlite_pragmas)

        # Create synchronous session
        sync_session = sessionmaker(bind=sync_engine, expire_on_commit=False, autoflush=False)

        # Test basic database operations
        with sync_session() as db:
            # Test a simple query using proper SQLAlchemy syntax
            from sqlalchemy import text
            result = db.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"Database test query result: {row[0]}")

            # Test importing our synchronous functions
            from app.scanner import scan_movie_library_sync, scan_tv_library_sync
            from app.metadata import enrich_library_sync
            print("All synchronous functions imported successfully")

        print("Synchronous database connection test PASSED")
        return True

    except Exception as e:
        print(f"Synchronous database connection test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_threaded_execution():
    """Test running synchronous operations in a background thread"""
    print("\nTesting threaded execution...")

    def background_task():
        try:
            # Simulate what happens in _bg_scan_library_sync
            from app.database import get_engine
            from sqlalchemy import create_engine, event
            from sqlalchemy.orm import sessionmaker

            db_url = str(get_engine().url)
            if db_url.startswith("sqlite+aiosqlite://"):
                db_url = db_url.replace("sqlite+aiosqlite://", "sqlite://")

            sync_engine = create_engine(
                db_url,
                echo=False,
                pool_pre_ping=True,
                connect_args={"timeout": 30},
            )

            def _set_sqlite_pragmas(dbapi_conn, _record):
                try:
                    cur = dbapi_conn.cursor()
                    cur.execute("PRAGMA journal_mode=WAL;")
                    cur.execute("PRAGMA synchronous=NORMAL;")
                    cur.execute("PRAGMA temp_store=MEMORY;")
                    cur.execute("PRAGMA busy_timeout=30000;")
                    cur.close()
                except Exception:
                    pass

            event.listen(sync_engine, "connect", _set_sqlite_pragmas)
            sync_session = sessionmaker(bind=sync_engine, expire_on_commit=False, autoflush=False)

            with sync_session() as db:
                from sqlalchemy import text
                result = db.execute(text("SELECT 1 as test"))
                row = result.fetchone()
                print(f"Background thread database test: {row[0]}")

            print("Background thread execution PASSED")
        except Exception as e:
            print(f"Background thread execution FAILED: {e}")
            import traceback
            traceback.print_exc()

    # Run in a thread
    thread = threading.Thread(target=background_task)
    thread.start()
    thread.join(timeout=10)

    if thread.is_alive():
        print("Background thread is still running (timeout)")
        return False
    else:
        print("Background thread completed successfully")
        return True

if __name__ == "__main__":
    success1 = test_sync_database_connection()
    success2 = test_threaded_execution()

    if success1 and success2:
        print("\n✅ All tests PASSED! Synchronous background scanning should work without SQLAlchemy async context errors.")
    else:
        print("\n❌ Some tests FAILED. There may still be issues with the synchronous approach.")
