"""Draw the storyboard maps used in chapters 3 and 7: which stretch of track each shot covers and where the keyframes sit.

    python scripts/storyboard_map.py   # writes assets/storyboard_map_{7,8}shots.png and the English _en.png versions

Shots, keyframes, titles and durations come from storyboards/lap_7shots.json and lap_8shots.json; the track
stretches come from each storyboard's "track_path" file, the same one stitch_lap.py uses for the minimap.
Rerun after changing a storyboard or a track path.
"""
import json
import math
import os

from PIL import Image, ImageDraw, ImageOps

import common

COLORS = ["#1f77b4", "#d62728", "#9467bd", "#ff7f0e", "#2ca02c", "#17becf", "#8c564b", "#e377c2"]
TOP = 110


def outward(p, q, c):
    tx, ty = q[0] - p[0], q[1] - p[1]
    n = math.hypot(tx, ty) or 1
    nx, ny = -ty / n, tx / n
    mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
    if (mx + nx - c[0]) ** 2 + (my + ny - c[1]) ** 2 < (mx - c[0]) ** 2 + (my - c[1]) ** 2:
        nx, ny = -nx, -ny
    return nx, ny


def at(points, frac):
    d = [0.0]
    for a, b in zip(points, points[1:]):
        d.append(d[-1] + math.dist(a, b))
    t = d[-1] * frac
    i = next(i for i in range(1, len(d)) if d[i] >= t)
    return points[i - 1], points[i]


def track_layer(base, segs, scale):
    """Faded minimap with the shot segments and direction arrows, scaled by `scale`."""
    img = base.resize((round(base.width * scale), round(base.height * scale)), Image.LANCZOS)
    d = ImageDraw.Draw(img)
    S = [[(x * scale, y * scale) for x, y in pts] for pts in segs]
    for pts in S:
        d.line(pts, fill="#222", width=round(26 * scale ** 0.6), joint="curve")
    for i, pts in enumerate(S):
        d.line(pts, fill=COLORS[i], width=round(18 * scale ** 0.6), joint="curve")
        p, q = at(pts, 0.55)
        ang = math.atan2(q[1] - p[1], q[0] - p[0])
        k = scale ** 0.6
        tip = (q[0] + 10 * k * math.cos(ang), q[1] + 10 * k * math.sin(ang))
        wing = [(tip[0] - 22 * k * math.cos(ang + s), tip[1] - 22 * k * math.sin(ang + s)) for s in (0.5, -0.5)]
        d.polygon([tip, wing[0], wing[1]], fill="white")
    return img


def shot_badge(d, x, y, n, r=30):
    d.ellipse((x - r, y - r, x + r, y + r), fill=COLORS[n - 1], outline="white", width=4)
    d.text((x, y), str(n), font=common.font(round(r * 1.2), True), fill="white", anchor="mm")


def key_marker(d, x, y, label, lx, ly):
    d.ellipse((x - 15, y - 15, x + 15, y + 15), fill="white", outline="#111", width=5)
    d.text((lx, ly), label, font=common.font(34, True), fill="#111", anchor="mm", stroke_width=5, stroke_fill="white")


