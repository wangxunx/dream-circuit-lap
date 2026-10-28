"""Stitch the selected onboard shots into one lap video with sector titles, a minimap, an intro and an outro.

    python scripts/stitch_lap.py                # storyboards/lap_7shots.json; every shot must exist
    python scripts/stitch_lap.py --placeholder  # stand-ins for missing shots, to preview timing and overlays
    python scripts/stitch_lap.py --en           # English titles, saved with an _en suffix
    python scripts/stitch_lap.py --no-minimap   # no minimap in the lower right corner, saved with a _nomap suffix
    python scripts/stitch_lap.py --shots lap_8shots.json        # the chapter 7 storyboard
    python scripts/stitch_lap.py --comfyui /path/to/ComfyUI     # default $COMFYUI_DIR or the parent directory

Shot lookup, under the ComfyUI directory: the shot's "clip", else output/video/<name>/selected/shot_0X.mp4,
else the newest output/video/<name>/shot_0X_*.mp4, where <name> is the storyboard's "name".
Placeholder keyframes come from <ComfyUI>/input, else examples/keyframes.
The minimap and its per-shot path come from the storyboard's "minimap" and "track_path" files in assets/.
The film is written to output/<output>.mp4 in this course, from the storyboard's "output".

Adapted from f1_circuit (https://github.com/wangxunx/f1_circuit, commit 42b74ae) scripts/stitch_lap.py.
"""
import glob
import json
import math
import os
import sys

import av
import numpy as np
from PIL import Image, ImageDraw

import common
from common import font

ROOT = common.COMFYUI
SHOTS_FILE = sys.argv[sys.argv.index("--shots") + 1] if "--shots" in sys.argv else "lap_7shots.json"
SB = json.load(open(os.path.join(common.STORYBOARDS, SHOTS_FILE), encoding="utf-8"))
KEYFRAMES = {k["id"]: k for k in SB["keyframes"]}
N = SB["name"]
TRACK = json.load(open(os.path.join(common.ASSETS, SB["track_path"]), encoding="utf-8"))
MINIMAP = Image.open(os.path.join(common.ASSETS, SB["minimap"])).convert("RGB")
PLACEHOLDER = "--placeholder" in sys.argv[1:]
EN = "--en" in sys.argv[1:]
SHOW_MINIMAP = "--no-minimap" not in sys.argv[1:]
OUT = os.path.join(common.OUTPUT, SB["output"] + ("_en" if EN else "") + ("" if SHOW_MINIMAP else "_nomap") + ".mp4")
XF = SB["edit"]["crossfade"]


def tr(zh, en):
    return en if EN else zh


def field(obj, key):
    return obj[key + "_en"] if EN else obj[key]


def find_clip(shot):
    if "clip" in shot:
        path = os.path.join(ROOT, shot["clip"])
        return path if os.path.exists(path) else None
    selected = os.path.join(ROOT, "output", "video", N, "selected", f"shot_{shot['id']:02d}.mp4")
    if os.path.exists(selected):
        return selected
    takes = glob.glob(os.path.join(ROOT, "output", "video", N, f"shot_{shot['id']:02d}_*.mp4"))
    return max(takes, key=os.path.getmtime) if takes else None


def probe(path):
    with av.open(path) as c:
        st = c.streams.video[0]
        dur = float(st.duration * st.time_base) if st.duration else c.duration / av.time_base
        return st.codec_context.width, st.codec_context.height, float(st.average_rate), dur


CLIPS = {s["id"]: find_clip(s) for s in SB["shots"]}
missing = [i for i, p in CLIPS.items() if p is None]
if missing and not PLACEHOLDER:
    sys.exit(f"missing shots {missing}; generate them or rerun with --placeholder")
real = [p for p in CLIPS.values() if p]
if real:
    w, h, FPS, _ = probe(real[0])
    W, H, FPS = w // 2 * 2, h // 2 * 2, round(FPS)
else:
    W, H, FPS = 1366, 768, 24
U = H / 768

if len(TRACK["sectors"]) != len(SB["shots"]):
    sys.exit(f"{SB['track_path']} has {len(TRACK['sectors'])} segments for {len(SB['shots'])} shots; "
             "the minimap path needs one segment per shot")

# --- timeline: intro, the shots, outro; neighbours overlap by XF and crossfade ---
segments = [{"kind": "intro", "dur": SB["edit"]["intro_seconds"]}]
for s in SB["shots"]:
    path = CLIPS[s["id"]]
    # H3 returns clips a little longer than requested and only reaches the last keyframe in that tail
    dur = probe(path)[3] if path else s["duration"]
    segments.append({"kind": "shot", "shot": s, "path": path, "dur": dur})
