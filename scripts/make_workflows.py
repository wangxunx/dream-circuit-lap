"""Build the ComfyUI workflows and the storyboard handbook from a storyboard file.

    python scripts/make_workflows.py                            # storyboards/lap_7shots.json: workflows/dream7_*.json and docs/storyboard_dream7.md
    python scripts/make_workflows.py --shots lap_8shots.json    # the chapter 7 storyboard
    python scripts/make_workflows.py --install                  # also copies the workflows into <ComfyUI>/user/default/workflows/
    python scripts/make_workflows.py --comfyui /path/to/ComfyUI # ComfyUI install, default $COMFYUI_DIR or the parent directory

Keyframes with "file" reuse an existing input image, so only the remaining keyframes get a text-to-image workflow.
Shots with "clip" reuse a video (path relative to the ComfyUI directory) and get no workflow.

Adapted from f1_circuit (https://github.com/wangxunx/f1_circuit, commit 42b74ae) scripts/make_workflows.py.
"""
import json
import os
import shutil
import sys

import common

ROOT = common.COMFYUI
WF_DIR = common.WORKFLOWS
USER_WF_DIR = os.path.join(ROOT, "user", "default", "workflows")
MAX_PROMPT = 2000

DEFAULT_SHOTS = "lap_7shots.json"
SHOTS_FILE = sys.argv[sys.argv.index("--shots") + 1] if "--shots" in sys.argv else DEFAULT_SHOTS
with open(os.path.join(common.STORYBOARDS, SHOTS_FILE), encoding="utf-8") as f:
    SB = json.load(f)
KEYFRAMES = {k["id"]: k for k in SB["keyframes"]}
N = SB["name"]
GEN_KEYFRAMES = [k["id"] for k in SB["keyframes"] if "file" not in k]
GEN_SHOTS = [s for s in SB["shots"] if "clip" not in s]


def keyframe_prompt(k):
    return f"{k['scene']} {SB['style']}"


def video_prompt(shot):
    return f"{shot['motion']} {SB['video_rules']} Visual style: {SB['style']}"


def take_prompt(prompt, take):
    # Neither gateway node has a seed and identical prompts come back identical; trailing whitespace
    # is not enough to change that, so every extra take ends with a short distinct sentence.
    return prompt if take == 1 else f"{prompt} Take {take}."


def keyframe_file(kid):
    return KEYFRAMES[kid].get("file", f"{N}_{kid}.png")


