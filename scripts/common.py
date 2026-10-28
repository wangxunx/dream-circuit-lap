"""Project paths, the ComfyUI install the workflows run in, and the CJK font used for every label.

Adapted from f1_circuit (https://github.com/wangxunx/f1_circuit, commit 42b74ae) scripts/common.py.
"""
import os
import sys

from PIL import ImageFont

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORYBOARDS = os.path.join(PROJECT, "storyboards")
ASSETS = os.path.join(PROJECT, "assets")
WORKFLOWS = os.path.join(PROJECT, "workflows")
DOCS = os.path.join(PROJECT, "docs")
EXAMPLE_KEYFRAMES = os.path.join(PROJECT, "examples", "keyframes")
MEDIA = os.path.join(PROJECT, "media")
OUTPUT = os.path.join(PROJECT, "output")

# keyframes are read from <ComfyUI>/input and generated clips from <ComfyUI>/output/video;
# defaults to the directory this project was cloned into
COMFYUI = os.path.abspath(sys.argv[sys.argv.index("--comfyui") + 1] if "--comfyui" in sys.argv
                          else os.environ.get("COMFYUI_DIR", os.path.dirname(PROJECT)))

# (regular, bold, collection index); index 2 of Noto Sans CJK is Simplified Chinese
FONT_CANDIDATES = [
    (os.environ.get("F1_FONT_REGULAR", ""), os.environ.get("F1_FONT_BOLD", ""), int(os.environ.get("F1_FONT_INDEX", "0"))),
    (os.path.join(PROJECT, "fonts", "NotoSansSC-Regular.otf"), os.path.join(PROJECT, "fonts", "NotoSansSC-Bold.otf"), 0),
    ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 2),
    ("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc", "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc", 2),
    ("/usr/share/fonts/google-noto-sans-cjk-fonts/NotoSansCJK-Regular.ttc", "/usr/share/fonts/google-noto-sans-cjk-fonts/NotoSansCJK-Bold.ttc", 2),
    ("/System/Library/Fonts/STHeiti Light.ttc", "/System/Library/Fonts/STHeiti Medium.ttc", 0),
    ("C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/msyhbd.ttc", 0),
]
FONT_R, FONT_B, FONT_INDEX = next((c for c in FONT_CANDIDATES if os.path.isfile(c[0]) and os.path.isfile(c[1])), (None, None, 0))
_fonts = {}


def font(size, bold=False):
    if FONT_R is None:
        sys.exit("no CJK font found: run scripts/fetch_media.py --fonts, install Noto Sans CJK, "
                 "or set F1_FONT_REGULAR and F1_FONT_BOLD (and F1_FONT_INDEX for .ttc collections)")
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT_B if bold else FONT_R, size, index=FONT_INDEX)
    return _fonts[key]
