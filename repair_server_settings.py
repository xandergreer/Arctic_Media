"""
Repair or initialize server_settings in SQLite DBs.

Usage:
  .venv\Scripts\python.exe repair_server_settings.py [--db dist/arctic.db]

If no DB is specified, repairs both arctic.db and dist/arctic.db when present.
"""
from __future__ import annotations
import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone

DEFAULTS = {
    "server": {
        "server_host": "0.0.0.0",
        "server_port": 8085,
        "external_access": True,
        "ssl_enabled": False,
        "ssl_cert_file": "",
        "ssl_key_file": "",
    },
    "remote": {
        "enable_remote_access": False,
        "public_base_url": "",
        "port": 443,
        "upnp": True,
        "allow_insecure_fallback": "never",
    },
}


def repair_db(path: str, prefer_cert: tuple[str, str] | None = None, force_port: int | None = None) -> None:
    if not os.path.exists(path):
        print(f"SKIP {path} (not found)")
        return
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.execute(
        "CREATE TABLE IF NOT EXISTS server_settings (key TEXT PRIMARY KEY, value TEXT, updated_at TEXT)"
    )

    # Load rows into map
    cur.execute("SELECT key, value FROM server_settings")
    rows = {k: json.loads(v) if v else {} for (k, v) in cur.fetchall()}

    changed = False
    for key, defaults in DEFAULTS.items():
        data = rows.get(key, {}).copy()
        # overlay defaults for missing fields
        for dk, dv in defaults.items():
            data.setdefault(dk, dv)

        if key == "server":
            # If certificate preference provided, apply
            if prefer_cert:
                cert, pkey = prefer_cert
                if cert and pkey:
                    data["ssl_enabled"] = True
                    data["ssl_cert_file"] = cert
                    data["ssl_key_file"] = pkey
            if force_port:
                data["server_port"] = int(force_port)

        if data != rows.get(key):
            payload = json.dumps(data)
            now = datetime.now(timezone.utc).isoformat()
            cur.execute(
                "INSERT INTO server_settings(key,value,updated_at) VALUES (?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, payload, now),
            )
            rows[key] = data
            changed = True

    if changed:
        con.commit()
        print(f"REPAIRED {path}")
    else:
        print(f"OK {path} (no changes)")

    # Show
    cur.execute("SELECT key, value FROM server_settings")
    for k, v in cur.fetchall():
        print("  ", k, (v or "")[:200])
    con.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", help="Path to SQLite DB (default repairs both root and dist)")
    ap.add_argument("--cert", help="Path to fullchain PEM/CRT to set (optional)")
    ap.add_argument("--key", help="Path to private key PEM to set (optional)")
    ap.add_argument("--port", type=int, help="Force server_port to this value (optional)")
    args = ap.parse_args()

    cert_pair = (args.cert, args.key) if args.cert and args.key else None

    if args.db:
        repair_db(args.db, cert_pair, args.port)
    else:
        for db in ("arctic.db", os.path.join("dist", "arctic.db")):
            repair_db(db, cert_pair, args.port)


if __name__ == "__main__":
    main()

