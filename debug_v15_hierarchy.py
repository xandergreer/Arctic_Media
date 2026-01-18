
import sqlite3
import json
import os

# Target the PRODUCTION database
DB_PATH = "e:/Arctic_Media/dist/arctic.db"

if not os.path.exists(DB_PATH):
    print(f"ERROR: {DB_PATH} not found!")
    exit(1)

print(f"--- DIAGNOSTIC V15: HIERARCHY CHECK ({DB_PATH}) ---")

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# 1. Check Shows
print("\nChecking Shows...")
c.execute("SELECT id, title, extra_json FROM media_items WHERE kind='show'")
shows = c.fetchall()
show_map = {} # id -> {title, tmdb_id}
print(f"Found {len(shows)} shows.")
for sid, title, extra in shows:
    ej = json.loads(extra) if extra else {}
    tmdb = ej.get("tmdb_id")
    show_map[sid] = {"title": title, "tmdb_id": tmdb}
    if not tmdb:
        print(f"  [WARN] Show '{title}' (ID: {sid}) has NO TMDB ID!")
    else:
        pass
        # print(f"  Show '{title}' -> TMDB {tmdb}")

# 2. Check Seasons
print("\nChecking Seasons...")
c.execute("SELECT id, title, parent_id FROM media_items WHERE kind='season'")
seasons = c.fetchall()
season_map = {} # id -> {title, parent_id, valid_chain}
print(f"Found {len(seasons)} seasons.")
for sid, title, pid in seasons:
    parent_show = show_map.get(pid)
    valid = False
    if parent_show:
        if parent_show["tmdb_id"]:
            valid = True
        else:
            print(f"  [WARN] Season '{title}' (ID: {sid}) parent '{parent_show['title']}' has NO TMDB ID.")
    else:
        print(f"  [ERR] Season '{title}' (ID: {sid}) ORPHANED (Parent {pid} not found).")
    
    season_map[sid] = {"title": title, "parent_id": pid, "valid_chain": valid}

# 3. Check Episodes
print("\nChecking Episodes...")
c.execute("SELECT id, title, parent_id FROM media_items WHERE kind='episode'")
episodes = c.fetchall()
print(f"Found {len(episodes)} episodes.")
skipped_potential = 0
valid_chain = 0
orphaned = 0

for eid, title, pid in episodes:
    parent_season = season_map.get(pid)
    if parent_season:
        if parent_season["valid_chain"]:
            valid_chain += 1
        else:
            skipped_potential += 1
            # print(f"  [SKIP] Episode '{title}' -> Season '{parent_season['title']}' -> Invalid Show Chain")
    else:
        orphaned += 1
        print(f"  [ERR] Episode '{title}' ORPHANED (Parent {pid} not found).")

print("\n--- SUMMARY ---")
print(f"Episodes with Valid Hierarchy (Ready to Enrich): {valid_chain}")
print(f"Episodes likely to be SKIPPED (Broken Chain): {skipped_potential}")
print(f"Episodes Orphaned: {orphaned}")
print("If SKIPPED > 0, the Shows need to be enriched FIRST before episodes can be enriched.")

conn.close()
