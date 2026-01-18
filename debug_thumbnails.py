
import sqlite3
import json

DB_PATH = "e:/Arctic_Media/arctic.db"
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

c.execute("SELECT id, title, poster_url, extra_json FROM media_items WHERE kind='episode' ORDER BY created_at DESC LIMIT 5")
rows = c.fetchall()

print(f"Total rows found: {len(rows)}")
for r in rows:
    eid, title, poster_url, extra = r
    print(f"Title: '{title}'")
    print(f"RAW poster_url: '{poster_url}'")
    if extra:
        ej = json.loads(extra)
        print(f"JSON still: '{ej.get('still')}'")
        print(f"JSON tmdb_still_path: '{ej.get('tmdb_still_path')}'")
    print("-" * 10)

conn.close()
