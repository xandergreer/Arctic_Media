# app/fsbrowse.py
from __future__ import annotations

import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from .auth import get_current_user
from .config import settings

router = APIRouter(prefix="/fs", tags=["fs"])

# ───────────────────────── Models ─────────────────────────

class FSNode(BaseModel):
    path: str
    name: str
    is_dir: bool
    size: Optional[int] = None

class FSListOut(BaseModel):
    path: str
    entries: List[FSNode]

# ───────────────────────── Helpers ─────────────────────────

def _split_csv(val: str) -> List[str]:
    if not val:
        return []
    return [p.strip() for p in val.replace(";", ",").split(",") if p.strip()]

def _windows_drives() -> List[str]:
    drives: List[str] = []
    for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        d = f"{c}:\\"
        if os.path.exists(d):
            drives.append(d)
    return drives

def _roots() -> List[str]:
    """
    Allowed roots based on settings.
      - If FS_BROWSE_MODE=dev_open  -> expose all drives (Windows) or '/' + HOME (POSIX)
      - Else if FS_BROWSE_ALLOW/FS_BROWSE_ROOTS set -> those paths
      - Else:  **Windows:** expose all drives (friendly default)
               **POSIX:**  expose '/' and HOME
    """
    allow_cfg = settings.FS_BROWSE_ALLOW or getattr(settings, "FS_BROWSE_ROOTS", "")

    dev_open = (settings.FS_BROWSE_MODE or "").lower() == "dev_open"
    allow_list = [_ for _ in (_split_csv(allow_cfg)) if os.path.isdir(os.path.abspath(_))]

    if dev_open or not allow_list:
        if os.name == "nt":
            roots = _windows_drives()
            if not roots:
                # fallback to current drive root
                drive = os.path.splitdrive(os.getcwd())[0] or "C:"
                roots = [f"{drive}\\"]
        else:
            roots = ["/"]
            home = os.path.expanduser("~")
            if os.path.isdir(home):
                roots.append(home)
        # if explicit allow_list exists, use it; otherwise, use the defaults above
        return allow_list or roots

    return [os.path.abspath(p) for p in allow_list]

def _norm(p: str) -> str:
    return os.path.normcase(os.path.abspath(p))

def _allowed(path: str, roots: List[str]) -> bool:
    path_nc = _norm(path)
    for r in roots:
        r_nc = _norm(r)
        try:
            common = os.path.commonpath([path_nc, r_nc])
        except Exception:
            # different drive letters on Windows
            continue
        if common == r_nc:
            return True
    return False

def _list_dir(path: str, include_files: bool, include_dirs: bool, show_hidden: bool) -> List[FSNode]:
    try:
        names = sorted(os.listdir(path), key=lambda n: n.lower())
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied")

    entries: List[FSNode] = []
    for name in names:
        if not show_hidden and name.startswith("."):
            continue
        full = os.path.join(path, name)
        try:
            is_dir = os.path.isdir(full)
            if (is_dir and not include_dirs) or ((not is_dir) and not include_files):
                continue
            size = None if is_dir else os.path.getsize(full)
            entries.append(FSNode(path=os.path.abspath(full), name=name, is_dir=is_dir, size=size))
        except OSError:
            continue
    return entries

# ───────────────────────── Routes ─────────────────────────

@router.get("/roots", response_model=List[FSNode])
async def fs_roots(user = Depends(get_current_user)):
    return [FSNode(path=r, name=r, is_dir=True) for r in _roots()]

@router.get("/ls", response_model=FSListOut)
async def fs_ls(
    path: str = Query(..., description="Absolute path under an allowed root"),
    include_files: bool = Query(True),
    include_dirs: bool = Query(True),
    show_hidden: bool = Query(False),
    user = Depends(get_current_user),
):
    roots = _roots()
    if not _allowed(path, roots):
        raise HTTPException(status_code=403, detail="Path not allowed")
    if not os.path.isdir(path):
        raise HTTPException(status_code=404, detail="Directory not found")

    entries = _list_dir(path, include_files=include_files, include_dirs=include_dirs, show_hidden=show_hidden)
    return FSListOut(path=os.path.abspath(path), entries=entries)

# Legacy endpoint kept for UI compatibility
@router.get("/list", response_model=FSListOut)
async def fs_list_legacy(
    path: str = Query(..., description="Absolute path under an allowed root"),
    include_files: bool = Query(True),
    include_dirs: bool = Query(True),
    show_hidden: bool = Query(False),
    user = Depends(get_current_user),
):
    return await fs_ls(path=path, include_files=include_files, include_dirs=include_dirs, show_hidden=show_hidden, user=user)
