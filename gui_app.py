import os
import sys
import time
import threading
from collections import deque
import subprocess
import webbrowser
import urllib.request
import contextlib
import shutil

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except Exception:
    tk = None
    ttk = None
    messagebox = None

# Optional tray support via pystray + pillow
try:
    import pystray
    from PIL import Image
except Exception:
    pystray = None
    Image = None


def _default_port() -> int:
    p = os.getenv("ARCTIC_PORT") or os.getenv("PORT")
    try:
        return int(p) if p else 8085
    except Exception:
        return 8085


def _server_url() -> str:
    return f"http://127.0.0.1:{_default_port()}"


def _resource_path(rel: str) -> str:
    # Resolve path inside PyInstaller bundle or source tree
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        base = sys._MEIPASS  # type: ignore[attr-defined]
        return os.path.join(base, rel)
    return os.path.join(os.path.dirname(__file__), rel)


class ServerManager:
    def __init__(self) -> None:
        self.proc: subprocess.Popen | None = None
        self.lock = threading.Lock()
        self._log_buf: deque[str] = deque(maxlen=5000)
        self._log_thread: threading.Thread | None = None

    def is_running(self) -> bool:
        with self.lock:
            if self.proc is not None and self.proc.poll() is None:
                return True
        # If process not tracked, try health endpoint
        try:
            with urllib.request.urlopen(_server_url() + "/health", timeout=0.5) as r:
                return r.status == 200
        except Exception:
            return False

    def start(self) -> None:
        with self.lock:
            if self.proc is not None and self.proc.poll() is None:
                return
            # Prefer packaged server EXE if present
            exe_name = "ArcticMedia.exe"
            cmd: list[str]
            env = os.environ.copy()

            if getattr(sys, "frozen", False):
                # Single-binary mode: run this same EXE with a --server flag
                cmd = [sys.executable, "--server"]
            else:
                # Dev mode: use installed python to run run_server.py
                py = sys.executable or "python"
                cmd = [py, os.path.join(os.path.dirname(__file__), "run_server.py")]
            # Inherit environment; allow overriding PORT
            env.setdefault("PORT", str(_default_port()))
            # Hide console window on Windows; no console on other OS
            creationflags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
            try:
                self.proc = subprocess.Popen(
                    cmd,
                    env=env,
                    creationflags=creationflags,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=True,
                )
                # start log reader
                if self.proc.stdout:
                    self._start_log_reader(self.proc.stdout)
            except Exception:
                # Last resort: no special flags
                self.proc = subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    bufsize=1,
                    universal_newlines=True,
                )
                if self.proc.stdout:
                    self._start_log_reader(self.proc.stdout)

    def stop(self) -> None:
        with self.lock:
            if self.proc and self.proc.poll() is None:
                try:
                    if os.name == "nt":
                        self.proc.terminate()
                        # Give it a moment, then kill if needed
                        try:
                            self.proc.wait(timeout=3)
                        except Exception:
                            self.proc.kill()
                    else:
                        self.proc.terminate()
                except Exception:
                    pass
            self.proc = None

    def _start_log_reader(self, stream) -> None:
        def _reader():
            try:
                for line in stream:
                    self._log_buf.append(line.rstrip("\n"))
            except Exception:
                pass
        self._log_thread = threading.Thread(target=_reader, daemon=True)
        self._log_thread.start()

    def get_logs(self) -> list[str]:
        with self.lock:
            return list(self._log_buf)


