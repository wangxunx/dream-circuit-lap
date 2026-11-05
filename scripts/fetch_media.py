"""Download the bundled media (historical clips) and, if no CJK font is installed, the Noto Sans SC fonts.

    python scripts/fetch_media.py            # every file in media/manifest.json, into media/
    python scripts/fetch_media.py --fonts    # also NotoSansSC-Regular/Bold.otf into fonts/, unless a CJK font is found

Files that already exist with the right sha256 are skipped, so the script is safe to rerun.
If DREAM_CIRCUIT_MEDIA_CACHE points to a directory with copies of the media (the Docker image sets it),
copies with the right sha256 are used instead of downloading, and an older copy is used if the download fails.
"""
import hashlib
import json
import os
import shutil
import sys
import urllib.error
import urllib.request

import common

MANIFEST = json.load(open(os.path.join(common.MEDIA, "manifest.json"), encoding="utf-8"))
CACHE = os.environ.get("DREAM_CIRCUIT_MEDIA_CACHE")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(url, path, digest, cached=None):
    if os.path.isfile(path) and sha256(path) == digest:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if cached and os.path.isfile(cached) and sha256(cached) == digest:
        shutil.copyfile(cached, path)
        return
    print(f"downloading {os.path.basename(path)}")
    try:
        urllib.request.urlretrieve(url, path + ".part")
    except urllib.error.URLError as e:
        if cached and os.path.isfile(cached):
            print(f"{url}: download failed ({e}), using the older copy in {os.path.dirname(cached)}")
            shutil.copyfile(cached, path)
            return
        sys.exit(f"{url}: download failed: {e}")
    if sha256(path + ".part") != digest:
        os.remove(path + ".part")
        sys.exit(f"{url}: sha256 mismatch")
    os.replace(path + ".part", path)


for name, f in MANIFEST["files"].items():
    fetch(f"{MANIFEST['base_url']}/{name}", os.path.join(common.MEDIA, name), f["sha256"], CACHE and os.path.join(CACHE, name))
print(f"media ready: {len(MANIFEST['files'])} files in {common.MEDIA}")

if "--fonts" in sys.argv:
    if common.FONT_R:
        print(f"CJK font found: {common.FONT_R}")
    else:
        for name, f in MANIFEST["fonts"].items():
            fetch(f["url"], os.path.join(common.PROJECT, "fonts", name), f["sha256"])
        print("fonts ready in fonts/")