def draw(storyboard, out, en, zoom=None):
    """zoom: (shot ids, keyframe indices, (x0, y0, x1, y1) crop in minimap pixels, inset scale, inset top-left)."""
    t = lambda zh, english: english if en else zh
    sb = json.load(open(os.path.join(common.STORYBOARDS, storyboard), encoding="utf-8"))
    track = json.load(open(os.path.join(common.ASSETS, sb["track_path"]), encoding="utf-8"))
    base = Image.open(os.path.join(common.ASSETS, sb["minimap"])).convert("RGB")
    base = Image.blend(ImageOps.grayscale(base).convert("RGB"), Image.new("RGB", base.size, "white"), 0.55)
    W, H = base.size
    segs = [[tuple(p) for p in s["points"]] for s in track["sectors"]]
    allp = [p for s in segs for p in s]
    c = (sum(p[0] for p in allp) / len(allp), sum(p[1] for p in allp) / len(allp))
    kids = [sb["shots"][0]["first"]] + [s["last"] for s in sb["shots"]]
    zshots, zkeys = (zoom[0], zoom[1]) if zoom else ((), ())

    img = Image.new("RGB", (W + t(700, 860), H + TOP), "white")
    img.paste(track_layer(base, segs, 1), (0, TOP))
    d = ImageDraw.Draw(img)
    nshots = len(sb["shots"])
    d.text((30, 28), t(f"{nshots} 镜头分镜：每个镜头跑哪一段，关键帧在哪", f"{nshots}-shot storyboard: what each shot drives and where the keyframes are"),
           font=common.font(46, True), fill="#222")

    for i, pts in enumerate(segs):
        if i + 1 in zshots:
            continue
        p, q = at(pts, 0.5)
        nx, ny = outward(p, q, c)
        x, y = (p[0] + q[0]) / 2 + nx * 58, (p[1] + q[1]) / 2 + ny * 58
        if not (40 < x < W - 40 and 40 < y < H - 40):
            x, y = (p[0] + q[0]) / 2 - nx * 58, (p[1] + q[1]) / 2 - ny * 58
        shot_badge(d, x, y + TOP, i + 1)
    for i, kid in enumerate(kids[:-1]):
        if i in zkeys:
            continue
        x, y = segs[i][0]
        nx, ny = outward(segs[i][0], segs[i][1], c)
        key_marker(d, x, y + TOP, f"{kid} / {kids[-1]}" if i == 0 else kid, x - nx * 58, y - ny * 58 + TOP)

    if zoom:
        (x0, y0, x1, y1), s, (ix, iy) = zoom[2], zoom[3], zoom[4]
        layer = track_layer(base, segs, s).crop((round(x0 * s), round(y0 * s), round(x1 * s), round(y1 * s)))
        d.rectangle((x0, y0 + TOP, x1, y1 + TOP), outline="#333", width=3)
        d.line(((x0 + x1) / 2, y1 + TOP, ix + layer.width / 2, iy + TOP), fill="#333", width=3)
        img.paste(layer, (ix, iy + TOP))
        d.rectangle((ix, iy + TOP, ix + layer.width, iy + TOP + layer.height), outline="#333", width=3)
        d.text((ix + 14, iy + TOP + 10), t("T7–T8 放大", "T7–T8 zoomed"), font=common.font(26, True), fill="#333")
        to = lambda x, y: (ix + (x - x0) * s, iy + TOP + (y - y0) * s)
        for n in zshots:
            p, q = at(segs[n - 1], 0.5)
            nx, ny = outward(p, q, c)
            x, y = to((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
            shot_badge(d, x + nx * 70, y + ny * 70, n)
        for i in zkeys:
            nx, ny = outward(segs[i][0], segs[i][1], c)
            x, y = to(*segs[i][0])
            key_marker(d, x, y, kids[i], x - nx * 60, y - ny * 60)

    x0, y = W + 30, 150
    d.text((x0, y), t("镜头 · 赛段 · 首帧 → 尾帧 · 时长", "Shot · sector · first → last frame · length"), font=common.font(30, True), fill="#222")
    y += 62
    for i, s in enumerate(sb["shots"]):
        d.ellipse((x0, y, x0 + 44, y + 44), fill=COLORS[i])
        d.text((x0 + 22, y + 22), str(s["id"]), font=common.font(26, True), fill="white", anchor="mm")
        d.text((x0 + 62, y - 2), t(s["title"], s["title_en"]), font=common.font(29, True), fill="#222")
        d.text((x0 + 62, y + 36), f"{s['first']} → {s['last']} · {s['duration']:g} {t('秒', 's')} · {t(s['turns'], s['turns_en'])}",
               font=common.font(22), fill="#555")
        y += 96 if nshots > 7 else 104
    y += 10
    legend = [
        "○ 关键帧：镜头交界处的车手视角画面",
        f"   第 i 个镜头从 K(i-1) 开到 K(i)；{kids[0]} 和 {kids[-1]} 都在起终点线上",
        "▶ 行驶方向（逆时针）",
        f"工作流：{sb['name']}_shot_0i 拍镜头 i",
    ] if not en else [
        "○ Keyframe: the onboard view at a shot boundary",
        f"   shot i drives K(i-1) → K(i); {kids[0]} and {kids[-1]} are both on the start line",
        "▶ Driving direction (anticlockwise)",
        f"Workflow {sb['name']}_shot_0i shoots shot i",
    ]
    for line in legend:
        d.text((x0, y), line, font=common.font(23), fill="#444")
        y += 36
    img.save(out, optimize=True)
    print("wrote", out, img.size)


if __name__ == "__main__":
    for en, suffix in ((False, ""), (True, "_en")):
        draw("lap_7shots.json", os.path.join(common.ASSETS, f"storyboard_map_7shots{suffix}.png"), en)
        # the T7-T8 chicane is too tight to label at full size: shots 5-6 and K4-K6 go into an inset inside the loop
        draw("lap_8shots.json", os.path.join(common.ASSETS, f"storyboard_map_8shots{suffix}.png"), en,
             zoom=((5, 6), (4, 5, 6), (600, 60, 880, 220), 2.4, (430, 330)))