segments.append({"kind": "outro", "dur": SB["edit"]["outro_seconds"]})
t = 0.0
for seg in segments:
    seg["start"] = t
    t += seg["dur"] - XF
TOTAL = segments[-1]["start"] + segments[-1]["dur"]


def audio_rate(path):
    with av.open(path) as c:
        return c.streams.audio[0].rate if c.streams.audio else None


AUDIO_RATE = next((r for r in map(audio_rate, real) if r), None)
AUDIO_CHUNK = 1024


def clip_audio(path):
    """Clip audio as float32 (2, samples) at AUDIO_RATE, or None when the clip has no audio track."""
    with av.open(path) as c:
        if not c.streams.audio:
            return None
        rs = av.AudioResampler(format="fltp", layout="stereo", rate=AUDIO_RATE)
        chunks = [r.to_ndarray() for f in c.decode(audio=0) for r in rs.resample(f)]
        chunks += [r.to_ndarray() for r in rs.resample(None)]
    return np.concatenate(chunks, axis=1)


def mix_audio():
    """Shot audio laid on the video timeline with equal-power fades across each crossfade; intro and outro stay silent."""
    mix = np.zeros((2, int(TOTAL * AUDIO_RATE) + 1), np.float32)
    nf = int(XF * AUDIO_RATE)
    ramp = np.sin(np.linspace(0, np.pi / 2, nf, dtype=np.float32))
    for seg in segments:
        if seg["kind"] != "shot" or not seg["path"]:
            continue
        a = clip_audio(seg["path"])
        if a is None:
            continue
        a = a[:, :int(seg["dur"] * AUDIO_RATE)]
        a[:, :nf] *= ramp
        a[:, -nf:] *= ramp[::-1]
        start = int(seg["start"] * AUDIO_RATE)
        mix[:, start:start + a.shape[1]] += a
    return mix

# --- minimap overlay geometry ---
MM_W = int(330 * U)
MM_K = MM_W / TRACK["size"][0]
MM_H = int(TRACK["size"][1] * MM_K)
_maps = {}
SECTOR_PTS = [[(x * MM_K, y * MM_K) for x, y in sec["points"]] for sec in TRACK["sectors"]]


def sector_clock(sec):
    """Fraction of the sector's driving time elapsed at each point: distance between points over their mean speed."""
    pts, kmh = sec["points"], sec["kmh"]
    dt = [math.dist(a, b) / (va + vb) for a, b, va, vb in zip(pts, pts[1:], kmh, kmh[1:])]
    t = np.concatenate([[0.0], np.cumsum(dt)])
    return t / t[-1]


SECTOR_T = [sector_clock(sec) for sec in TRACK["sectors"]]


def trail(sector, p):
    """Minimap points driven so far: every sector before `sector`, then the part of it driven in time fraction p."""
    pts = [pt for sec in SECTOR_PTS[:sector] for pt in sec]
    cur, t = SECTOR_PTS[sector], SECTOR_T[sector]
    i = min(int(np.searchsorted(t, p, side="right")) - 1, len(cur) - 1)
    pts += cur[:i + 1]
    if i + 1 < len(cur):
        (x0, y0), (x1, y1) = cur[i], cur[i + 1]
        f = (p - t[i]) / (t[i + 1] - t[i])
        pts.append((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f))
    return pts


def draw_map(canvas, box, pts, dot=None, pulse=0.0):
    """Paste a minimap scaled into box (x, y, w) and draw the trail and the car dot on top."""
    x0, y0, bw = box
    k = bw / MM_W
    if bw not in _maps:
        _maps[bw] = MINIMAP.resize((bw, round(MM_H * k)), Image.LANCZOS)
    img = _maps[bw]
    canvas.paste(img, (x0, y0))
    d = ImageDraw.Draw(canvas)
    d.rectangle((x0 - 1, y0 - 1, x0 + img.width, y0 + img.height), outline=(255, 255, 255), width=max(1, int(2 * U)))
    scaled = [(x0 + x * k, y0 + y * k) for x, y in pts]
    if len(scaled) > 1:
        d.line(scaled, fill=(255, 212, 0), width=max(2, int(4 * U * k)), joint="curve")
    if dot:
        cx, cy = x0 + dot[0] * k, y0 + dot[1] * k
        if pulse:
            rr = (8 + 14 * pulse) * U * k
            d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(255, 60, 40), width=max(1, int(3 * U)))
        r = 7 * U * k
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(230, 30, 30), outline=(255, 255, 255), width=max(1, int(2 * U)))


def card_background():
    y = np.linspace(0, 1, H)[:, None, None]
    top, bottom = np.array([18, 34, 28]), np.array([6, 12, 10])
    return Image.fromarray(np.broadcast_to(top + (bottom - top) * y, (H, W, 3)).astype(np.uint8))


