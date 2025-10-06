#!/usr/bin/env python3
"""
find_files_from_json.py

Reads filtering conditions from a JSON file and outputs a CSV of matching files.
Supports positive and inverse recency conditions:
  - accessed_within / not_accessed_within
  - modified_within / not_modified_within
  - created_within  / not_created_within
"""

import os
import csv
import json
import time
from datetime import datetime
from typing import List
from tqdm import tqdm

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # still works if path provided in JSON


# Optional: tweak these to mirror your first script’s exclusions
EXCLUDE_DIRS = set()          # e.g., {'node_modules', '.git', '__pycache__'}
EXCLUDE_EXTENSIONS = set()    # e.g., {'.txt', '.png'}


def file_size_mb(bytes_size: int) -> float:
    return bytes_size / (1024 * 1024)


def iso(ts: float) -> str:
    try:
        return datetime.fromtimestamp(ts).isoformat(timespec="seconds")
    except Exception:
        return ""


def scan_files(path: str):
    for root, dirs, files in os.walk(path):
        if EXCLUDE_DIRS:
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for name in files:
            ext = os.path.splitext(name)[1]
            if EXCLUDE_EXTENSIONS and ext in EXCLUDE_EXTENSIONS:
                continue
            full_path = os.path.join(root, name)
            # skip broken symlinks
            if os.path.islink(full_path) and not os.path.exists(full_path):
                continue
            try:
                st = os.stat(full_path, follow_symlinks=False)
            except (FileNotFoundError, PermissionError, OSError):
                continue
            yield full_path, st


def passes_conditions(full_path: str, st: os.stat_result, cfg: dict) -> bool:
    checks = []
    size_mb = file_size_mb(st.st_size)
    ext = os.path.splitext(full_path)[1].lower()
    now = time.time()

    # Size checks
    if cfg.get("min_size_mb") is not None:
        checks.append(size_mb >= cfg["min_size_mb"])
    if cfg.get("max_size_mb") is not None:
        checks.append(size_mb <= cfg["max_size_mb"])

    # Extension allowlist
    if cfg.get("ext"):
        exts = [e.lower() if e.startswith(".") else "." + e.lower() for e in cfg["ext"]]
        checks.append(ext in exts)

    # Access time (within / not within N days)
    if cfg.get("accessed_within") is not None:
        checks.append(st.st_atime >= now - cfg["accessed_within"] * 86400)
    if cfg.get("not_accessed_within") is not None:
        checks.append(st.st_atime <  now - cfg["not_accessed_within"] * 86400)

    # Modified time (within / not within N days)
    if cfg.get("modified_within") is not None:
        checks.append(st.st_mtime >= now - cfg["modified_within"] * 86400)
    if cfg.get("not_modified_within") is not None:
        checks.append(st.st_mtime <  now - cfg["not_modified_within"] * 86400)

    # Created time (within / not within N days)
    if cfg.get("created_within") is not None:
        checks.append(st.st_ctime >= now - cfg["created_within"] * 86400)
    if cfg.get("not_created_within") is not None:
        checks.append(st.st_ctime <  now - cfg["not_created_within"] * 86400)

    # Ownership checks
    owned_by = cfg.get("owned_by")
    if owned_by == "current":
        checks.append(getattr(st, "st_uid", -1) == getattr(os, "getuid", lambda: -2)())
    elif owned_by == "root":
        checks.append(getattr(st, "st_uid", -1) == 0)

    # If no conditions at all, avoid matching everything
    if not checks:
        return False

    return all(checks) if cfg.get("logic", "all") == "all" else any(checks)


def write_matches_csv(rows: List[dict], out_path: str) -> None:
    fieldnames = [
        "path",
        "extension",
        "size_mb",
        "last_accessed",
        "last_modified",
        "created",
        "owned_by_current_user",
        "owned_by_root",
    ]
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(config_file: str = "filter_conditions.json"):
    with open(config_file, "r") as f:
        cfg = json.load(f)

    load_dotenv()
    scan_path = os.getenv("SCAN_PATH")
    if not scan_path:
        raise SystemExit("No scan path provided in .env (SCAN_PATH).")
    if not os.path.isdir(scan_path):
        raise SystemExit(f"Path does not exist or is not a directory: {scan_path}")

    rows: List[dict] = []
    for full_path, st in tqdm(scan_files(scan_path), desc="Scanning"):
        if passes_conditions(full_path, st, cfg):
            rows.append(
                {
                    "path": full_path,
                    "extension": os.path.splitext(full_path)[1],
                    "size_mb": round(file_size_mb(st.st_size), 2),
                    "last_accessed": iso(st.st_atime),
                    "last_modified": iso(st.st_mtime),
                    "created": iso(st.st_ctime),
                    "owned_by_current_user": int(getattr(st, "st_uid", -1) == getattr(os, "getuid", lambda: -2)()),
                    "owned_by_root": int(getattr(st, "st_uid", -1) == 0),
                }
            )

    out_path = cfg.get("out", "filtered_files.csv")
    write_matches_csv(rows, out_path)
    print(f"Wrote {len(rows)} matching files to {out_path}")


if __name__ == "__main__":
    main()
