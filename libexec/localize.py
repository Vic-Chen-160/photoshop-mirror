#!/usr/bin/env python3
"""Detect whether an -assets folder is on a different filesystem than the temp dir;
with --apply, replace it with a symlink to a local folder.

Background: Photoshop Generator renders into TMPDIR (local disk), then os.rename()s the
file into -assets. rename(2) cannot cross devices, so with the PSD on SMB/NFS every write
fails with EXDEV. Pointing -assets at a local folder keeps the path Generator sees the
same while the files actually land on local disk.
"""
import hashlib, os, shutil, sys, tempfile

HOME  = os.environ.get("PSMIRROR_HOME") or os.path.expanduser("~/.psmirror")
APPLY = "--apply" in sys.argv
d = os.path.abspath(sys.argv[1])

if os.path.islink(d):
    sys.exit(0)                                   # already handled

try:
    same = os.stat(d).st_dev == os.stat(tempfile.gettempdir()).st_dev
except OSError:
    sys.exit(0)

if same:
    sys.exit(0)                                   # local disk, nothing to do

if not APPLY:
    print("  ⚠️  This -assets folder is on a network drive; Generator's rename() will fail (EXDEV)")
    print("      Add --local to redirect output to local disk")
    sys.exit(0)

# The path hash keeps same-named PSDs from different projects apart
tag = hashlib.sha1(d.encode()).hexdigest()[:8]
local = os.path.join(HOME, "assets", f"{os.path.basename(d)[:-7]}-{tag}")
os.makedirs(local, exist_ok=True)

# Move existing images over, then replace the folder with a symlink
for f in os.listdir(d):
    src, dst = os.path.join(d, f), os.path.join(local, f)
    if not os.path.exists(dst):
        shutil.move(src, dst)
shutil.rmtree(d)
os.symlink(local, d)
# Back-pointer so `psmirror --clean` can tell whether this folder is still in use
with open(os.path.join(local, ".psmirror-source"), "w") as fh:
    fh.write(d)
print(f"  🔗 Redirected to local disk  {d.split('/')[-1]} → {local.replace(os.path.expanduser('~'), '~')}")