CARD = card_background()


def centered(d, y, text, f, fill):
    d.text(((W - d.textlength(text, font=f)) / 2, y), text, font=f, fill=fill)


def map_card(title, subtitle, pts, dot, pulse):
    img = CARD.copy()
    d = ImageDraw.Draw(img)
    centered(d, 40 * U, title, font(int(46 * U), True), (255, 255, 255))
    centered(d, 104 * U, subtitle, font(int(24 * U)), (200, 215, 205))
    bw = int(min(W * 0.62, (H - 190 * U) * TRACK["size"][0] / TRACK["size"][1]))
    draw_map(img, ((W - bw) // 2, int(160 * U), bw), pts, dot, pulse)
    return img


SUMMARY = tr(f"约 {TRACK['lap_km']} km · {TRACK['turns']} 个弯 · 逆时针", f"About {TRACK['lap_km']} km · {TRACK['turns']} turns · Counter-clockwise")
START = SECTOR_PTS[0][0]


def intro_frame(tau):
    return map_card(field(SB, "title"), SUMMARY + tr(" · 车载视角从起终点线出发", " · Onboard from the start/finish line"), [], START, (tau * 1.2) % 1.0)


def outro_frame(tau):
    pts = [pt for sec in SECTOR_PTS for pt in sec]
    return map_card(tr("完成一圈", "Lap complete"), SUMMARY, pts, START, 0.0)


class Clip:
    """Decodes forward only; the timeline asks for monotonically increasing times."""

    def __init__(self, path):
        self.container = av.open(path)
        self.fps = float(self.container.streams.video[0].average_rate)
        self.frames = self.container.decode(video=0)
        self.index = -1
        self.image = None

    def frame(self, tau):
        while self.index < int(tau * self.fps):
            f = next(self.frames, None)
            if f is None:
                break
            self.index += 1
            self.image = f.to_image().convert("RGB").resize((W, H), Image.LANCZOS)
        return self.image

    def close(self):
        self.container.close()


def keyframe(kid):
    name = KEYFRAMES[kid].get("file", f"{N}_{kid}.png")
    path = next((p for p in (os.path.join(ROOT, "input", name), os.path.join(common.EXAMPLE_KEYFRAMES, name)) if os.path.exists(p)), None)
    return Image.open(path).convert("RGB").resize((W, H), Image.LANCZOS) if path else None


class Placeholder:
    """Stand-in for a shot that has not been generated: a slow push-in from the first keyframe to the last
    (or on whichever of the two exists), or a plain card."""

    def __init__(self, seg):
        s = seg["shot"]
        self.dur = seg["dur"]
        self.first, self.last = keyframe(s["first"]), keyframe(s["last"])
        self.color = s["color"]
        self.text = tr(f"占位：镜头 {s['id']} 尚未生成", f"Placeholder: shot {s['id']} not generated yet")

    def frame(self, tau):
        p = tau / self.dur
        if self.first or self.last:
            z = 1 + 0.15 * p
            src = Image.blend(self.first, self.last, p) if self.first and self.last else self.first or self.last
            cw, ch = W / z, H / z
            img = src.crop((int((W - cw) / 2), int((H - ch) / 2), int((W + cw) / 2), int((H + ch) / 2))).resize((W, H), Image.BILINEAR)
        else:
            img = Image.new("RGB", (W, H), self.color)
            d = ImageDraw.Draw(img)
            for i in range(12):
                y = H * 0.55 + (H * 0.45) * ((i / 12 + p * 3) % 1) ** 2
                d.line((W / 2 - (y - H * 0.55) * 1.6, y, W / 2 + (y - H * 0.55) * 1.6, y), fill=(255, 255, 255), width=1)
        d = ImageDraw.Draw(img)
        d.text((24 * U, 20 * U), self.text, font=font(int(22 * U), True), fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
        return img

    def close(self):
        pass


def segment_frame(seg, tau, cache):
    if seg["kind"] == "intro":
        return intro_frame(tau)
    if seg["kind"] == "outro":
        return outro_frame(tau)
    key = seg["shot"]["id"]
    if key not in cache:
        cache[key] = Clip(seg["path"]) if seg["path"] else Placeholder(seg)
    return cache[key].frame(tau)


def overlay(img, t):
    """Sector title (lower left) and, unless --no-minimap, the minimap with the moving car (lower right) for the shot playing at time t."""
    shots = [i for i, seg in enumerate(segments) if seg["kind"] == "shot"]
    cur = next((i for i in reversed(shots) if segments[i]["start"] <= t), None)
    if cur is None or t >= segments[-1]["start"] + XF:
        return img
    seg = segments[cur]
    tau = t - seg["start"]
    sector = cur - 1
    alpha = min(1.0, tau / XF) if cur == shots[0] else 1.0
    if t > segments[-1]["start"]:
        alpha = 1 - (t - segments[-1]["start"]) / XF
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    m = int(24 * U)
    if SHOW_MINIMAP:
        pts = trail(sector, min(1.0, tau / (seg["dur"] - XF)))
        bx, by = W - MM_W - m, H - MM_H - m
        panel = Image.new("RGBA", (MM_W + 16, MM_H + 16), (0, 0, 0, 110))
        layer.alpha_composite(panel, (bx - 8, by - 8))
        mm = Image.new("RGB", (MM_W + 2, MM_H + 2))
        draw_map(mm, (1, 1, MM_W), pts, pts[-1])
        layer.paste(mm.convert("RGBA"), (bx - 1, by - 1))

    title_a = min(1.0, (tau - 0.3) / 0.4, (2.8 - tau) / 0.4)
    if title_a > 0:
        s = seg["shot"]
        d = ImageDraw.Draw(layer)
        f1, f2 = font(int(34 * U), True), font(int(20 * U))
        title = field(s, "title")
        lines = [field(s, "turns"), tr("海拔", "Elevation") + f" {field(s, 'elevation')}  ·  {field(s, 'speed')}"]
        tw = max(d.textlength(title, font=f1) + 64 * U, *(d.textlength(x, font=f2) for x in lines)) + 40 * U
        x0, y0 = m, H - m - 150 * U
        a = int(255 * title_a)
        d.rounded_rectangle((x0, y0, x0 + tw, H - m), radius=int(10 * U), fill=(0, 0, 0, int(150 * title_a)))
        d.rounded_rectangle((x0 + 16 * U, y0 + 18 * U, x0 + 62 * U, y0 + 64 * U), radius=int(8 * U), fill=s["color"] + f"{a:02x}")
        d.text((x0 + 39 * U, y0 + 41 * U), str(s["id"]), font=font(int(28 * U), True), fill=(255, 255, 255, a), anchor="mm")
        d.text((x0 + 76 * U, y0 + 14 * U), title, font=f1, fill=(255, 255, 255, a))
        d.text((x0 + 20 * U, y0 + 78 * U), lines[0], font=f2, fill=(235, 235, 235, a))
        d.text((x0 + 20 * U, y0 + 108 * U), lines[1], font=f2, fill=(200, 200, 200, a))

    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    img = img.convert("RGBA")
    img.alpha_composite(layer)
    return img.convert("RGB")


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    n_frames = int(round(TOTAL * FPS))
    cache = {}
    with av.open(OUT, "w") as out:
        st = out.add_stream("libx264", rate=FPS)
        st.width, st.height, st.pix_fmt = W, H, "yuv420p"
        st.options = {"crf": "18"}
        audio = mix_audio() if AUDIO_RATE else None
        if audio is not None:
            ast = out.add_stream("aac", rate=AUDIO_RATE, layout="stereo")
        apos = 0

        def mux_audio(until):
            nonlocal apos
            while apos < min(until, audio.shape[1]):
                frame = av.AudioFrame.from_ndarray(np.ascontiguousarray(audio[:, apos:apos + AUDIO_CHUNK]), format="fltp", layout="stereo")
                frame.sample_rate, frame.pts = AUDIO_RATE, apos
                for packet in ast.encode(frame):
                    out.mux(packet)
                apos += AUDIO_CHUNK

        for n in range(n_frames):
            t = n / FPS
            active = [i for i, seg in enumerate(segments) if seg["start"] <= t < seg["start"] + seg["dur"]]
            for k in [k for k in cache if k not in {segments[i].get("shot", {}).get("id") for i in active}]:
                cache.pop(k).close()
            cur = active[-1]
            img = segment_frame(segments[cur], t - segments[cur]["start"], cache)
            if len(active) > 1:
                prev = active[-2]
                a = (t - segments[cur]["start"]) / XF
                img = Image.blend(segment_frame(segments[prev], t - segments[prev]["start"], cache), img, a)
            img = overlay(img, t)
            for packet in st.encode(av.VideoFrame.from_image(img)):
                out.mux(packet)
            if audio is not None:
                mux_audio(int((n + 1) / FPS * AUDIO_RATE))
        for packet in st.encode():
            out.mux(packet)
        if audio is not None:
            mux_audio(audio.shape[1])
            for packet in ast.encode():
                out.mux(packet)
    src = ", ".join(f"{i}:{'clip' if p else 'placeholder'}" for i, p in CLIPS.items())
    sound = f"audio {AUDIO_RATE} Hz" if audio is not None else "no audio"
    print(f"{OUT}: {W}x{H} @ {FPS} fps, {TOTAL:.1f} s, {sound} ({src})")


if __name__ == "__main__":
    main()
