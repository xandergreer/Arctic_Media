#!/usr/bin/env python3
"""Simple test to check if scanner functions can be imported and basic functionality works."""

try:
    print("Testing scanner imports...")
    
    # Test basic imports
    from app.scanner import scan_movie_library_sync, scan_tv_library_sync
    print("✓ Scanner functions imported successfully")
    
    # Test models import
    from app.models import Library, MediaKind
    print("✓ Models imported successfully")
    
    # Test database imports
    from app.database import get_engine
    print("✓ Database imports successful")
    
    # Test basic scanner logic without DB
    from app.utils import parse_movie_from_path
    test_result = parse_movie_from_path("Test Movie (2020).mp4")
    print(f"✓ Movie parser works: {test_result}")
    
    print("\n✅ All basic scanner components are working!")
    print("The issue might be with the specific scan request or database state.")
    
except Exception as e:
    print(f"❌ Scanner test failed: {e}")
    import traceback
    traceback.print_exc()
