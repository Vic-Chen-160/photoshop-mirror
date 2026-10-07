#!/usr/bin/env python3
"""List the folders under ~/.psmirror/assets and mark which are in use and which are orphans.

Each folder holds a .psmirror-source file with the original -assets path. If that path is
still a symlink pointing back here, the folder is in use — deleting it would break the
symlink and Generator would start failing again. Otherwise it is an orphan (the PSD was
moved, renamed or deleted) and is safe to remove.

Usage: clean.py            list only
       clean.py --yes      delete orphans
"""
import os, shutil, sys

HOME  = os.environ.get("PSMIRROR_HOME") or os.path.expanduser("~/.psmirror")
ROOT  = os.path.join(HOME, "assets")
APPLY = "--yes" in sys.argv
SHORT = ROOT.replace(os.path.expanduser("~"), "~")


def size(path):
    n = 0
    for r, _, fs in os.walk(path):
        for f in fs:
            try:
                n += os.path.getsize(os.path.join(r, f))
            except OSError:
                pass
    return n


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{u}" if u != "B" else f"{n}B"
        n /= 1024
    return f"{n:.1f}TB"


if not os.path.isdir(ROOT):
    print(f"  {SHORT} does not exist, nothing to clean")
    sys.exit(0)

dirs = sorted(d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d)))
if not dirs:
    print(f"  {SHORT} is empty")
    sys.exit(0)

live, orphan, unknown = [], [], []
for d in dirs:
    full = os.path.join(ROOT, d)
    src_file = os.path.join(full, ".psmirror-source")
    if not os.path.exists(src_file):
        unknown.append((d, full, None))
        continue
    src = open(src_file).read().strip()
    if os.path.islink(src) and os.path.realpath(src) == os.path.realpath(full):
        live.append((d, full, src))
    else:
        orphan.append((d, full, src))

total = 0
for label, group, mark in (("In use (keep)", live, "🔗"),
                           ("Orphans (safe to remove)", orphan, "🗑"),
                           ("Unknown (no back-pointer)", unknown, "❓")):
    if not group:
        continue
    print(f"\n{label}")
    for d, full, src in group:
        s = size(full)
        total += s
        n = len([f for f in os.listdir(full) if not f.startswith(".")])
        print(f"  {mark} {d:28} {human(s):>8}  {n} file(s)")
        if src:
            print(f"     ← {src.replace(os.path.expanduser('~'), '~')}")

print(f"\nTotal {human(total)}")

if orphan:
    if APPLY:
        for d, full, _ in orphan:
            shutil.rmtree(full)
            print(f"  Removed {d}")
    else:
        print(f"\n{len(orphan)} orphan(s) can be removed. To delete them: psmirror --clean --yes")
elif not unknown:
    print("Nothing to clean.")
