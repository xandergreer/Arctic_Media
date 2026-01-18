import sqlite3
import sys

try:
    conn = sqlite3.connect('dist/arctic.db')
    c = conn.cursor()
    row = c.execute("SELECT id FROM libraries WHERE type='tv'").fetchone()
    if row:
        print(row[0])
    else:
        print("NONE")
except Exception as e:
    print(e)
