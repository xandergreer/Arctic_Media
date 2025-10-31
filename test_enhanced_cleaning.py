#!/usr/bin/env python3
"""Test the enhanced TV title cleaning"""

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app.utils import _clean_show_title_enhanced, parse_tv_parts

# Test cases based on your current database entries
test_cases = [
    # Current problematic titles from your database
    "Fish.Hooks.S01-S03.720p.DSNY.WEBRip.AAC2.0.x264-TVSmash",
    "Invincible.2021.S03E07.1080p.WEB.h264-ETHEL", 
    "Ted.S01E01.1080p.WEB.h264-ETHEL",
    
    # Additional test cases
    "Yellowstone.2018.S05E11.Three.Fifty-Three.1080p.WEB.h264-ETHEL",
    "The.Last.of.Us.S01E06.Kin.1080p.WEB.h264-ETHEL",
    "Murder.Bot.S01E01.720p.WEB.x264-TVSmash",
    "Fish Hooks S01E01 720p DSNY WEBRip AAC2.0 x264-TVSmash",
    
    # Good titles that should remain clean
    "Yellowstone",
    "The Last Of Us", 
    "Murder Bot",
    "Fish Hooks"
]

print("Testing Enhanced Title Cleaning")
print("=" * 50)

for test_title in test_cases:
    cleaned = _clean_show_title_enhanced(test_title)
    print(f"Original: {test_title}")
    print(f"Cleaned:  {cleaned}")
    print("-" * 30)

print("\nTesting Full TV Parsing")
print("=" * 50)

# Test parsing with some sample paths
test_paths = [
    ("Fish.Hooks.S01-S03.720p.DSNY.WEBRip.AAC2.0.x264-TVSmash", "Fish.Hooks.S01E01.720p.DSNY.WEBRip.AAC2.0.x264-TVSmash.mkv"),
    ("Invincible.2021", "Invincible.2021.S03E07.1080p.WEB.h264-ETHEL.mkv"),
    ("Ted", "Ted.S01E01.1080p.WEB.h264-ETHEL.mkv"),
    ("Yellowstone", "Yellowstone.S05E11.Three.Fifty-Three.1080p.WEB.h264-ETHEL.mkv")
]

for rel_root, filename in test_paths:
    result = parse_tv_parts(rel_root, filename)
    if result:
        show_title, season, episode, ep_title = result
        print(f"Path: {rel_root}/{filename}")
        print(f"Parsed: Show='{show_title}', S{season:02d}E{episode:02d}, Title='{ep_title}'")
    else:
        print(f"Path: {rel_root}/{filename}")
        print("Parsed: FAILED")
    print("-" * 30)
