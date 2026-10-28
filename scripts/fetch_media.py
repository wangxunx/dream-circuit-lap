"""Download the course media (historical clips) and, if no CJK font is installed, the Noto Sans SC fonts.

    python scripts/fetch_media.py            # every file in media/manifest.json, into media/
    python scripts/fetch_media.py --fonts    # also NotoSansSC-Regular/Bold.otf into fonts/, unless a CJK font is found

Files that already exist with the right sha256 are skipped, so the script is safe to rerun.
"""
import hashlib
import json
import os
import sys
import urllib.request

import common

MANIFEST = json.load(open(os.path.join(common.MEDIA, "manifest.json"), encoding="utf-8"))


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(url, path, digest):
    if os.path.isfile(path) and sha256(path) == digest:
        return
    print(f"downloading {os.path.basename(path)}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    urllib.request.urlretrieve(url, path + ".part")
    if sha256(path + ".part") != digest:
        os.remove(path + ".part")
        sys.exit(f"{url}: sha256 mismatch")
    os.replace(path + ".part", path)


for name, f in MANIFEST["files"].items():
    fetch(f"{MANIFEST['base_url']}/{name}", os.path.join(common.MEDIA, name), f["sha256"])
print(f"media ready: {len(MANIFEST['files'])} files in {common.MEDIA}")

if "--fonts" in sys.argv:
    if common.FONT_R:
        print(f"CJK font found: {common.FONT_R}")
    else:
        for name, f in MANIFEST["fonts"].items():
            fetch(f["url"], os.path.join(common.PROJECT, "fonts", name), f["sha256"])
        print("fonts ready in fonts/")
