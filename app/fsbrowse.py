from __future__ import annotations

import os
import ctypes
from string import ascii_uppercase
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .auth import require_admin
from .config import settings  # only used for optional FS_BROWSE_ROOTS extras

router = APIRouter(prefix="/fs", tags=["filesystem"])

# ---------------- Models ----------------
class FsEntry(BaseModel):
    name: str
    path: str
    type: Literal["dir", "file"]
    is_hidden: bool = False

# ---------------- Windows helpers ----------------
if os.name == "nt":
    GetLogicalDrives = ctypes.windll.kernel32.GetLogicalDrives
    GetDriveTypeW = ctypes.windll.kernel32.GetDriveTypeW
    GetFileAttributesW = ctypes.windll.kernel32.GetFileAttributesW

    INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF
    FILE_ATTRIBUTE_HIDDEN = 0x2
    FILE_ATTRIBUTE_SYSTEM = 0x4

    DRIVE_REMOVABLE = 2
    DRIVE_FIXED = 3
    DRIVE_REMOTE = 4
    DRIVE_CDROM = 5
    DRIVE_RAMDISK = 6
    _VALID_TYPES = {DRIVE_FIXED, DRIVE_REMOVABLE, DRIVE_REMOTE, DRIVE_CDROM, DRIVE_RAMDISK}

def _letters_c_to_z_then_a_b(letters: List[str]) -> List[str]:
    ordered = [ch for ch in letters if "C" <= ch <= "Z"] + [ch for ch in letters if ch in ("A", "B")]
    out, seen = [], set()
    for ch in ordered:
        if ch not in seen:
            seen.add(ch); out.append(ch)
    return out

def _probe_ready(path: str) -> bool:
    try:
        with os.scandir(path):
            return True
    except OSError:
        return False

def _windows_drives() -> List[str]:
    mask = GetLogicalDrives()
    letters = [ascii_uppercase[i] for i in range(26) if mask & (1 << i)]
    roots: List[str] = []
    for letter in _letters_c_to_z_then_a_b(letters):
        root = f"{letter}:\\"
        dtype = GetDriveTypeW(ctypes.c_wchar_p(root))
        if dtype in _VALID_TYPES and _probe_ready(root):
            roots.append(root)
    return roots

# ---------------- Hidden detection ----------------
def _name_hidden(name: str) -> bool:
    return name.startswith(".") or name.startswith("$")

def _win_is_hidden(full_path: str) -> bool:
    if os.name != "nt":
        return False
    try:
        attrs = GetFileAttributesW(ctypes.c_wchar_p(full_path))
        if attrs == INVALID_FILE_ATTRIBUTES:
            return False
        return bool(attrs & (FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM))
    except Exception:
        return False

# ---------------- Roots ----------------
def _extra_roots() -> List[str]:
    # Optional extras via .env FS_BROWSE_ROOTS="D:\Media,\\NAS\Share"
    raw = (getattr(settings, "FS_BROWSE_ROOTS", "") or "")
    items = [p.strip() for p in raw.split(",") if p.strip()]
    if os.name == "nt":
        normd = []
        for r in items:
            if len(r) == 2 and r[1] == ":":
                r += "\\"
            normd.append(r)
        return normd
    return items

def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen, out = set(), []
    for x in items:
        if x not in seen:
            seen.add(x); out.append(x)
    return out

def _roots() -> List[str]:
    base = _windows_drives() if os.name == "nt" else ["/"]
    return _dedupe_keep_order(base + _extra_roots())

# ---------------- Parent ----------------
def _parent_of(p: str, roots: List[str]) -> Optional[str]:
    q = p.rstrip("\\/")
    if os.name == "nt":
        if any(q.upper() == r.rstrip("\\/").upper() for r in roots):
            return None
    else:
        if q == "/":
            return None
    parent = os.path.dirname(q)
    return None if parent == q else (parent or None)

# ---------------- Endpoints ----------------
@router.get("/roots")
async def fs_roots(_: str = Depends(require_admin)):
    roots = _roots()
    # label: use "C:" style on Windows, otherwise last segment
    items = []
    for r in roots:
        label = r
        if os.name == "nt":
            label = r[:2] if len(r) >= 2 and r[1] == ":" else r
        else:
            # strip trailing slashes for nicer labels
            label = r[:-1] if r != "/" and r.endswith("/") else r
        items.append({"path": r, "label": label})
    return items

@router.get("/list")
async def fs_list(
    path: str = Query("", description="Absolute path to list. If empty, returns first root."),
    include_files: bool = Query(False, description="Include files in the listing"),
    show_hidden: bool = Query(False, description="Show hidden/system items"),
    _: str = Depends(require_admin),
):
    roots = _roots()
    if not roots:
        raise HTTPException(400, "No roots available")

    target = path or roots[0]
    try:
        norm = os.path.abspath(target)  # preserves UNC on Windows
    except Exception:
        norm = target

    if not os.path.exists(norm):
        raise HTTPException(400, f"Path does not exist: {norm}")
    if not os.path.isdir(norm):
        raise HTTPException(400, f"Not a directory: {norm}")

    entries: List[FsEntry] = []
    try:
        with os.scandir(norm) as it:
            for e in it:
                full = os.path.join(norm, e.name)
                hidden = _name_hidden(e.name) or _win_is_hidden(full)
                if not show_hidden and hidden:
                    continue

                try:
                    if e.is_dir(follow_symlinks=False):
                        entries.append(FsEntry(name=e.name, path=full, type="dir", is_hidden=hidden))
                    elif include_files and e.is_file(follow_symlinks=False):
                        entries.append(FsEntry(name=e.name, path=full, type="file", is_hidden=hidden))
                except OSError:
                    # Inaccessible reparse point, etc.
                    continue
    except PermissionError:
        raise HTTPException(403, "Permission denied")

    # dirs first, then files, then alpha
    entries.sort(key=lambda x: (x.type != "dir", x.name.lower()))
    parent = _parent_of(norm, roots)

    return {
        "path": norm,
        "parent": parent,
        "roots": roots,
        "entries": [e.model_dump() for e in entries],
    }
