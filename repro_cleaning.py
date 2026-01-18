
import re
from app.utils import _clean_show_title_enhanced, parse_tv_parts

bad_filenames = [
    # User provided examples from logs
    "Agatha.All.Along.S01E01.1080p.WEB.H264-SuccessfulCrab.mkv",
    "Agatha.All.Along.S01E02.1080p.WEB.H264-SuccessfulCrab.mkv",
    "Alien Earth S01E03 1080p DSNP WEB-DL DDP5 1 H 264-BiOMA.mkv",
    "American.Dad.S20E04.1080p.WEBRip.x264-BAE.mkv",
    "Beast Games S01E08 Betray Your Friend For S1000000 1080p AMZN WEB-DL DD 2 0 H 264-playWEB.mkv",
    "Beast.Games.S01E07.1080p.AV1.10bit-MeGusta.mkv",
    "Bobs Burgers S14E14 The Big Stieblitzki 1080p DSNP WEB-DL DDP5 1 H 264-NTb.mkv",
    "Bobs.Burgers.S14E16.1080p.WEB.H264-SuccessfulCrab.mkv",
    "Bobs.Burgers.S15E01.1080p.WEB.h264-BAE.mkv",
    "Channel.Zero.S01E01.You.Have.to.Go.Inside.1080p.AMZN.WEB-DL.DDP5.1.H.264-KiNGS.mkv",
    "Constellation.S01E04.1080p.HEVC.x265-MeGusta.mkv",
    "Futurama S09E01 The One Amigo 1080p HULU WEB-DL DDP5 1 H 264-FLUX.mkv",
    "King.Of.The.Hill.S14E01.1080p.WEB.h264-ETHEL.mkv",
    "Rick.and.Morty.S08E01.1080p.WEB.H264-LAZYCUNTS.mkv",
    "Severance (2022) S01E01 (1080p BluRay x265 SDR DDP 5.1 English - DarQ HONE).mkv", 
    "S01E01 The Burger DSNP DL 1 H 264 NTb mkv", # From detail log, constructed title?
]

print("--- Testing Cleaning Logic ---")
for f in bad_filenames:
    print(f"\nFilename: {f}")
    
    # Test full parsing
    res = parse_tv_parts("", f)
    if res:
        show, season, ep, guess = res
        print(f"  Parsed Guess: '{guess}'")
        
        # Apply enhanced cleaning to the guess (as scanner does)
        cleaned_guess = _clean_show_title_enhanced(guess) if guess else ""
        print(f"  Cleaned Guess: '{cleaned_guess}'")
        
        # Test if we can extract a better title or if it should be empty
        if cleaned_guess and cleaned_guess.lower() in [show.lower()]: 
             print("  -> MATCHES SHOW NAME (Should be empty!)")

