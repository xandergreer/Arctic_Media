#!/usr/bin/env python3
"""
Test script to verify Arctic Media configuration
"""

from app.config import settings

def test_config():
    print("=== Arctic Media Configuration Test ===")
    print(f"Brand Name: {settings.BRAND_NAME}")
    print(f"App Name: {settings.APP_NAME}")
    print(f"Host: {settings.HOST}")
    print(f"Port: {settings.PORT}")
    print(f"Database URL: {settings.DATABASE_URL}")
    print(f"FFmpeg Path: {settings.FFMPEG_PATH}")
    print(f"Environment: {settings.ENV}")
    print(f"Debug: {settings.DEBUG}")
    print("=" * 40)
    
    # Test external access configuration
    if settings.HOST == "0.0.0.0":
        print("✅ External access enabled (0.0.0.0)")
        print(f"   Access URL: http://YOUR_IP:{settings.PORT}")
    else:
        print("⚠️  External access disabled (localhost only)")
        print(f"   Access URL: http://localhost:{settings.PORT}")

if __name__ == "__main__":
    test_config()
