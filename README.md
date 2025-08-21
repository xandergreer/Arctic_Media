Arctic Media Server

A fast, minimal media server for your local movies & TV. No Docker or Python setup needed — just download ArcticMedia.exe, run it, and open your browser.

✨ What you get

Clean, responsive UI with hero art and posters

Movies & TV libraries (multiple per type supported)

Inline playback in the browser with resume

One-click scans of local folders

Optional TMDB enrichment for posters/backdrops/cast

Everything runs locally on your machine

🚀 Quick Start (Windows)

Download the latest ArcticMedia.exe from the Releases
 page.

Run ArcticMedia.exe.

If Windows asks about firewall access, allow Private networks so your browser can connect.

Open your browser to http://127.0.0.1:8000/
.

Follow the on-screen first-run setup:

Create your admin account.

Add a Movies and/or TV library by pointing at the folders where your media lives.

Click Scan to index your files.

(Optional) Click Refresh Metadata to pull posters/backdrops/cast from TMDB.

That’s it. Head to Movies or TV Shows in the top nav and start watching.

🧭 Using the app

Movies → grid of titles → click into a movie for a hero view and inline player.

TV → shows grid → show page lists Seasons → season page lists Episodes with inline play.

Player is collapsible/minimizable and remembers your position per file.

🔧 Requirements

Windows 10/11, 64-bit

Your video files on local drives or network shares you can read

Internet is optional; needed only for metadata/posters (TMDB)

All data stays on your machine. Streaming is local to your browser. Posters/metadata load from TMDB if you choose to enrich.

🧩 Optional: TMDB (posters & cast)

If you want rich artwork and cast lists, set a TMDB API key in Settings → Libraries → Refresh Metadata.
Without a key, the server still works — you just won’t get extra artwork automatically.

🔁 Updating

Stop the running server (close the window).

Download the new ArcticMedia.exe from Releases
.

Run it again. Your database and settings are kept locally.

❓ Troubleshooting

Can’t open 127.0.0.1:8000

Make sure the app is running (a window with logs should be open).

If something else is using port 8000, stop that program and relaunch Arctic.

Allow the app through Windows Firewall when prompted (Private networks).

No posters/backdrops

Run Refresh Metadata on the library (requires TMDB API key).

Hard refresh your browser (Ctrl+F5).

Only one episode shows up

Re-scan the TV library. The server includes a repair step that splits mis-grouped episodes based on filenames like S01E02. After scanning, reload the season page.

Multiple TV libraries

Supported. Slugs are auto-unique (tv, tv-2, tv-3, …).

🗂️ How it stores data

The app creates a local database file (e.g., arctic.db) and keeps your configuration on your machine.

No cloud services are required; nothing leaves your PC unless you choose to fetch metadata from TMDB.

🙋‍♂️ Feedback & Issues

Found a bug or have a feature request?
Open an issue on GitHub with steps to reproduce, relevant logs, and (if possible) a screenshot.

📝 License

MIT (see LICENSE in the repo).

Happy streaming! 🍿