class App:
    def __init__(self) -> None:
        if tk is None:
            raise RuntimeError("Tkinter not available")
        self.manager = ServerManager()
        self.root = tk.Tk()
        self.root.title("Arctic Media Server")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        try:
            self.root.iconbitmap(_resource_path("app/static/img/logo-mark-icecap-cutout.ico"))
        except Exception:
            pass

        # Apply dark theme
        self._apply_dark_theme()
        self._build_ui()
        self._tray_icon = None
        self._status_updater()
        # Check for FFmpeg on first run
        self._ensure_ffmpeg()

    def _build_ui(self) -> None:
        frm = ttk.Frame(self.root, padding=12)
        frm.grid(column=0, row=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Status: Stopped")
        ttk.Label(frm, textvariable=self.status_var).grid(column=0, row=0, columnspan=3, sticky="w")

        ttk.Button(frm, text="Start Server", command=self._start).grid(column=0, row=1, padx=4, pady=8, sticky="ew")
        ttk.Button(frm, text="Stop Server", command=self._stop).grid(column=1, row=1, padx=4, pady=8, sticky="ew")
        ttk.Button(frm, text="Open Web UI", command=self._open_ui).grid(column=2, row=1, padx=4, pady=8, sticky="ew")

        ttk.Separator(frm, orient="horizontal").grid(column=0, row=2, columnspan=3, sticky="ew", pady=(4, 8))
        ttk.Button(frm, text="Scan All (scan + refresh)", command=self._scan_all).grid(column=0, row=3, columnspan=2, padx=4, pady=4, sticky="ew")
        ttk.Button(frm, text="Show Logs", command=self._show_logs).grid(column=2, row=3, padx=4, pady=4, sticky="ew")

        ttk.Label(frm, text=f"Listening on: {_server_url()}").grid(column=0, row=4, columnspan=3, sticky="w", pady=(8, 0))

        for i in range(3):
            frm.columnconfigure(i, weight=1)

    def _apply_dark_theme(self) -> None:
        try:
            bg = "#0a0a0a"
            panel = "#262626"
            fg = "#f0f0f0"
            acc = "#7fb0ff"
            self.root.configure(bg=bg)
            style = ttk.Style(self.root)
            # Force a theme that respects background colors (clam works cross-platform)
            try:
                style.theme_use("clam")
            except Exception:
                try:
                    style.theme_use(style.theme_use())
                except Exception:
                    pass
            # General widgets
            style.configure("TFrame", background=bg)
            style.configure("TLabel", background=bg, foreground=fg)
            style.configure("TSeparator", background=panel)
            # Buttons with #262626 background and light text
            style.configure("TButton",
                            background=panel,
                            foreground=fg,
                            borderwidth=0,
                            focusthickness=0,
                            padding=6)
            style.map("TButton",
                      background=[("disabled", panel), ("active", "#333333"), ("pressed", "#1f1f1f")],
                      foreground=[("disabled", "#9a9a9a")])
            # Entries (if any)
            style.configure("TEntry", fieldbackground=panel, foreground=fg, insertcolor=fg)
            # Notebook/Tabbed (future-proof)
            style.configure("TNotebook", background=bg)
            style.configure("TNotebook.Tab", background=panel, foreground=fg)
        except Exception:
            pass

    def _start(self) -> None:
        try:
            self.manager.start()
            time.sleep(0.3)
            self._maybe_first_run_tip()
        except Exception as e:
            if messagebox:
                messagebox.showerror("Error", f"Failed to start server: {e}")

    def _stop(self) -> None:
        try:
            self.manager.stop()
        except Exception as e:
            if messagebox:
                messagebox.showerror("Error", f"Failed to stop server: {e}")

    def _open_ui(self) -> None:
        webbrowser.open(_server_url())

    def _scan_all(self) -> None:
        def _worker():
            try:
                url = _server_url() + "/libraries/scan_all?background=true&refresh_metadata=true"
                req = urllib.request.Request(url, method="POST")
                with urllib.request.urlopen(req, timeout=10) as r:
                    if r.status != 200:
                        raise RuntimeError(f"HTTP {r.status}")
                if messagebox:
                    self.root.after(0, lambda: messagebox.showinfo("Scan All", "Scan jobs queued."))
            except Exception as e:
                if messagebox:
                    self.root.after(0, lambda: messagebox.showerror("Scan All", f"Failed to queue scans: {e}"))
        threading.Thread(target=_worker, daemon=True).start()

    def _status_updater(self) -> None:
        txt = "Status: Running" if self.manager.is_running() else "Status: Stopped"
        self.status_var.set(txt)
        self.root.after(1000, self._status_updater)

    def _logs_window(self):
        win = tk.Toplevel(self.root)
        win.title("Arctic Media • Server Logs")
        win.geometry("900x500")
        # Dark styling
        bg = "#0a0a0a"
        panel = "#262626"
        fg = "#f0f0f0"
        win.configure(bg=bg)
        txt = tk.Text(win, wrap="none", bg=bg, fg=fg, insertbackground=fg, relief="flat")
        txt.pack(fill="both", expand=True)
        btns = ttk.Frame(win)
        btns.pack(fill="x")
        def _copy():
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(txt.get("1.0", "end-1c"))
            except Exception:
                pass
        def _clear():
            txt.delete("1.0", "end")
        ttk.Button(btns, text="Copy", command=_copy).pack(side="left")
        ttk.Button(btns, text="Clear", command=_clear).pack(side="left")

        def _tick():
            lines = self.manager.get_logs()
            content = "\n".join(lines[-5000:])
            txt.delete("1.0", "end")
            txt.insert("end", content)
            txt.see("end")
            if win.winfo_exists():
                win.after(1000, _tick)
        _tick()

    def _show_logs(self) -> None:
        try:
            self._logs_window()
        except Exception:
            pass

    def _ensure_ffmpeg(self) -> None:
        """Check for FFmpeg and download if missing (Windows only)."""
        if os.name != "nt":
            return
        try:
            appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
            ffmpeg_dir = os.path.join(appdata, "ArcticMedia", "ffmpeg")
            ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
            ffprobe_exe = os.path.join(ffmpeg_dir, "ffprobe.exe")
            
            if os.path.exists(ffmpeg_exe) and os.path.exists(ffprobe_exe):
                return  # Already have FFmpeg
            
            # Check if download marker exists (prevents repeated prompts)
            marker = os.path.join(ffmpeg_dir, ".download_attempted")
            if os.path.exists(marker):
                return  # Already attempted download
            
            # Ask user if they want to download FFmpeg
            if messagebox:
                result = messagebox.askyesno(
                    "FFmpeg Required",
                    "FFmpeg is required for media playback.\n\n"
                    "Would you like to download it automatically?\n\n"
                    "If you already have FFmpeg installed, you can skip this.",
                    icon="question"
                )
                if not result:
                    os.makedirs(ffmpeg_dir, exist_ok=True)
                    with open(marker, "w") as f:
                        f.write("skipped")
                    return
            
            # Download FFmpeg
            self._download_ffmpeg(ffmpeg_dir)
        except Exception:
            pass  # Silently fail - user can install FFmpeg manually
    
    def _download_ffmpeg(self, target_dir: str) -> None:
        """Download FFmpeg essentials ZIP and extract to target_dir."""
        import zipfile
        import tempfile
        
        try:
            os.makedirs(target_dir, exist_ok=True)
            
            # FFmpeg essentials download URL (using GitHub releases)
            # Using a known-good FFmpeg essentials build for Windows
            url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            
            if messagebox:
                messagebox.showinfo(
                    "Downloading FFmpeg",
                    "Downloading FFmpeg essentials...\n\n"
                    "This may take a few minutes.\n"
                    "The window may appear frozen during download."
                )
            
            # Download ZIP
            zip_path = os.path.join(tempfile.gettempdir(), "ffmpeg_essentials.zip")
            urllib.request.urlretrieve(url, zip_path)
            
            # Extract ffmpeg.exe and ffprobe.exe
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # Find ffmpeg.exe and ffprobe.exe in the ZIP
                for name in zip_ref.namelist():
                    if name.endswith("ffmpeg.exe"):
                        zip_ref.extract(name, tempfile.gettempdir())
                        extracted = os.path.join(tempfile.gettempdir(), name)
                        shutil.move(extracted, os.path.join(target_dir, "ffmpeg.exe"))
                    elif name.endswith("ffprobe.exe"):
                        zip_ref.extract(name, tempfile.gettempdir())
                        extracted = os.path.join(tempfile.gettempdir(), name)
                        shutil.move(extracted, os.path.join(target_dir, "ffprobe.exe"))
            
            # Clean up
            with contextlib.suppress(Exception):
                os.remove(zip_path)
            
            # Create marker
            marker = os.path.join(target_dir, ".download_attempted")
            with open(marker, "w") as f:
                f.write("downloaded")
            
            if messagebox:
                messagebox.showinfo("Success", "FFmpeg downloaded successfully!")
        except Exception as e:
            if messagebox:
                messagebox.showerror(
                    "Download Failed",
                    f"Failed to download FFmpeg:\n{str(e)}\n\n"
                    "Please install FFmpeg manually from:\n"
                    "https://ffmpeg.org/download.html"
                )
            # Create marker to prevent repeated prompts
            try:
                marker = os.path.join(target_dir, ".download_attempted")
                with open(marker, "w") as f:
                    f.write("failed")
            except Exception:
                pass

    def _maybe_first_run_tip(self) -> None:
        try:
            # Marker file in APPDATA
            appdata = os.environ.get("APPDATA") or os.path.expanduser("~")
            marker_dir = os.path.join(appdata, "ArcticMedia")
            marker = os.path.join(marker_dir, "first_run_done")
            if not os.path.exists(marker):
                if messagebox:
                    messagebox.showinfo(
                        "Welcome",
                        f"First-time setup: open {_server_url()}/register to create your admin account.",
                    )
                try:
                    os.makedirs(marker_dir, exist_ok=True)
                    with open(marker, "w", encoding="utf-8") as f:
                        f.write("ok")
                except Exception:
                    pass
        except Exception:
            pass

    def on_close(self) -> None:
        # Minimize to tray if possible
        if pystray and Image:
            try:
                self._show_tray_icon()
                self.root.withdraw()
                return
            except Exception:
                pass
        self.root.destroy()

    def _tray_image(self):
        try:
            ico_path = _resource_path("app/static/img/logo-mark-icecap-cutout.ico")
            return Image.open(ico_path)
        except Exception:
            # Fallback: create a small blank image
            from PIL import Image as _Image
            return _Image.new("RGB", (64, 64), color=(40, 120, 200))

    def _show_tray_icon(self) -> None:
        if not (pystray and Image):
            return
        if self._tray_icon:
            return

        def _restore(icon, _item=None):
            self.root.after(0, self._restore_from_tray)

        def _exit(icon, _item=None):
            try:
                icon.visible = False
                icon.stop()
            except Exception:
                pass
            self._tray_icon = None
            self.root.after(0, self.root.destroy)

        def _start(icon, _item=None):
            self.manager.start()

        def _stop(icon, _item=None):
            self.manager.stop()

        def _open(icon, _item=None):
            self._open_ui()

        def _scan(icon, _item=None):
            self._scan_all()

        def _logs(icon, _item=None):
            self.root.after(0, self._show_logs)

        menu = pystray.Menu(
            pystray.MenuItem("Open", _restore),
            pystray.MenuItem("Open Web UI", _open),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start Server", _start),
            pystray.MenuItem("Stop Server", _stop),
            pystray.MenuItem("Scan All", _scan),
            pystray.MenuItem("Show Logs", _logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", _exit),
        )
        icon = pystray.Icon("ArcticMedia", self._tray_image(), "Arctic Media Server", menu)
        self._tray_icon = icon
        threading.Thread(target=icon.run, daemon=True).start()

    def _restore_from_tray(self) -> None:
        try:
            if self._tray_icon:
                self._tray_icon.visible = False
                self._tray_icon.stop()
        except Exception:
            pass
        self._tray_icon = None
        try:
            self.root.deiconify()
        except Exception:
            pass

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    # Single-binary dispatcher: '--server' starts the server, otherwise start GUI
    if any(arg == "--server" for arg in sys.argv[1:]):
        # Start server directly via uvicorn to avoid run_server import issues in single-EXE mode
        try:
            import uvicorn  # type: ignore
            from app.main import app  # type: ignore
            host = os.getenv("HOST", "0.0.0.0")
            port = int(os.getenv("PORT", "8085"))
            uvicorn.run(app, host=host, port=port, log_level="info", proxy_headers=True, forwarded_allow_ips="*", timeout_keep_alive=20)
        except Exception as e:
            import traceback
            sys.stderr.write("Failed to start server: " + str(e) + "\n" + traceback.format_exc())
        
        return
    app = App()
    app.run()


if __name__ == "__main__":
    main()