class Graph:
    def __init__(self):
        self.nodes, self.links, self.groups = [], [], []

    def node(self, type_, pos, size, widgets, inputs=(), outputs=(), color=True):
        n = {
            "id": len(self.nodes) + 1, "type": type_, "pos": list(pos), "size": list(size), "flags": {},
            "order": len(self.nodes), "mode": 0,
            "inputs": [dict(name=name, type=t, link=None, **({"shape": 7} if optional else {})) for name, t, optional in inputs],
            "outputs": [{"name": name, "type": t, "links": None} for name, t in outputs],
            "properties": {"Node name for S&R": type_} if type_ != "SaveVideo" else {},
            "widgets_values": list(widgets),
        }
        if color:
            n["color"], n["bgcolor"] = "#432", "#653"
        self.nodes.append(n)
        return n

    def link(self, src, src_slot, dst, dst_slot):
        lid = len(self.links) + 1
        t = src["outputs"][src_slot]["type"]
        src["outputs"][src_slot]["links"] = (src["outputs"][src_slot]["links"] or []) + [lid]
        dst["inputs"][dst_slot]["link"] = lid
        self.links.append([lid, src["id"], src_slot, dst["id"], dst_slot, t])

    def note(self, pos, size, text):
        return self.node("MarkdownNote", pos, size, [text])

    def group(self, title, x, y, w, h):
        self.groups.append({"title": title, "bounding": [x, y, w, h], "color": "#3f789e", "font_size": 24, "flags": {}})

    def dump(self, path):
        wf = {
            "last_node_id": len(self.nodes), "last_link_id": len(self.links), "nodes": self.nodes, "links": self.links,
            "groups": self.groups, "config": {}, "extra": {"ds": {"scale": 0.6, "offset": [2300, 100]}}, "version": 0.4,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(wf, f, ensure_ascii=False, indent=2)


def keyframes_workflow(kids, path):
    g = Graph()
    takes = SB["keyframe"]["takes"]
    g.note((-2160, 0), (460, 520), "\n".join([
        "## 赛道关键帧（Qwen Image 2.1 文生图）",
        "",
        f"每一行是一张关键帧，每行 {takes} 个候选。点一次 **运行**，所有候选会一起生成，"
        f"共消耗约 {len(kids) * takes} 个额度（30 步 = 1 个额度）。",
        "",
        f"图片保存在 `output/{N}/`，文件名形如 `{kids[0]}_t2_00001_.png`。",
        "",
        "**挑选后复制到 input 目录**（镜头工作流会读取这些文件名）：",
        "",
        "```",
        f"cp output/{N}/{kids[0]}_t2_00001_.png input/{keyframe_file(kids[0])}",
        "```",
        "",
        "同一张关键帧的几个候选，提示词末尾分别多了 `Take 2.`、`Take 3.`。这是有意为之：节点没有随机种子，"
        "提示词完全相同的话只会得到同一张图。",
    ]))
    for r, kid in enumerate(kids):
        k = KEYFRAMES[kid]
        y = r * 420
        g.group(f"{kid} · {k['label']}", -1640, y - 40, takes * 900 + 20, 400)
        for t in range(1, takes + 1):
            x = -1620 + (t - 1) * 900
            gen = g.node("AMDQwenImage21TextToImage", (x, y), (420, 330),
                         [take_prompt(keyframe_prompt(k), t), SB["keyframe"]["aspect_ratio"], "Qwen-Image-2.1", SB["keyframe"]["steps"]],
                         outputs=[("IMAGE", "IMAGE")])
            save = g.node("SaveImage", (x + 440, y), (420, 330), [f"{N}/{kid}_t{t}"], inputs=[("images", "IMAGE", False)], color=False)
            g.link(gen, 0, save, 0)
    g.dump(path)


def shot_workflow(shot, path):
    g = Graph()
    takes = SB["video"]["takes"]
    first, last = keyframe_file(shot["first"]), keyframe_file(shot["last"])
    g.note((-2160, 220), (460, 560), "\n".join([
        f"## 镜头 {shot['id']}：{shot['title']}（{shot['duration']} 秒）",
        "",
        f"- 弯道：{shot['turns']}",
        f"- 海拔：{shot['elevation']}",
        f"- 速度：{shot['speed']}",
        "",
        f"**运行前** 先把挑好的关键帧放进 `input/`：首帧 `{first}`，尾帧 `{last}`。文件不存在时 LoadImage 会报 *value not in list*。",
        "",
        f"点一次 **运行** 生成 {takes} 条候选，视频保存在 `output/video/{N}/`，文件名形如 `shot_{shot['id']:02d}_t1_00001_.mp4`。",
        "",
        "挑出最好的一条，复制为拼接脚本读取的文件：",
        "",
        "```",
        f"mkdir -p output/video/{N}/selected",
        f"cp output/video/{N}/shot_{shot['id']:02d}_t1_00001_.mp4 output/video/{N}/selected/shot_{shot['id']:02d}.mp4",
        "```",
    ]))
    load_first = g.node("LoadImage", (-1660, 220), (340, 340), [first, "image"], outputs=[("IMAGE", "IMAGE"), ("MASK", "MASK")], color=False)
    load_last = g.node("LoadImage", (-1660, 620), (340, 340), [last, "image"], outputs=[("IMAGE", "IMAGE"), ("MASK", "MASK")], color=False)
    g.group(f"首帧 {shot['first']} / 尾帧 {shot['last']}", -1680, 180, 380, 800)
    for t in range(1, takes + 1):
        y = 220 + (t - 1) * 460
        gen = g.node("AMDMiniMaxH3FirstLastFrameToVideo", (-1260, y), (440, 400),
                     [take_prompt(video_prompt(shot), t), SB["video"]["resolution"], shot["duration"]],
                     inputs=[("first_frame", "IMAGE", False), ("last_frame", "IMAGE", True)], outputs=[("VIDEO", "VIDEO")])
        save = g.node("SaveVideo", (-800, y), (540, 400), [f"video/{N}/shot_{shot['id']:02d}_t{t}", "auto", "auto"],
                      inputs=[("video", "VIDEO", False)], outputs=[("video", "VIDEO")], color=False)
        g.link(load_first, 0, gen, 0)
        g.link(load_last, 0, gen, 1)
        g.link(gen, 0, save, 0)
    g.dump(path)


def storyboard_md(path):
    kf, vid, ed = SB["keyframe"], SB["video"], SB["edit"]
    shots, kfs = SB["shots"], SB["keyframes"]
    total = sum(s["duration"] for s in shots)
    film = total + ed["intro_seconds"] + ed["outro_seconds"] - ed["crossfade"] * (len(shots) + 1)
    reused = [k for k in kfs if "file" in k] + [s for s in shots if "clip" in s]
    shots_arg = "" if SHOTS_FILE == DEFAULT_SHOTS else f" --shots {SHOTS_FILE}"
    step = iter(range(1, 10))
    L = [
        f"# {SB['title']}：分镜与生成手册（{SHOTS_FILE}）",
        "",
        f"{len(shots)} 个镜头，一圈约 {total:.0f} 秒；加上片头、片尾和接缝处的交叉淡化，成片约 {film:.0f} 秒。",
        f"本文件由 `scripts/make_workflows.py` 根据 `storyboards/{SHOTS_FILE}` 生成。要改提示词或时长，请改 `{SHOTS_FILE}` 后重新运行脚本，不要直接改本文件。",
        "",
        "下文的 `input/`、`output/`、`user/` 都指 ComfyUI 目录下的文件夹；`scripts/`、`workflows/`、`examples/` 指本项目目录下的文件夹。",
        "",
        "## 整体流程",
        "",
        f"1. 关键帧：用 Qwen Image 2.1 为每个镜头的交界处生成一张车手视角图片，K0 到 {kfs[-1]['id']} 共 {len(kfs)} 张。",
        "2. 视频：第 i 个镜头用 K(i-1) 作首帧、K(i) 作尾帧，交给 MiniMax H3 首尾帧节点生成。相邻镜头共用交界帧，所以能接上。",
        f"3. 拼接：`stitch_lap.py` 把 {len(shots)} 段按顺序接起来，接缝处做交叉淡化，叠加赛段标题和右下角的小地图，再加上片头和片尾。",
        "",
    ]
    if reused:
        L += ["## 复用的素材", "", "下面这些不用重新生成：", ""]
        for k in kfs:
            if "file" in k:
                L.append(f"- {k['id']}（{k['label']}）：复用 `input/{k['file']}`")
        for s in shots:
            if "clip" in s:
                L.append(f"- 镜头 {s['id']}（{s['title']}）：复用 `{s['clip']}`")
        L.append("")
    L += [
        "## 准备",
        "",
        "- 在 ComfyUI 的 `custom_nodes/` 里安装 [ComfyUI-AMD-Qwen-Image-2.1](https://github.com/wangxunx/ComfyUI-AMD-Qwen-Image-2.1) "
        "和 [ComfyUI-AMD-MiniMaxH3](https://github.com/wangxunx/ComfyUI-AMD-MiniMaxH3)。",
        "- 启动 ComfyUI，并确认 `H3_GATEWAY_API_KEY` 已配置（或 `user/h3_gateway_api_key.txt` 存在）。",
        f"- 工作流在 `workflows/`，可以直接拖进 ComfyUI 打开。运行过 `make_workflows.py --install` 的话，ComfyUI 左侧 **工作流** 面板里能直接看到以 `{N}_` 开头的条目。",
        f"- 额度估算：关键帧每张 1 个额度（{kf['steps']} 步）；视频按网关计费。全部生成一遍约为 {len(GEN_KEYFRAMES) * kf['takes']} 张图加 {len(GEN_SHOTS) * vid['takes']} 段视频。",
        "",
    ]
    if "pilot" in SB:
        a, b = SB["pilot"]
        L += [
            f"## 第 {next(step)} 步：试拍（强烈建议先做）",
            "",
            f"1. 打开 `{N}_keyframes_pilot`，点运行，只生成 {a} 和 {b} 的候选。",
            f"2. 各挑一张，复制为 `input/{keyframe_file(a)}` 和 `input/{keyframe_file(b)}`（命令见下面“挑选与复制”）。",
            f"3. 打开 `{N}_shot_01`，点运行。看三件事：画风是否满意；视频开头和结尾是否贴近两张关键帧；速度感和方向是否对。",
            f"4. 满意了再继续。不满意就先改 `{SHOTS_FILE}` 里的 `style`、`scene` 或 `motion`，重新运行 `make_workflows.py`，再重拍。",
            "",
        ]
    L += [
        f"## 第 {next(step)} 步：生成{'新' if reused else '全部'}关键帧",
        "",
        f"打开 `{N}_keyframes`，点运行。挑选时重点看：",
        "",
        "- 镜头高度和构图一致（halo 防护杆、座舱顶部在画面底部的位置差不多）。",
        "- 赛车外观一致。",
        "- 前方路面的走向和分镜一致：该左转的图里，路就要往左弯。",
        "",
        "### 挑选与复制",
        "",
        f"关键帧输出在 `output/{N}/`，挑好后复制进 `input/`，文件名必须和镜头工作流里的一致：",
        "",
        "```bash",
        "cd /path/to/ComfyUI",
    ]
    for kid in GEN_KEYFRAMES:
        L.append(f"cp output/{N}/{kid}_t1_00001_.png input/{keyframe_file(kid)}   # 把 t1 换成你选的候选")
    L += [
        "```",
        "",
        f"想跳过这一步、直接试视频的话，可以把项目自带的关键帧复制进去：`cp examples/keyframes/{N}_*.png /path/to/ComfyUI/input/`。",
        "",
        f"## 第 {next(step)} 步：逐段生成视频",
        "",
        f"依次打开 `{N}_shot_{GEN_SHOTS[0]['id']:02d}` 到 `{N}_shot_{GEN_SHOTS[-1]['id']:02d}`，每个点一次运行，会生成 {vid['takes']} 条候选。"
        f"选好的那条复制为 `output/video/{N}/selected/shot_0X.mp4`（每个工作流左侧的说明里有现成命令）。",
        "",
        f"## 第 {next(step)} 步：逐段检查",
        "",
        "- 转向方向是否和分镜一致（最常见的错误）。",
        "- 有没有突然切镜、画面倒放或倒车。",
        "- 赛车和镜头位置有没有中途变化。",
        "- 开头和结尾两帧是否贴近关键帧，否则拼接处会跳。",
        "",
        f"## 第 {next(step)} 步：拼接成片",
        "",
        "在本项目目录下运行（ComfyUI 不在上一级目录时，加 `--comfyui /path/to/ComfyUI` 或设置 `COMFYUI_DIR`）：",
        "",
        "```bash",
        f"python scripts/stitch_lap.py{shots_arg}        # 中文版",
        f"python scripts/stitch_lap.py{shots_arg} --en   # 英文版",
        "```",
        "",
        f"脚本读取 ComfyUI 的 `output/video/{N}/selected/shot_0X.mp4`；某个镜头没有 selected 文件时，会用 `output/video/{N}/` 里该镜头最新的一条。"
        + ("复用的镜头直接读取分镜文件里 `clip` 指定的视频。" if reused else "")
        + f"成片写到本项目目录的 `output/{SB['output']}.mp4`，英文版是 `output/{SB['output']}_en.mp4`。",
        "",
        "还没生成任何视频时，可以加 `--placeholder` 先预览节奏、标题和小地图：缺失的镜头会用关键帧（如果有）或占位画面代替。",
        "",
        "## 每个镜头的分镜",
        "",
    ]
    for s in shots:
        L += [
            f"### 镜头 {s['id']}：{s['title']}（{s['duration']:g} 秒）",
            "",
            f"- 首帧 / 尾帧：{s['first']}（{KEYFRAMES[s['first']]['label']}）→ {s['last']}（{KEYFRAMES[s['last']]['label']}）",
        ]
        if "clip" in s:
            L.append(f"- 来源：复用 `{s['clip']}`，不用重新生成")
        L += [
            f"- 弯道：{s['turns']}",
            f"- 海拔：{s['elevation']}",
            f"- 速度：{s['speed']}",
            "",
            "视频提示词（只描述“怎么动”，后面会自动接上统一规则和风格设定）：",
            "",
            "```text",
            s["motion"],
            "```",
            "",
        ]
    L += ["## 关键帧画面", ""]
    for k in kfs:
        L += [f"### {k['id']}：{k['label']}", "", "```text", k["scene"], "```", ""]
    L += [
        "## 统一风格设定（自动附加在每条提示词后面）",
        "",
        "```text",
        SB["style"],
        "```",
        "",
        "视频额外附加：",
        "",
        "```text",
        SB["video_rules"],
        "```",
        "",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


def main():
    os.makedirs(WF_DIR, exist_ok=True)
    for s in GEN_SHOTS:
        n = len(take_prompt(video_prompt(s), SB["video"]["takes"]))
        assert n <= MAX_PROMPT, f"shot {s['id']} prompt is {n} chars, over {MAX_PROMPT}"
    outputs = []
    if "pilot" in SB:
        outputs.append(f"{N}_keyframes_pilot.json")
        keyframes_workflow(SB["pilot"], os.path.join(WF_DIR, outputs[-1]))
    if GEN_KEYFRAMES:
        outputs.append(f"{N}_keyframes.json")
        keyframes_workflow(GEN_KEYFRAMES, os.path.join(WF_DIR, outputs[-1]))
    for s in GEN_SHOTS:
        outputs.append(f"{N}_shot_{s['id']:02d}.json")
        shot_workflow(s, os.path.join(WF_DIR, outputs[-1]))
    storyboard_md(os.path.join(common.DOCS, f"storyboard_{N}.md"))
    if "--install" in sys.argv[1:]:
        os.makedirs(USER_WF_DIR, exist_ok=True)
        for name in outputs:
            shutil.copy(os.path.join(WF_DIR, name), os.path.join(USER_WF_DIR, name))
    print(f"wrote {len(outputs)} workflows to {WF_DIR}" + (f" and {USER_WF_DIR}" if "--install" in sys.argv[1:] else ""))


if __name__ == "__main__":
    main()
