"""Build the ComfyUI workflows and the storyboard handbook from a storyboard file.

    python scripts/make_workflows.py                            # storyboards/lap_7shots.json: workflows/dream7_*.json and docs/storyboard_dream7.md
    python scripts/make_workflows.py --shots lap_8shots.json    # the chapter 7 storyboard
    python scripts/make_workflows.py --install                  # also copies the workflows into <ComfyUI>/user/default/workflows/
    python scripts/make_workflows.py --comfyui /path/to/ComfyUI # ComfyUI install, default $COMFYUI_DIR or the parent directory

Keyframes with "file" reuse an existing input image, so only the remaining keyframes get a text-to-image workflow.
Shots with "clip" reuse a video (path relative to the ComfyUI directory) and get no workflow.
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
MATCH = SB["keyframe"]["match"]
EDIT_KEYFRAMES = [kid for kid in GEN_KEYFRAMES if kid != MATCH["reference"]]
# The gateway's Qwen Image 2.1 edit comes back grainy and over-sharpened at 16:9, so the car edit runs the local model.
HF = "https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main"
EDIT_UNET = "qwen_image_2.1_int8_convrot.safetensors"
EDIT_CLIP = "qwen3vl_8b_int8_convrot.safetensors"
EDIT_VAE = "qwen_image_2.1_vae_bf16.safetensors"
EDIT_SEED, EDIT_STEPS = 860643297917446, 25


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
    g.note((-2160, 0), (460, 620 + 24 * len(kids)), "\n".join([
        "## 赛道关键帧（Qwen Image 2.1 文生图）",
        "",
        f"每一行是一张关键帧。点一次 **运行** 生成全部 {len(kids)} 张，共消耗 {len(kids)} 个额度（30 步 = 1 个额度）。",
        "",
        f"图片保存在 `output/{N}/`，文件名形如 `{kids[0]}_00001_.png`，每重新生成一次编号加 1。",
        "",
        "**生成后对照分镜检查**：前方的路往哪边弯、离弯道多远，画面里该有的东西在不在。"
        "不对就改这张图提示词开头的场景描述（`Photorealistic onboard` 之前的部分），再点运行："
        "ComfyUI 只会重新生成提示词改过的那张。节点没有随机种子，提示词不变时重新生成也是同一张图。",
        "",
        "ComfyUI 重启后缓存会清空，点运行会把每张都重新生成；只想重做一张时，先选中其他行的 Save Image 节点，按 Ctrl+M 静音。",
        "",
        "**定稿后复制到 input 目录**（镜头工作流会读取这些文件名）：",
        "",
        "```",
        *[f"cp output/{N}/{kid}_00001_.png input/{keyframe_file(kid)}" for kid in kids],
        "```",
        "",
        "`00001` 换成你定稿的那一版。",
    ]))
    for r, kid in enumerate(kids):
        k = KEYFRAMES[kid]
        y = r * 420
        g.group(f"{kid} · {k['label']}", -1640, y - 40, 920, 400)
        gen = g.node("AMDQwenImage21TextToImage", (-1620, y), (420, 330),
                     [keyframe_prompt(k), SB["keyframe"]["aspect_ratio"], "Qwen-Image-2.1", SB["keyframe"]["steps"]],
                     outputs=[("IMAGE", "IMAGE")])
        save = g.node("SaveImage", (-1180, y), (420, 330), [f"{N}/{kid}"], inputs=[("images", "IMAGE", False)], color=False)
        g.link(gen, 0, save, 0)
    g.dump(path)


def edit_workflow(kids, path):
    ref = keyframe_file(MATCH["reference"])
    g = Graph()
    g.note((-2160, 0), (460, 980 + 24 * len(kids)), "\n".join([
        "## 统一车身（本地 Qwen Image 2.1 图像编辑）",
        "",
        f"文生图的每张关键帧各画各的车。这里以 `input/{ref}` 为参考（image 2），把每张关键帧（image 1）里的车改成和它一致。",
        "同一个镜头的首尾帧如果是两辆车，视频中途就会换车，所以要在拍镜头之前统一。",
        "",
        "这一步在本机 GPU 上跑，不花额度：网关的图像编辑在 16:9 下会把整张图弄出颗粒和过度锐化。"
        "需要下面 3 个模型（约 17 GB），缺的话打开工作流时 ComfyUI 会提示下载：",
        "",
        f"- `models/diffusion_models/{EDIT_UNET}`",
        f"- `models/text_encoders/{EDIT_CLIP}`",
        f"- `models/vae/{EDIT_VAE}`",
        "",
        f"**运行前** 关键帧已经定稿并复制进 `input/`。点一次 **运行** 编辑全部 {len(kids)} 张，"
        f"结果保存在 `output/{N}/`，文件名形如 `{kids[0]}_edit_00001_.png`。",
        "",
        "**检查**：车和参考图是同一辆（halo、中柱顶上的黑色部件、深蓝车身、前轮），机位高度一致；"
        "路面、弯道、红车、看台这些场景内容没被改掉。哪张不行就在它的提示词里补一句，或者换一个 KSampler 的 seed，再点运行，ComfyUI 只会重做改过的那张。",
        "",
        "**满意后覆盖 input 里的关键帧**（镜头工作流读取这些文件名；未编辑的原图仍在 `output/` 里）：",
        "",
        "```",
        *[f"cp output/{N}/{kid}_edit_00001_.png input/{keyframe_file(kid)}" for kid in kids],
        "```",
        "",
        "`00001` 换成你选定的那一版。覆盖之后再点运行，编辑的就是已经统一过的图。",
    ]))
    unet = g.node("UNETLoader", (-1260, -460), (420, 90), [EDIT_UNET, "default"], outputs=[("MODEL", "MODEL")], color=False)
    clip = g.node("CLIPLoader", (-1260, -330), (420, 110), [EDIT_CLIP, "qwen_image", "default"], outputs=[("CLIP", "CLIP")], color=False)
    vae = g.node("VAELoader", (-1260, -180), (420, 60), [EDIT_VAE], outputs=[("VAE", "VAE")], color=False)
    for n, folder in ((unet, "diffusion_models"), (clip, "text_encoders"), (vae, "vae")):
        name = n["widgets_values"][0]
        n["properties"]["models"] = [{"name": name, "url": f"{HF}/{folder}/{name}", "directory": folder}]
    load_ref = g.node("LoadImage", (-1640, -460), (340, 330), [ref, "image"], outputs=[("IMAGE", "IMAGE"), ("MASK", "MASK")], color=False)
    g.group(f"参考：{MATCH['reference']}，以及模型", -1660, -500, 860, 400)
    for r, kid in enumerate(kids):
        k = KEYFRAMES[kid]
        y = r * 420
        g.group(f"{kid} · {k['label']}", -1660, y - 40, 1920, 400)
        load = g.node("LoadImage", (-1640, y), (340, 330), [keyframe_file(kid), "image"], outputs=[("IMAGE", "IMAGE"), ("MASK", "MASK")], color=False)
        enc = g.node("TextEncodeQwenImage21", (-1260, y), (420, 330), [MATCH["prompt"], "", 0],
                     inputs=[("clip", "CLIP", False), ("vae", "VAE", True), ("images.image_1", "IMAGE", True), ("images.image_2", "IMAGE", True)],
                     outputs=[("positive", "CONDITIONING"), ("negative", "CONDITIONING"), ("latent", "LATENT")])
        ks = g.node("KSampler", (-800, y), (320, 330), [EDIT_SEED, "fixed", EDIT_STEPS, 1, "euler", "simple", 1],
                    inputs=[("model", "MODEL", False), ("positive", "CONDITIONING", False), ("negative", "CONDITIONING", False), ("latent_image", "LATENT", False)],
                    outputs=[("LATENT", "LATENT")])
        dec = g.node("VAEDecode", (-440, y), (200, 50), [], inputs=[("samples", "LATENT", False), ("vae", "VAE", False)], outputs=[("IMAGE", "IMAGE")], color=False)
        save = g.node("SaveImage", (-200, y), (420, 330), [f"{N}/{kid}_edit"], inputs=[("images", "IMAGE", False)], color=False)
        g.link(clip, 0, enc, 0)
        g.link(vae, 0, enc, 1)
        g.link(load, 0, enc, 2)
        g.link(load_ref, 0, enc, 3)
        g.link(unet, 0, ks, 0)
        for slot in range(3):
            g.link(enc, slot, ks, slot + 1)
        g.link(ks, 0, dec, 0)
        g.link(vae, 0, dec, 1)
        g.link(dec, 0, save, 0)
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
        f"- 额度估算：关键帧每张 1 个额度（{kf['steps']} 步），视频按网关计费。"
        f"全部生成一遍约为 {len(GEN_KEYFRAMES)} 张图（每改一次多 1 张）加 {len(GEN_SHOTS) * vid['takes']} 段视频。",
    ]
    if EDIT_KEYFRAMES:
        L.append(f"- 统一车身的编辑用本地 Qwen Image 2.1 模型，不花额度，但需要本机 GPU 和约 17 GB 的模型文件（见下面“统一车身”）。")
    L += [
        "",
    ]
    if "pilot" in SB:
        a, b = SB["pilot"]
        ref = MATCH["reference"]
        edited = [kid for kid in SB["pilot"] if kid != ref]
        L += [
            f"## 第 {next(step)} 步：试拍（强烈建议先做）",
            "",
            f"1. 打开 `{N}_keyframes_pilot`，点运行，只生成 {a} 和 {b}。",
            f"2. 对照分镜检查（见下一步），定稿后复制为 `input/{keyframe_file(a)}` 和 `input/{keyframe_file(b)}`（命令见下面“复制到 input”）。",
            f"3. 打开 `{N}_keyframes_edit_pilot`，点运行，把 {'、'.join(edited)} 的车统一成 {ref} 那辆，检查后覆盖 "
            + "、".join(f"`input/{keyframe_file(kid)}`" for kid in edited) + "（见下面“统一车身”）。",
            f"4. 打开 `{N}_shot_01`，点运行。看三件事：画风是否满意；视频开头和结尾是否贴近两张关键帧；速度感和方向是否对。",
            f"5. 满意了再继续。不满意就先改 `{SHOTS_FILE}` 里的 `style`、`scene` 或 `motion`，重新运行 `make_workflows.py`，再重拍。",
            "",
        ]
    L += [
        f"## 第 {next(step)} 步：生成{'新' if reused else '全部'}关键帧",
        "",
        f"打开 `{N}_keyframes`，点运行，每张关键帧生成 1 张图。逐张对照下面“关键帧画面”和小地图检查：",
        "",
        "- 前方路面的走向和分镜一致：该左转的图里，路就要往左弯；远端只该有一个弯时，不能画出两个。",
        "- 距离和比例对得上：直道有多长、离弯道多远。",
        "- 画面里该有的东西都在，比如起终点的灯架、看台、红车。",
        "- 镜头高度、构图和赛车外观与其他关键帧一致。",
        "",
        "不对就在工作流里改这张图提示词开头的场景描述（`Photorealistic onboard` 之前的部分），再点运行，ComfyUI 只会重新生成改过的那张（ComfyUI 重启过的话会全部重新生成，可以先选中不用重做的 Save Image 节点按 Ctrl+M 静音）。"
        f"节点没有随机种子，提示词不变时重新生成也是同一张图，所以要改的是描述，不是多生成几次。满意后把新的场景描述写回 `{SHOTS_FILE}` 的 `keyframes[].scene`，"
        "否则下次重新运行 `make_workflows.py --install` 时会被覆盖。",
        "",
        "### 复制到 input",
        "",
        f"关键帧输出在 `output/{N}/`，每重新生成一次编号加 1。把定稿的那一张复制进 `input/`，文件名必须和镜头工作流里的一致：",
        "",
        "```bash",
        "cd /path/to/ComfyUI",
    ]
    for kid in GEN_KEYFRAMES:
        L.append(f"cp output/{N}/{kid}_00001_.png input/{keyframe_file(kid)}   # 00001 换成你定稿的那一版")
    L += [
        "```",
        "",
        f"想跳过这一步、直接试视频的话，可以把项目自带的关键帧复制进去：`cp examples/keyframes/{N}_*.png /path/to/ComfyUI/input/`。",
        "",
    ]
    if EDIT_KEYFRAMES:
        ref = MATCH["reference"]
        L += [
            f"## 第 {next(step)} 步：统一车身",
            "",
            f"文生图的每张关键帧各画各的车：halo 顶上的部件、车身颜色、机位高低都可能不同。同一个镜头的首尾帧如果是两辆车，视频中途就会换车，"
            "相邻镜头又共用关键帧，所以要在拍镜头之前把所有关键帧统一成同一辆车。",
            "",
            f"打开 `{N}_keyframes_edit`，点运行：以 `input/{keyframe_file(ref)}` 为参考图，把 {'、'.join(EDIT_KEYFRAMES)} 里的车改成和 {ref} 一致"
            f"。结果在 `output/{N}/{EDIT_KEYFRAMES[0]}_edit_00001_.png` 这样的文件里。",
            "",
            "这一步用本地 Qwen Image 2.1 模型，不花额度：网关的图像编辑在 16:9 下会把整张图弄出颗粒和过度锐化。需要以下模型（约 17 GB），"
            "缺的话打开工作流时 ComfyUI 会提示下载，也可以手动下载：",
            "",
            "```bash",
            "cd /path/to/ComfyUI",
            f"wget -P models/diffusion_models {HF}/diffusion_models/{EDIT_UNET}",
            f"wget -P models/text_encoders {HF}/text_encoders/{EDIT_CLIP}",
            f"wget -P models/vae {HF}/vae/{EDIT_VAE}",
            "```",
            "",
            "检查车和参考图是同一辆、机位高度一致，路面、弯道、红车、看台这些场景内容没被改掉。"
            "不满意就补一句编辑指令或换一个 KSampler 的 seed 再运行。满意后覆盖 input 里的关键帧：",
            "",
            "```bash",
            "cd /path/to/ComfyUI",
            *[f"cp output/{N}/{kid}_edit_00001_.png input/{keyframe_file(kid)}" for kid in EDIT_KEYFRAMES],
            "```",
            "",
            f"编辑指令在 `{SHOTS_FILE}` 的 `keyframe.match`。",
            "",
        ]
    L += [
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
        outputs.append(f"{N}_keyframes_edit_pilot.json")
        edit_workflow([kid for kid in SB["pilot"] if kid != MATCH["reference"]], os.path.join(WF_DIR, outputs[-1]))
    if GEN_KEYFRAMES:
        outputs.append(f"{N}_keyframes.json")
        keyframes_workflow(GEN_KEYFRAMES, os.path.join(WF_DIR, outputs[-1]))
    if EDIT_KEYFRAMES:
        outputs.append(f"{N}_keyframes_edit.json")
        edit_workflow(EDIT_KEYFRAMES, os.path.join(WF_DIR, outputs[-1]))
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
