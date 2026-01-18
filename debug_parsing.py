
import os
import re
from app.utils import parse_tv_parts, _clean_show_title_enhanced

filenames = [
    "Yellowstone.2018.S05E11.Three.Fifty-Three.1080p.WEB.H264-GGEZ.mkv",
    "The.Last.of.Us.S01E06.Kin.1080p.WEB.H264.mkv",
    "Show.Name.S02E03.My.Messy.Episode.Title.720p.WEB-DL.AAC2.0.H.264.mkv",
    "Another.Show.S01E01.Pilot.mkv",
    "Only.Murders.in.the.Building.S02E05.The.Tell.2160p.WEB.H265.mkv"
]

print("--- Testing TV Parsing ---")
for f in filenames:
    res = parse_tv_parts("", f)
    if res:
        show, season, ep, title_guess = res
        print(f"\nFile: {f}")
        print(f"  Show: '{show}'")
        print(f"  S{season:02d}E{ep:02d}")
        print(f"  Guess: '{title_guess}'")
        
        # Simulate scanner logic
        ep_title_core = title_guess.strip() if title_guess else ""
        final_ep_title = f"S{int(season):02d}E{int(ep):02d}" + (f" {ep_title_core}" if ep_title_core else "")
        print(f"  Final stored title: '{final_ep_title}'")
    else:
        print(f"\nFile: {f} -> FAILED TO PARSE")
