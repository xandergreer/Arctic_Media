
import os
import sys
import time
import requests
import json
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from app.models import MediaItem, MediaKind
from app.config import settings

# Override DB URL for Sync
DB_DIS = "sqlite:///dist/arctic.db"
# If running in root, dist/arctic.db is clean path
if not os.path.exists("dist/arctic.db"):
    print("WARNING: dist/arctic.db not found, using ./arctic.db")
    DB_DIS = "sqlite:///arctic.db"

engine = create_engine(DB_DIS)
Session = sessionmaker(bind=engine)

API_KEY = settings.TMDB_API_KEY
if not API_KEY:
    print("ERROR: TMDB API KEY MISSING")
    sys.exit(1)

TMDB_API = "https://api.themoviedb.org/3"

def get_json(path, params={}):
    url = f"{TMDB_API}/{path}"
    p = {"api_key": API_KEY}
    p.update(params)
    try:
        r = requests.get(url, params=p, timeout=10)
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 429:
            time.sleep(1)
            return get_json(path, params)
    except Exception as e:
        print(f"Req Error: {e}")
    return None

def search_tv(title):
    res = get_json("search/tv", {"query": title})
    if res and res.get("results"):
        return res["results"][0]["id"]
    return None

def get_ep_details(tmdb_id, s, e):
    return get_json(f"tv/{tmdb_id}/season/{s}/episode/{e}")

def fix():
    session = Session()
    print(f"Connected to {DB_DIS}")
    
    # Get all episodes without poster
    # We can fetch all and filter in python to be safe with NULLs
    eps = session.query(MediaItem).filter(MediaItem.kind == MediaKind.episode).all()
    print(f"Total Episodes: {len(eps)}")
    
    needs_fix = [e for e in eps if not e.poster_url]
    print(f"Episodes missing poster: {len(needs_fix)}")
    
    fixed = 0
    
    # Cache show tmdb ids
    show_cache = {} # id -> tmdb_id
    
    for i, ep in enumerate(needs_fix):
        ej = ep.extra_json or {}
        s_num = ej.get("season")
        e_num = ej.get("episode")
        if not (s_num and e_num):
            # Try parsing from title
            import re
            m = re.search(r"S(\d+)E(\d+)", ep.title, re.IGNORECASE)
            if m:
                s_num = int(m.group(1))
                e_num = int(m.group(2))
                ej["season"] = s_num
                ej["episode"] = e_num
                # print(f"  Parsed S{s_num}E{e_num} from '{ep.title}'")
            else:
                print(f"[{i}] Skip '{ep.title}': No S/E number in extra_json or title")
                continue
            
        # Hierarchy
        # Parent -> Season
        season = session.get(MediaItem, ep.parent_id)
        if not season:
            print(f"[{i}] Skip '{ep.title}': Orphaned (No Season {ep.parent_id})")
            continue
        
        # Parent -> Show
        show = session.get(MediaItem, season.parent_id)
        if not show:
            print(f"[{i}] Skip '{ep.title}': Orphaned (No Show {season.parent_id})")
            continue
        
        show_tmdb = show_cache.get(show.id)
        if show_tmdb == -1:
             # Already failed search
             continue

        if not show_tmdb:
            sej = show.extra_json or {}
            show_tmdb = sej.get("tmdb_id")
            
            if not show_tmdb:
                # Search
                print(f"Searching TMDB for Show: '{show.title}'")
                found = search_tv(show.title)
                if found:
                    print(f"  Found: {found}")
                    sej["tmdb_id"] = found
                    show.extra_json = sej
                    # show_tmdb = found # Don't update local var yet, let next loop handle or update now
                    show_cache[show.id] = found
                    session.add(show) # Update show
                    session.commit()
                    show_tmdb = found
                else:
                    print(f"  NOT FOUND: '{show.title}'")
                    show_cache[show.id] = -1 # mark fail
                    continue
            else:
                 show_cache[show.id] = show_tmdb
        
        # Enrich Episode
        # print(f"Enriching S{s_num}E{e_num} (Show {show_tmdb})")
        data = get_ep_details(show_tmdb, s_num, e_num)
        if data:
            still = data.get("still_path")
            if still:
                url = f"https://image.tmdb.org/t/p/w500{still}"
                ep.poster_url = url
                ej["still"] = url # also update extra json for consistency
                # print(f"  Fixed: {url}")
                fixed += 1
            
            # update other meta
            if data.get("name"): ep.title = data.get("name")
            if data.get("overview"): ep.overview = data.get("overview")
            
            ep.extra_json = ej
            session.add(ep)
            
        if i % 10 == 0:
            print(f"Progress: {i}/{len(needs_fix)} Fixed: {fixed}")
            session.commit()
            
    session.commit()
    print(f"Done. Fixed {fixed} episodes.")

if __name__ == "__main__":
    fix()
