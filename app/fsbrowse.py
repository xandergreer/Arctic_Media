# app/fsbrowse.py
from __future__ import annotations

import os
from string import ascii_uppercase
from typing import List, Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .auth import require_admin
from .config import settings

router = APIRouter(prefix="/fs", tags=["filesystem"])

# ---------- models ----------

class FsEntry(BaseModel):
    name: str
    path: str
    type: Literal["dir", "file"]
    is_hidden: bool = False

# ---------- helpers ----------

def _is_hidden(name: str) -> bool:
    # Hide dot/system-ish names; Windows $RECYCLE.BIN, etc.
    return name.startswith(".") or name.startswith("$")

def _windows_drives() -> List[str]:
    drives: List[str] = []
    for letter in ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            drives.append(root)
    return drives

def _roots() -> List[str]:
    """Base roots + optional extra roots via FS_BROWSE_ROOTS (comma-separated)."""
    extras = [r.strip() for r in (settings.FS_BROWSE_ROOTS or "").split(",") if r.strip()]
    if os.name == "nt":
        return _windows_drives() + extras
    return ["/"] + extras

# ---------- endpoints ----------

@router.get("/roots")
async def fs_roots(_: str = Depends(require_admin)):
    """
    List available starting points for browsing.
    Returns: [{ "path": "C:\\", "label": "C:\\" }, ...]
    """
    roots = _roots()
    return [{"path": r, "label": r} for r in roots]

@router.get("/list")
async def fs_list(
    path: str = Query("", description="Absolute path to list. If empty, uses first root."),
    include_files: bool = Query(False, description="Include files (default false)"),
    show_hidden: bool = Query(False, description="Include hidden entries"),
    _: str = Depends(require_admin),
):
    """
    List a directory's contents.
    Returns:
      {
        "path": "<normalized dir>",
        "parent": "<parent dir or null>",
        "roots": [ "<root1>", "<root2>", ... ],
        "entries": [
          {"name": "...", "path": "...", "type": "dir"|"file", "is_hidden": bool},
          ...
        ]
      }
    """
    roots = _roots()
    if not roots:
        raise HTTPException(status_code=400, detail="No roots available")

    # Default to the first root when path is empty
    if not path:
        path = roots[0]

    # Normalize path (preserve UNC if any)
    try:
        norm = os.path.abspath(path)
    except Exception:
        norm = path

    if not os.path.exists(norm):
        raise HTTPException(status_code=400, detail=f"Path does not exist: {norm}")
    if not os.path.isdir(norm):
        raise HTTPException(status_code=400, detail=f"Not a directory: {norm}")

    # Determine parent (drive root has no parent on Windows; "/" has none on *nix)
    parent = None
    try:
        if os.name == "nt":
            # "C:\", "D:\" style roots
            if len(norm) <= 3 and norm[1:3] == ":\\":
                parent = None
            else:
                parent_candidate = os.path.dirname(norm.rstrip("\\/"))
                parent = parent_candidate if parent_candidate and parent_candidate != norm else None
        else:
            if norm == "/":
                parent = None
            else:
                parent_candidate = os.path.dirname(norm.rstrip("/"))
                parent = parent_candidate if parent_candidate and parent_candidate != norm else None
    except Exception:
        parent = None

    # Enumerate entries
    entries: List[FsEntry] = []
    try:
        with os.scandir(norm) as it:
            for e in it:
                hidden = _is_hidden(e.name)
                if not show_hidden and hidden:
                    continue
                if e.is_dir(follow_symlinks=False):
                    entries.append(FsEntry(name=e.name, path=os.path.join(norm, e.name), type="dir", is_hidden=hidden))
                elif include_files and e.is_file(follow_symlinks=False):
                    entries.append(FsEntry(name=e.name, path=os.path.join(norm, e.name), type="file", is_hidden=hidden))
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Sort: directories first, then files, alpha by name
    entries.sort(key=lambda x: (x.type != "dir", x.name.lower()))

    return {
        "path": norm,
        "parent": parent,
        "roots": roots,
        "entries": [e.model_dump() for e in entries],
    }
