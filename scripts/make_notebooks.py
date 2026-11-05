"""Generate the notebooks: notebooks/local.ipynb and cloud.ipynb in Chinese, local_en.ipynb and cloud_en.ipynb in English.

    python scripts/make_notebooks.py

Edit the cells here rather than in the notebooks; every markdown cell has a Chinese and an English text, code cells are
shared unless they show language-specific labels or files. The notebooks are written without outputs.
"""
import json
import os

import common


def md(zh, en):
    return {"cell_type": "markdown", "source": (zh, en)}


def code(zh, en=None):
    return {"cell_type": "code", "source": (zh, zh if en is None else en)}


def notebook(cells, en):
    out = []
    for i, c in enumerate(cells):
        cell = {"cell_type": c["cell_type"], "metadata": {}}
        if c["cell_type"] == "code":
            cell.update(execution_count=None, outputs=[])
        cell.update(source=c["source"][en].strip("\n").splitlines(keepends=True), id=f"cell-{i:02d}")
        out.append(cell)
    return {"cells": out, "metadata": {"kernelspec": {"display_name": "Python 3 (ipykernel)", "language": "python", "name": "python3"},
                                       "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}


def intro(zh_where, en_where):
    return md(f"""
# 开上你的梦幻赛道：用 AI 分镜跑完一圈（{zh_where}）

我们手里有一张自己设计的赛道俯视图。任务：生成一段车手第一视角的视频，把这条赛道完整跑一圈。

| 章节 | 内容 | 要生成的内容 |
|---|---|---|
| 1 | 认识赛道地图，抛出任务 | 无 |
| 2 | 一个提示词直接生成：15 秒、跑不完、不可控 | 每次 1 段视频（可选） |
| 3 | 分镜：把一圈拆成 7 个镜头 | 无 |
| 4 | 关键帧：每个镜头交界处一张车手视角图，对照分镜检查，再统一车身 | 8 张图起，每改一次多 1 张；统一车身用本地模型，需要 GPU（可直接用自带素材） |
| 5 | 逐段拍镜头：首尾帧生成视频 | 最多 14 段视频（可直接用自带素材） |
| 6 | 拼接成片，找出问题 | 无 |
| 7 | 用分镜修好 T7–T8 减速弯 | 2 张关键帧，3 段视频 × 2 候选（可直接用自带素材） |
| 8 | 总结和练习 | 无 |

这个 notebook 只负责准备环境、启动 ComfyUI、准备素材和拼接成片；生成图片和视频都在浏览器里的 ComfyUI 完成。
每个生成步骤都附有已经生成好的关键帧和视频，可以直接用它们快速拼出成片，也可以自己重新生成。

### 怎么用这个 notebook

- 从上往下逐格运行：点中一格，按 `Shift+Enter`。左边显示 `[*]` 表示还在运行，变成数字才算完成，输出显示在这一格下面。
- 两条路线，可以每章自由选：
  - **路线 A，用自带素材**：所有单元格按顺序运行，自带素材会补上关键帧和视频。
  - **路线 B，自己生成**：遇到“在浏览器里”的步骤，先去 ComfyUI 生成，再运行“挑选”单元格（视频要先填上你选中的候选编号）；没生成的部分仍由自带素材补上。
- 重启 kernel 或第二天继续时，从第 0 节重新运行即可，已经完成的步骤会自动跳过。
""", f"""
# Drive Your Dream Circuit: an AI-Storyboarded Onboard Lap ({en_where})

We have a top-down map of a race track we designed. The task: generate an onboard video that drives one full lap of it.

| Chapter | Topic | What gets generated |
|---|---|---|
| 1 | The track map and the task | none |
| 2 | One prompt: 15 s, cannot finish the lap, hard to control | 1 video per run (optional) |
| 3 | Storyboard: split the lap into 7 shots | none |
| 4 | Keyframes: one onboard image at each shot boundary, checked against the storyboard, then the car made consistent | 8 images, plus 1 per revision; the car edit runs a local model and needs a GPU (bundled results available) |
| 5 | Shots: first-last-frame video, one shot at a time | up to 14 videos (bundled results available) |
| 6 | Stitch the film and find the problems | none |
| 7 | Fix the T7–T8 chicane with the storyboard | 2 keyframes, 3 videos × 2 takes (bundled results available) |
| 8 | Wrap-up and exercise | none |

This notebook only sets up the environment, starts ComfyUI, prepares the media and stitches the films; images and videos are generated in ComfyUI in the browser.
Every generation step ships with ready-made keyframes and videos, so you can stitch the film quickly from them or generate everything yourself.
The chapter outlines in `docs/` and the notes inside the ComfyUI workflows are in Chinese; this notebook covers the same points.

### How to use this notebook

- Run the cells from top to bottom: click a cell and press `Shift+Enter`. `[*]` on the left means it is still running; a number means it is done, and its output appears below the cell.
- Two routes, chosen per chapter:
  - **Route A, bundled media**: run every cell in order; the bundled media fill in the keyframes and videos.
  - **Route B, generate yourself**: at each "In the browser" step, generate in ComfyUI first, then run the picker cell (for videos, fill in the takes you chose first); anything you did not generate is still filled in from the bundled media.
- After a kernel restart, or when you come back the next day, rerun section 0; finished steps are skipped.
""")


NODES_CODE = code("""
for repo in ("ComfyUI-AMD-Qwen-Image-2.1", "ComfyUI-AMD-MiniMaxH3"):
    if (COMFY / "custom_nodes" / repo).is_dir():
        print("installed:", repo)
    else:
        subprocess.run(["git", "clone", "-q", "--depth", "1", f"https://github.com/wangxunx/{repo}.git", str(COMFY / "custom_nodes" / repo)], check=True)
        print("cloned:", repo)
""")

KEY_CODE = code("""
key_file = COMFY / "user" / "h3_gateway_api_key.txt"
if os.environ.get("H3_GATEWAY_API_KEY") or key_file.is_file():
    print("H3 key already configured")
else:
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_text(getpass("H3 key: ").strip())
    print("saved to", key_file)
""")

EDIT_MODELS_CODE = """
DOWNLOAD = False  # NOTE
for folder, name in (("diffusion_models", "qwen_image_2.1_int8_convrot.safetensors"),
                     ("text_encoders", "qwen3vl_8b_int8_convrot.safetensors"),
                     ("vae", "qwen_image_2.1_vae_bf16.safetensors")):
    dst = COMFY / "models" / folder / name
    if dst.exists():
        print("found", dst)
    elif DOWNLOAD:
        part = dst.with_name(name + ".part")
        urllib.request.urlretrieve(f"https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/{folder}/{name}", part)
        part.rename(dst)
        print("downloaded", dst)
    else:
        print("missing", dst)
"""

LOCAL = [
    intro("本地版", "local"),
    md("""
## 0. 准备环境

本地版使用本项目目录的上一级 ComfyUI（`dream-circuit-lap` 放在 ComfyUI 目录里），也可以用环境变量 `COMFYUI_DIR` 指定。
请用 ComfyUI 所在的 Python 环境作为这个 notebook 的内核，下面启动 ComfyUI 时用的就是这个解释器。
""", """
## 0. Setup

The local notebook uses the ComfyUI one level above this project (`dream-circuit-lap` cloned inside the ComfyUI directory), or the one in `COMFYUI_DIR`.
Use ComfyUI's Python environment as this notebook's kernel; ComfyUI is started below with the same interpreter.
"""),
    code("""
import os, sys, shutil, socket, subprocess, time, urllib.request
from getpass import getpass
from pathlib import Path

PROJECT = Path.cwd().parent
COMFY = Path(os.environ.get("COMFYUI_DIR", PROJECT.parent)).resolve()
PY = sys.executable
assert (COMFY / "main.py").is_file(), f"ComfyUI not found at {COMFY}, set COMFYUI_DIR"
os.environ["COMFYUI_DIR"] = str(COMFY)
print("project:", PROJECT)
print("ComfyUI:", COMFY)
print("python :", PY)
"""),
    code("""
%pip install -q -r ../requirements.txt
"""),
    md("""
### 安装两个云端节点

[ComfyUI-AMD-Qwen-Image-2.1](https://github.com/wangxunx/ComfyUI-AMD-Qwen-Image-2.1) 生成关键帧，[ComfyUI-AMD-MiniMaxH3](https://github.com/wangxunx/ComfyUI-AMD-MiniMaxH3) 生成视频。
两者都在云端推理；只有第 4、7 章统一车身的编辑用本地模型、需要 GPU，没有 GPU 时用自带素材跳过即可。已经装过的会跳过。
""", """
### Install the two cloud nodes

[ComfyUI-AMD-Qwen-Image-2.1](https://github.com/wangxunx/ComfyUI-AMD-Qwen-Image-2.1) generates the keyframes and [ComfyUI-AMD-MiniMaxH3](https://github.com/wangxunx/ComfyUI-AMD-MiniMaxH3) the videos.
Both run in the cloud; only the car edit in chapters 4 and 7 runs a local model and needs a GPU, and without one the bundled media let you skip it. Nodes that are already installed are skipped.
"""),
    NODES_CODE,
    md("""
### 配置 H3 key

到 https://h3.oneclickamd.ai 注册拿到 key。key 写进 ComfyUI 的 `user/h3_gateway_api_key.txt`，两个节点都从这里读，不会写进工作流或视频元数据。
运行下一格时，输出区会出现一个输入框：粘贴 key，按回车。
""", """
### Configure the H3 key

Register at https://h3.oneclickamd.ai to get a key. It is written to ComfyUI's `user/h3_gateway_api_key.txt`; both nodes read it from there, and it never ends up in workflows or video metadata.
Running the next cell shows an input box below it: paste the key and press Enter.
"""),
    KEY_CODE,
    md("""
### 启动 ComfyUI

ComfyUI 在后台启动，第一次大约要等十几秒，日志在 ComfyUI 的 `user/comfyui_dream_circuit.log`。有 GPU 时使用 GPU（统一车身要用），没有时以 `--cpu` 启动。
8188 端口已经有 ComfyUI 在运行时直接使用它；如果它是在安装节点之前启动的，请先重启，否则看不到新节点。

Jupyter 跑在远程机器上（例如通过 Cursor / VS Code 的 Remote SSH）时，浏览器打不开 http://127.0.0.1:8188 的话，在 **Ports（端口）** 面板里转发 8188 端口。
""", """
### Start ComfyUI

ComfyUI starts in the background; the first start takes 10–20 seconds. The log is ComfyUI's `user/comfyui_dream_circuit.log`. It uses the GPU when there is one (the car edit needs it) and starts with `--cpu` otherwise.
A ComfyUI already running on port 8188 is reused; if it was started before the nodes were installed, restart it, otherwise the new nodes are missing.

If Jupyter runs on a remote machine (for example through Cursor or VS Code Remote SSH) and http://127.0.0.1:8188 does not open in your browser, forward port 8188 in the **Ports** panel.
"""),
    code("""
def comfy_up():
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", 8188)) == 0

if comfy_up():
    print("ComfyUI is already running")
else:
    log = open(COMFY / "user" / "comfyui_dream_circuit.log", "w")
    gpu = subprocess.run([PY, "-c", "import torch; assert torch.cuda.is_available()"], capture_output=True).returncode == 0
    subprocess.Popen([PY, "main.py", "--port", "8188"] + ([] if gpu else ["--cpu"]), cwd=COMFY, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    print("GPU" if gpu else "no GPU, started with --cpu")
    for _ in range(120):
        time.sleep(1)
        if comfy_up():
            break
    else:
        raise RuntimeError(f"ComfyUI did not start, see {log.name}")
print("open http://127.0.0.1:8188")
"""),
]

CLOUD = [
    intro("云端版", "cloud"),
    md("""
## 0. 准备环境
""", """
## 0. Setup
"""),
    code("""
import os, sys, shutil, subprocess, urllib.request
from getpass import getpass
from pathlib import Path

PROJECT = Path.cwd().parent
if not (PROJECT / "scripts" / "stitch_lap.py").is_file():
    PROJECT = Path.home() / "dream-circuit-lap"
    if not PROJECT.is_dir():
        subprocess.run(["git", "clone", "--depth", "1", "https://github.com/wangxunx/dream-circuit-lap.git", str(PROJECT)], check=True)
COMFY = Path(os.environ.get("COMFY_DIR", "/comfyui_workspace/ComfyUI"))
PY = sys.executable
assert (COMFY / "main.py").is_file(), f"ComfyUI not found at {COMFY}, set COMFY_DIR"
os.environ["COMFYUI_DIR"] = str(COMFY)
print("project:", PROJECT)
print("ComfyUI:", COMFY)
"""),
    code("""
%pip install -q -r {PROJECT}/requirements.txt
"""),
    md("""
### 安装两个云端节点

[ComfyUI-AMD-Qwen-Image-2.1](https://github.com/wangxunx/ComfyUI-AMD-Qwen-Image-2.1) 生成关键帧，[ComfyUI-AMD-MiniMaxH3](https://github.com/wangxunx/ComfyUI-AMD-MiniMaxH3) 生成视频。已经装过的会跳过。
""", """
### Install the two cloud nodes

[ComfyUI-AMD-Qwen-Image-2.1](https://github.com/wangxunx/ComfyUI-AMD-Qwen-Image-2.1) generates the keyframes and [ComfyUI-AMD-MiniMaxH3](https://github.com/wangxunx/ComfyUI-AMD-MiniMaxH3) the videos. Nodes that are already installed are skipped.
"""),
    NODES_CODE,
    md("""
### 配置 H3 key

到 https://h3.oneclickamd.ai 注册拿到 key。key 写进 ComfyUI 的 `user/h3_gateway_api_key.txt`，不会写进工作流或视频元数据。
运行下一格时，输出区会出现一个输入框：粘贴 key，按回车。
""", """
### Configure the H3 key

Register at https://h3.oneclickamd.ai to get a key. It is written to ComfyUI's `user/h3_gateway_api_key.txt` and never ends up in workflows or video metadata.
Running the next cell shows an input box below it: paste the key and press Enter.
"""),
    KEY_CODE,
    md("""
### 启动 ComfyUI

脚本在后台启动 ComfyUI，打印 `ComfyUI URL` 后返回，可以继续运行后面的单元格。重新运行这一格会重启 ComfyUI，URL 不变。

> **注意：** 拿到这个 URL 的任何人都能用你的 H3 key 提交任务。不要把它发到群里或贴在公开的地方。
""", """
### Start ComfyUI

The script starts ComfyUI in the background, prints the `ComfyUI URL` and returns, so you can keep running the cells below. Rerunning this cell restarts ComfyUI and keeps the URL.

> **Note:** anyone with this URL can queue jobs on your H3 key. Do not post it in group chats or anywhere public.
"""),
    code("""
!COMFY_DIR="{COMFY}" bash "{PROJECT}/scripts/start_comfyui_cloud.sh"
"""),
]

CHAPTERS = [
    md("""
### 准备素材

下载历史生成结果（约 72 MB，带 sha256 校验，可以重复运行）；系统里没有中文字体时顺带下载 Noto Sans SC，拼接时的中文标题要用。
然后把各章工作流装进 ComfyUI：浏览器左侧 **工作流** 面板里会出现 `ch2_single_prompt`、`dream7_*`、`dream8_*`。
""", """
### Prepare media

Download the historical results (about 72 MB, sha256-checked, safe to rerun), plus Noto Sans SC if the system has no CJK font; the stitching script draws its labels with it.
Then install the chapter workflows into ComfyUI: `ch2_single_prompt`, `dream7_*` and `dream8_*` appear in the **Workflows** panel on the left of the browser.
"""),
    code("""
!"{PY}" "{PROJECT}/scripts/fetch_media.py" --fonts
(COMFY / "user" / "default" / "workflows").mkdir(parents=True, exist_ok=True)
shutil.copy(PROJECT / "workflows" / "ch2_single_prompt.json", COMFY / "user" / "default" / "workflows")
shutil.copy(PROJECT / "assets" / "fictional_track_v1.png", COMFY / "input")
!"{PY}" "{PROJECT}/scripts/make_workflows.py" --install
!"{PY}" "{PROJECT}/scripts/make_workflows.py" --shots lap_8shots.json --install
"""),
    md("""
### 第一次用 ComfyUI 先看这里

1. 浏览器打开 ComfyUI（本地版是 http://127.0.0.1:8188，云端版是上面打印的 `ComfyUI URL`）。第一次打开会弹出 Templates 模板窗口，点右上角 × 关掉。中间是画布，方框是节点，连线是数据的流向。
2. 按 `w` 或点左侧 **Workflows（工作流）**，列表里点名字就能打开工作流。看不到本项目的工作流时，刷新浏览器页面（F5）。
3. 本项目的每个工作流左边都有一个黄色的说明节点，写着这一步做什么、运行前要准备什么。滚轮缩放，按住空白处拖动画布，按 `.` 显示全部节点。
4. 点右上角蓝色的 **Run（运行）** 提交任务，旁边的 “N active” 是还在进行的任务数。生成在云端完成，视频通常要等几分钟。
5. 结果显示在 Save Image / Save Video 节点里，同时保存在 ComfyUI 的 `output/` 目录。
6. Load Image 节点被红框圈住、右上角提示 “Media input missing” 或 “errors found”：它要读的图片还不在 `input/`。先运行 notebook 里对应的复制或挑选单元格，再刷新浏览器页面（F5），红框就会消失。
7. 第 4–7 章的工作流不要改文件名前缀，后面的挑选和拼接按这些文件名找文件。
""", """
### First time in ComfyUI

1. Open ComfyUI in the browser (http://127.0.0.1:8188 for the local notebook, the `ComfyUI URL` printed above for the cloud one). A Templates dialog appears on first launch; close it with the × in the top right. The middle is the canvas: boxes are nodes, and links show where the data flows.
2. Press `w` or click **Workflows** on the left, then click a name to open that workflow. If this project's workflows are not listed, reload the page (F5).
3. Every workflow in this project has a yellow note on its left saying what the step does and what to prepare first (in Chinese). Scroll to zoom, drag an empty spot to pan, press `.` to fit all nodes.
4. Click the blue **Run** button in the top right to queue the job; "N active" next to it counts the jobs still running. Generation happens in the cloud; a video usually takes a few minutes.
5. Results show up in the Save Image / Save Video nodes and are saved in ComfyUI's `output/` directory.
6. A Load Image node outlined in red with a "Media input missing" or "errors found" toast in the top right: the image it reads is not in `input/` yet. Run the matching copy or picker cell in this notebook first, then reload the page (F5) and the red outline goes away.
7. Do not change the filename prefixes in the chapter 4–7 workflows; the picker and stitching cells find files by these names.
"""),
    md("""
下面的 `play` 用相对路径引用视频，需要在 JupyterLab / JupyterHub 里打开这个 notebook，并且本项目目录在 Jupyter 的根目录之下；图片缩小后直接嵌入。
""", """
`play` below references videos by relative path, so open this notebook in JupyterLab / JupyterHub with the project directory under Jupyter's root directory; images are shrunk and embedded directly.
"""),
    code("""
from IPython.display import HTML, Markdown, display
from base64 import b64encode
from io import BytesIO
from PIL import Image
import json

MEDIA = PROJECT / "media"

def figure(inner, p, label, width):
    caption = f'{label}<br><small><code>{Path(p).name}</code></small>' if label else Path(p).name
    return f'<figure style="display:inline-block;vertical-align:top;margin:4px">{inner}<figcaption style="max-width:{width}px">{caption}</figcaption></figure>'

def play(*paths, width=480, labels=()):
    labels = labels or [None] * len(paths)
    display(HTML("".join(figure(f'<video src="{os.path.relpath(p)}" width="{width}" controls muted></video>', p, label, width) for p, label in zip(paths, labels))))

def show(*paths, width=360, labels=()):
    tags = []
    for p, label in zip(paths, labels or [None] * len(paths)):
        im = Image.open(p).convert("RGB")
        im.thumbnail((width * 2, width * 2))
        buf = BytesIO()
        im.save(buf, "JPEG", quality=85)
        tags.append(figure(f'<img src="data:image/jpeg;base64,{b64encode(buf.getvalue()).decode()}" width="{width}">', p, label, width))
    display(HTML("".join(tags)))

def copy_missing(src, dst):
    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.copy(src, dst)
        print("copied", dst)

def pick(patterns, src_dir, dst):
    missing = []
    for name, pattern in patterns.items():
        found = sorted(Path(src_dir).glob(pattern), key=os.path.getmtime)
        if not found:
            missing.append(name)
            continue
        target = Path(str(dst).format(name))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(found[-1], target)
        print(found[-1].name, "->", target)
    if missing:
        print("not generated yet:", " ".join(missing))
"""),
    md("""
## 第 1 章：赛道地图和任务

5.1 km，11 个弯，逆时针。从起终点直道出发，依次是重刹弯 T1–T2、爬坡弯组 T3–T5、高速大半径弯 T6、短直道和减速弯 T7–T8、下坡弯 T9、最后赛段 T10–T11。

任务：根据这张图，生成一段车手第一视角的视频，体验跑完一圈。讲解提纲见 `docs/ch1_map.md`。
""", """
## Chapter 1: the track map and the task

5.1 km, 11 turns, anticlockwise. From the start/finish straight: the heavy-braking T1–T2, the climbing turns T3–T5, the fast sweeper T6, a short straight into the T7–T8 chicane, the downhill T9 and the final sector T10–T11.

The task: from this map, generate an onboard video that drives one full lap. Outline (in Chinese): `docs/ch1_map.md`.
"""),
    code("""
show(PROJECT / "assets" / "fictional_track_v1.png", width=900)
"""),
    md("""
## 第 2 章：一个提示词跑一圈

最直接的想法：把俯视图当首帧，用一个提示词描述 7 个赛道元素，让 MiniMax H3 生成。
在浏览器里打开 `ch2_single_prompt` 工作流就能试（每次生成 1 段视频）。下面是当时的 9 次尝试：

- 1–6 号一直在改提示词：强调逆时针、说明起点位置、要求中文配音。但视频都从地图飞进去，“第一视角”一直嵌在地图的图例和海拔剖面中间，15 秒只够跑一小段，弯道也和地图对不上。
- 5 号和 6 号的提示词完全相同，结果的结构几乎一样，只有细节不同：重跑一次救不了，结果是被输入决定的。
- 7–8 号把目标缩小为“只拍起终点直道到 T1”，画风却变成了卡通；9 号再加上“路况和两侧环境与俯视图一致”，终于得到全屏、写实的座舱视角。

两个启发：一次只拍一小段；首帧不该是俯视图，而应该是车手视角的画面。这就是分镜和关键帧的起点。
""", """
## Chapter 2: one prompt for the whole lap

The most direct idea: use the top-down map as the first frame, describe the 7 track elements in one prompt, and let MiniMax H3 generate.
Open the `ch2_single_prompt` workflow in the browser to try it (1 video per run). Below are the 9 attempts from the time:

- Attempts 1–6 kept refining the prompt: stress anticlockwise, say where the start is, ask for Chinese narration. Every video still flies into the map, the "onboard view" stays framed between the map's legend and elevation profile, 15 seconds only covers a short stretch, and the turns do not match the map.
- Attempts 5 and 6 used exactly the same prompt and came out with almost the same structure, differing only in details: rerunning does not help, because the input decides the result.
- Attempts 7–8 narrowed the goal to "only the start/finish straight up to T1", but the style turned cartoonish; attempt 9 added "road surface and surroundings consistent with the map" and finally got a full-screen, photorealistic cockpit view.

Two lessons: shoot one short stretch at a time, and the first frame should be an onboard image, not the map. That is where storyboards and keyframes come from.
"""),
    code("""
play(MEDIA / "ch2_single_prompt_01.mp4", MEDIA / "ch2_single_prompt_05.mp4", MEDIA / "ch2_single_prompt_06.mp4", width=360)
play(MEDIA / "ch2_single_prompt_07.mp4", MEDIA / "ch2_single_prompt_09.mp4", width=360)
"""),
    md("""
## 第 3 章：分镜

把一圈拆成 7 个镜头，每个镜头 5–8 秒。相邻镜头共用一张交界处的关键帧 K0–K7：第 i 个镜头以 K(i-1) 为首帧、K(i) 为尾帧，所以能接上。
分镜表在 `storyboards/lap_7shots.json`，生成的手册是 `docs/storyboard_dream7.md`。
""", """
## Chapter 3: the storyboard

Split the lap into 7 shots of 5–8 seconds each. Neighbouring shots share a keyframe at their boundary, K0–K7: shot i starts at K(i-1) and ends at K(i), so the shots join up.
The storyboard is `storyboards/lap_7shots.json`; the generated guide is `docs/storyboard_dream7.md` (in Chinese).
"""),
    code("""
sb = json.load(open(PROJECT / "storyboards" / "lap_7shots.json", encoding="utf-8"))
rows = ["| 镜头 | 赛段 | 首帧 → 尾帧 | 时长 | 弯道 |", "|---|---|---|---|---|"]
rows += [f"| {s['id']} | {s['title']} | {s['first']} → {s['last']} | {s['duration']} 秒 | {s['turns']} |" for s in sb["shots"]]
display(Markdown("\\n".join(rows)))
show(PROJECT / "assets" / "storyboard_map_7shots.png", width=1000)
""", """
sb = json.load(open(PROJECT / "storyboards" / "lap_7shots.json", encoding="utf-8"))
rows = ["| Shot | Sector | First → last frame | Length | Turns |", "|---|---|---|---|---|"]
rows += [f"| {s['id']} | {s['title_en']} | {s['first']} → {s['last']} | {s['duration']} s | {s['turns_en']} |" for s in sb["shots"]]
display(Markdown("\\n".join(rows)))
show(PROJECT / "assets" / "storyboard_map_7shots_en.png", width=1000)
"""),
    md("""
上图每种颜色是一个镜头跑的路段，圆圈是关键帧的位置。后面几章提到的 K0–K7、镜头 1–7、`dream7_shot_01` 到 `dream7_shot_07`，都可以回到这张图对照。
""", """
Each colour is the stretch one shot drives, and the circles mark the keyframes. Come back to this map whenever later chapters mention K0–K7, shots 1–7, or `dream7_shot_01` to `dream7_shot_07`.
"""),
    md("""
## 第 4 章：关键帧

关键帧是镜头之间的“合同”：视频从首帧出发、必须到达尾帧，尾帧里画了什么，模型就往哪里开。所以每张图都要对照分镜检查，最重要的一条是：前方的路往哪边弯，要和地图一致。

节点没有随机种子，提示词不变时重新生成也是同一张图。所以每张关键帧只生成 1 次；不对的时候，找出哪里和分镜不符，把它写进场景描述，再生成。下面是同一张 K0 的几次生成，每次只改一个问题：

1. 直道远端先左弯、再右弯、再上坡；地图上从起终点线只能看到 T1 一个左弯。场景改为直道笔直、尽头只有一个左弯、四周平坦。
2. 左弯离得太近，直道看起来只有两三百米；地图上约 1 km。场景改为直道一直延伸到消失点，左弯只在消失点处隐约可见。
3. 路对了，但起跑灯架远在红车后面，红灯只剩几个小点。场景改为灯架在车前约 20 米、占满画面上部。
4. 定稿。

终点 K7 的灯架要和 K0 是同一个，所以 K7 的场景描述把 K0 灯架的样子逐项写了进去。
""", """
## Chapter 4: keyframes

Keyframes are the "contract" between shots: the video starts at the first frame and must arrive at the last one, so the model drives toward whatever the last frame shows. Check every image against the storyboard; the most important check is that the road ahead bends the same way as on the map.

The nodes have no random seed: with an unchanged prompt, generating again gives the same image. So generate each keyframe once; when it is wrong, find where it disagrees with the storyboard, write that into the scene description and generate again. Below are several generations of the same K0, each fixing one problem:

1. The far end of the straight bends left, then right, then climbs; from the start/finish line the map shows only one left-hander, T1. The scene was changed to a dead-straight straight ending in a single left-hander, flat all around.
2. The left-hander is too close, so the straight looks only two or three hundred metres long; on the map it is about 1 km. The scene was changed so the straight runs to the vanishing point, with the left-hander only faintly visible there.
3. The road is right, but the start light gantry is far behind the red car and the red lights are just a few dots. The scene was changed to put the gantry about 20 m ahead of the car, filling the top of the frame.
4. Final.

The gantry in the finishing K7 must be the same one as in K0, so K7's scene description spells out K0's gantry piece by piece.
"""),
    code("""
show(*[PROJECT / "examples" / "k0_versions" / f"K0_v{v}.jpg" for v in range(1, 5)], width=440)
"""),
    md("""
在浏览器里：

1. 打开 `dream7_keyframes_pilot`，点 Run，先只生成 K0、K1，看画风和机位是否满意。
2. 打开 `dream7_keyframes`，点 Run 生成全部 8 张，每张一行。
3. 逐张对照第 3 章的分镜表和小地图检查：路往哪边弯、离弯道多远、灯架和看台这类元素在不在、机位和赛车是否一致。
4. 哪张不对，就改那个节点提示词开头的场景描述（`Photorealistic onboard` 之前的部分），再点 Run。ComfyUI 只会重新生成改过的那张；ComfyUI 重启过的话会全部重新生成，可以先选中不用重做的 Save Image 节点按 Ctrl+M 静音。
5. 都满意后运行下一格，每张关键帧最新的那一版会复制到 ComfyUI 的 `input/dream7_K0.png` 到 `dream7_K7.png`。

路线 A 直接运行下面两格即可：挑选格找不到自己生成的图就什么都不做，再下一格用自带的关键帧补上缺的，不会覆盖你选好的文件。讲解提纲见 `docs/ch4_keyframes.md`。
""", """
In the browser:

1. Open `dream7_keyframes_pilot` and click Run to generate only K0 and K1 first; check the style and camera position.
2. Open `dream7_keyframes` and click Run to generate all 8, one row each.
3. Check each one against the chapter 3 storyboard table and map: which way the road bends, how far away the turn is, whether elements such as the light gantry and grandstands are there, and whether the camera and car match.
4. If one is wrong, edit the scene description at the start of that node's prompt (the part before `Photorealistic onboard`) and click Run again. ComfyUI only regenerates the edited image; after a ComfyUI restart everything regenerates, so first select the Save Image nodes you do not want redone and press Ctrl+M to mute them.
5. When all are good, run the next cell: the newest version of each keyframe is copied to ComfyUI's `input/dream7_K0.png` to `dream7_K7.png`.

For route A just run the next two cells: the picker does nothing if it finds none of your images, and the cell after it fills in the missing keyframes from the bundled ones without overwriting files you picked. Outline (in Chinese): `docs/ch4_keyframes.md`.
"""),
    code("""
pick({f"K{i}": f"K{i}_*.png" for i in range(8)}, COMFY / "output" / "dream7", COMFY / "input" / "dream7_{}.png")
"""),
    code("""
for i in range(8):
    copy_missing(PROJECT / "examples" / "keyframes" / f"dream7_K{i}.png", COMFY / "input" / f"dream7_K{i}.png")
show(*[COMFY / "input" / f"dream7_K{i}.png" for i in range(8)], width=300)
"""),
    md("""
### 统一车身

`style` 里写了赛车的样子，文生图还是每张各画各的车：halo 顶上的部件有大有小、车身有的带红色或白色、机位有高有低。
首尾帧是两辆车时，视频会在中途换车，相邻镜头又共用关键帧，所以这一步放在拍镜头之前。

编辑用本地 Qwen Image 2.1 模型（约 17 GB，需要 GPU）。

在浏览器里（路线 B）：

1. 把下一格的 `DOWNLOAD` 改成 `True` 并运行，下载缺的模型（已有的会跳过），然后重启 ComfyUI 或刷新页面。
2. 打开 `dream7_keyframes_edit`，点 Run：以 K1 为参考，把 K0、K2–K7 的车改成 K1 那辆。
3. 逐张检查：车和 K1 是同一辆、机位一致，路面走向、红车、看台这些场景没被改掉。不行就补一句指令或换 KSampler 的 seed 再运行。
4. 满意后运行再下一格，编辑结果会覆盖 `input/` 里的关键帧，然后刷新页面。

路线 A 直接运行下面几格：模型不会下载，挑选格什么都不做。自带的关键帧已经统一过车身，自带的视频就是用它们拍的；下面最后一格是编辑前后的对比。讲解提纲见 `docs/ch4_keyframes.md`。
""", """
### Make the car consistent

`style` describes the car, but text-to-image still draws a different car in each keyframe: the part on top of the halo changes size, some bodies have red or white on them, the camera sits higher or lower.
When the first and last frame show two different cars, the video swaps cars midway, and neighbouring shots share keyframes, so this step comes before the shots.

The edit runs the local Qwen Image 2.1 model (about 17 GB, needs a GPU).

In the browser (route B):

1. Set `DOWNLOAD` in the next cell to `True` and run it to download the missing models (existing ones are skipped), then restart ComfyUI or reload the page.
2. Open `dream7_keyframes_edit` and click Run: with K1 as the reference, the car in K0 and K2–K7 becomes K1's car.
3. Check each one: the same car as K1 at the same camera height, with the road, the red car and the grandstands unchanged. If one is off, add a sentence to its instruction or change the KSampler seed and run again.
4. When you are happy, run the cell after next: the edits overwrite the keyframes in `input/`. Then reload the page.

For route A just run the cells below: no models are downloaded and the picker does nothing. The bundled keyframes already have the consistent car and the bundled videos were shot from them; the last cell shows the edit before and after. Outline (in Chinese): `docs/ch4_keyframes.md`.
"""),
    code(EDIT_MODELS_CODE.replace("NOTE", "路线 B 改成 True"), EDIT_MODELS_CODE.replace("NOTE", "set to True for route B")),
    code("""
pick({f"K{i}": f"K{i}_edit_*.png" for i in (0, 2, 3, 4, 5, 6, 7)}, COMFY / "output" / "dream7", COMFY / "input" / "dream7_{}.png")
"""),
    code("""
show(PROJECT / "examples" / "car_edit" / "K1_reference.jpg", width=440)
show(*[PROJECT / "examples" / "car_edit" / f"{k}_{v}.jpg" for k in ("K0", "K2", "K6") for v in ("before", "after")], width=440)
"""),
    md("""
## 第 5 章：逐段拍镜头

第 i 个镜头以 K(i-1) 为首帧、K(i) 为尾帧，交给 MiniMax H3 首尾帧节点生成，提示词只描述“怎么动”。

在浏览器里：

0. 先完成第 4 章（关键帧已经在 `input/` 里），再刷新一次浏览器页面，否则 Load Image 节点会报红。
1. 打开 `dream7_shot_01` 拍镜头 1（试拍），每次 Run 生成 2 个候选：上面一条是 `_t1`，下面一条是 `_t2`。看画风是否满意、开头和结尾是否贴近 K0 和 K1、方向和速度感是否对。
2. 满意后依次打开 `dream7_shot_02` 到 `dream7_shot_07` 并 Run。可以连续提交，任务会排队。
3. 把每个镜头选中的候选编号填进下一格的 `SHOT_TAKES` 并运行，选中的视频会复制为 `output/video/dream7/selected/shot_0X.mp4`。

挑视频时看：转向方向对不对、有没有切镜或倒车、车和机位有没有中途变化、首尾是否贴近关键帧。
路线 A 直接运行下面两格，自带的视频会补上缺的镜头，不会覆盖你选好的文件；下面播放的是自带素材里的镜头 1、2。讲解提纲见 `docs/ch5_shots.md`。
""", """
## Chapter 5: shooting the shots

Shot i goes to the MiniMax H3 first-last-frame node with K(i-1) as the first frame and K(i) as the last frame; the prompt only describes the motion.

In the browser:

0. Finish chapter 4 first (the keyframes are in `input/`), then reload the page once, otherwise the Load Image nodes turn red.
1. Open `dream7_shot_01` for shot 1 (the pilot). Each Run makes 2 takes: the top one is `_t1`, the bottom one `_t2`. Check the style, whether the start and end are close to K0 and K1, and whether the direction and sense of speed are right.
2. When you are happy, open `dream7_shot_02` to `dream7_shot_07` in turn and click Run. You can submit them back to back; the jobs queue.
3. Fill in the take you chose for each shot in `SHOT_TAKES` in the next cell and run it; the chosen videos are copied to `output/video/dream7/selected/shot_0X.mp4`.

What to look for when picking: does it turn the right way, are there cuts or reversing, do the car or camera change midway, are the start and end close to the keyframes.
For route A just run the next two cells; the bundled videos fill in missing shots without overwriting your picks. The players below show shots 1 and 2 from the bundled media. Outline (in Chinese): `docs/ch5_shots.md`.
"""),
    code("""
SHOT_TAKES = {"shot_01": 1, "shot_02": 1, "shot_03": 1, "shot_04": 1, "shot_05": 1, "shot_06": 1, "shot_07": 1}
pick({s: f"{s}_t{t}_*" for s, t in SHOT_TAKES.items()}, COMFY / "output" / "video" / "dream7", COMFY / "output" / "video" / "dream7" / "selected" / "{}.mp4")
"""),
    code("""
for i in range(1, 8):
    copy_missing(MEDIA / f"dream7_shot_0{i}.mp4", COMFY / "output" / "video" / "dream7" / "selected" / f"shot_0{i}.mp4")
play(MEDIA / "dream7_shot_01.mp4", MEDIA / "dream7_shot_02.mp4", width=480)
"""),
    md("""
## 第 6 章：拼接成片，找问题

`stitch_lap.py` 把 7 段按顺序接起来，接缝处做交叉淡化，叠加赛段标题和右下角的小地图（红点按每段的车速移动），再加上片头和片尾。

边看边记录：哪里转向和地图不一致？哪里画面跳变？小地图的红点和画面对得上吗？
把问题按“分镜、关键帧、提示词、拼接”四层归类，正好对应第 3 到 6 章。讲解提纲见 `docs/ch6_problems.md`。
""", """
## Chapter 6: stitch the film and find the problems

`stitch_lap.py` joins the 7 shots in order with crossfades at the seams, overlays sector titles and a minimap in the lower right (the red dot moves at each shot's speed), and adds an intro and an outro. `--en` gives English titles.

While watching, note: where does the steering disagree with the map? Where does the picture jump? Does the minimap's red dot match the picture?
Sort the problems into four layers, storyboard, keyframes, prompts and stitching, which correspond to chapters 3 to 6. Outline (in Chinese): `docs/ch6_problems.md`.
"""),
    code("""
!"{PY}" "{PROJECT}/scripts/stitch_lap.py"
play(PROJECT / "output" / "dream_circuit_7shots.mp4", width=900)
""", """
!"{PY}" "{PROJECT}/scripts/stitch_lap.py" --en
play(PROJECT / "output" / "dream_circuit_7shots_en.mp4", width=900)
"""),
    md("""
## 第 7 章：用分镜修好 T7–T8 减速弯

地图上 T7 是右弯、T8 是左弯，但第 6 章成片的镜头 5 里只有一个左弯，T7 不见了。
下面开始一步步进行修复：每一步先说改了什么、改的是哪一层，再看效果。用到的视频和图片都已经生成好了，直接看就行。
""", """
## Chapter 7: fix the T7–T8 chicane with the storyboard

On the map T7 is a right-hander and T8 a left-hander, but shot 5 of the chapter 6 film shows only one left-hander: T7 is gone.
Now let's fix it step by step: each step says what is changed and in which layer, then shows the result. The videos and images are already generated, so you only need to watch.
"""),
    md("""
### 原来的镜头 5：K4 → K5 一个镜头跑完 T7–T8

K4 是出 T6 的画面，K5 是出减速弯的画面，两张图的朝向只差约 15°。模型从 K4 开到 K5，最省事的路线就是轻轻偏一下，T7 的右转被直接省掉了。

看视频：只有一个左弯。
""", """
### Original shot 5: K4 → K5 drives T7–T8 in one shot

K4 is the view leaving T6 and K5 the view leaving the chicane; their headings differ by only about 15°. Driving from K4 to K5, the easiest path for the model is a slight drift, so the T7 right turn is simply skipped.

Watch: only one left-hander.
"""),
    code("""
play(MEDIA / "dream7_shot_05.mp4", width=480, labels=["原来的镜头 5：只有一个左弯"])
""", """
play(MEDIA / "dream7_shot_05.mp4", width=480, labels=["Original shot 5: only one left-hander"])
"""),
    md("""
### 第 1 步：只改提示词（提示词层，第 5 章）

镜头和关键帧都不变，只在提示词里强调“先右后左”。

看视频：T7 的右弯仍然几乎看不出来。问题出在分镜层时，改提示词没有用。
""", """
### Step 1: change the prompt only (prompt layer, chapter 5)

Shot and keyframes stay the same; the prompt now stresses "right, then left".

Watch: the T7 right-hander is still barely visible. When the problem is in the storyboard, changing the prompt does not help.
"""),
    code("""
play(MEDIA / "chicane_1_prompt_only.mp4", width=480, labels=["只改提示词：T7 右弯仍然看不出来"])
""", """
play(MEDIA / "chicane_1_prompt_only.mp4", width=480, labels=["Prompt only: T7 is still barely visible"])
"""),
    md("""
### 第 2 步：拆成两个镜头（分镜层，第 3 章）

T7 一个镜头、T8 一个镜头，中间新增一张交界关键帧 K5，卡在 T7 出口。这样每个镜头只转一次弯。

看视频：T7 这个镜头一开头先往左转。原因在左边这张旧 K4：短直道尽头画的是一个左弯，模型就往左开。
""", """
### Step 2: split into two shots (storyboard layer, chapter 3)

One shot for T7 and one for T8, with a new boundary keyframe K5 at the T7 exit, so each shot turns only once.

Watch: the T7 shot starts by turning left. The cause is the old K4 on the left: the end of the short straight shows a left-hander, so the model drives left.
"""),
    code("""
show(PROJECT / "examples" / "keyframes" / "dream7_K4.png", width=360, labels=["旧 K4：直道尽头是左弯"])
play(MEDIA / "chicane_2_split.mp4", width=480, labels=["拆分后的 T7 镜头：开头先往左转"])
""", """
show(PROJECT / "examples" / "keyframes" / "dream7_K4.png", width=360, labels=["Old K4: a left-hander at the end of the straight"])
play(MEDIA / "chicane_2_split.mp4", width=480, labels=["T7 shot after the split: starts by turning left"])
"""),
    md("""
### 第 3 步：重画 K4（关键帧层，第 4 章）

重画 K4，让短直道尽头只看到 T7 的右弯。

看视频：开头对了，先往右转。但第一次画的 K5 同时看到右弯和左弯，画面在 1 秒内跳变，像倒回去又看了一遍 T7–T8。
""", """
### Step 3: redraw K4 (keyframe layer, chapter 4)

K4 is redrawn so the end of the short straight shows only the T7 right-hander.

Watch: the start is right now, turning right first. But the first K5 shows both the right- and the left-hander, and the picture jumps within a second, as if replaying T7–T8.
"""),
    code("""
show(PROJECT / "examples" / "keyframes" / "dream8_K4.png", MEDIA / "chicane_K5_first_try.png", width=360, labels=["新 K4：只看到 T7 右弯", "第一次画的 K5：右弯和左弯都在"])
play(MEDIA / "chicane_3_new_K4.mp4", width=480, labels=["新 K4 → 第一次的 K5：1 秒内跳变"])
""", """
show(PROJECT / "examples" / "keyframes" / "dream8_K4.png", MEDIA / "chicane_K5_first_try.png", width=360, labels=["New K4: only the T7 right-hander", "First K5: both the right- and the left-hander"])
play(MEDIA / "chicane_3_new_K4.mp4", width=480, labels=["New K4 → first K5: jumps within a second"])
"""),
    md("""
### 第 4 步：重画 K5（关键帧层，第 4 章）

重画 K5：刚出 T7，前方只看到 T8 的左弯。T8 的镜头用同样的规则：K5 只看到左弯，K6 只看到下坡。

看视频：镜头 5 是完整的 T7 右弯，镜头 6 接着是 T8 左弯，问题解决。
""", """
### Step 4: redraw K5 (keyframe layer, chapter 4)

K5 is redrawn just after T7, with only the T8 left-hander ahead. The T8 shot follows the same rule: K5 shows only the left-hander, K6 only the downhill.

Watch: shot 5 is a full T7 right-hander and shot 6 follows with the T8 left-hander. Fixed.
"""),
    code("""
show(PROJECT / "examples" / "keyframes" / "dream8_K5.png", width=360, labels=["新 K5：只看到 T8 左弯"])
play(MEDIA / "dream8_shot_05.mp4", MEDIA / "dream8_shot_06.mp4", width=480, labels=["新镜头 5（T7）：完整的右弯", "新镜头 6（T8）：左弯"])
""", """
show(PROJECT / "examples" / "keyframes" / "dream8_K5.png", width=360, labels=["New K5: only the T8 left-hander"])
play(MEDIA / "dream8_shot_05.mp4", MEDIA / "dream8_shot_06.mp4", width=480, labels=["New shot 5 (T7): a full right-hander", "New shot 6 (T8): the left-hander"])
"""),
    md("""
### 两条规则

1. **一个镜头只改变一次方向。** 两次转向放进一个镜头，模型会抄近路省掉一次。
2. **交界关键帧只画下一个弯。** 关键帧远端画了什么，模型就往哪里开；画了两个弯，就会在镜头里重复或跳变。
""", """
### Two rules

1. **One change of direction per shot.** Put two turns in one shot and the model cuts the corner, skipping one.
2. **A boundary keyframe shows only the next turn.** The model drives toward whatever the far end of the keyframe shows; show two turns and the shot repeats or jumps.
"""),
    md("""
### 拼出 8 镜头版本

8 镜头分镜表 `storyboards/lap_8shots.json` 只重做 K4、K5 两张关键帧和镜头 4–6，其余关键帧复用第 4 章、镜头复用第 5 章的结果。
原来的镜头 5 拆成了镜头 5（T7）和镜头 6（T8），中间多了 K5，所以后面的编号都往后顺延一位：7 镜头版的 K5、K6、K7 在这里是 K6、K7、K8，原来的镜头 6、7 在这里是镜头 7、8。对照下面的示意图看。
路线 B：在浏览器里打开 `dream8_keyframes` 生成 K4、K5，对照分镜检查（不对就改场景描述再生成），运行下面的挑选格，刷新浏览器页面；再打开 `dream8_keyframes_edit`，以 `dream7_K1.png` 为参考统一 K4、K5 的车，检查后再运行一次挑选格（它取每张关键帧最新的一版，也就是编辑后的），刷新页面。然后打开 `dream8_shot_04` 到 `dream8_shot_06` 生成视频，回来把挑选格里视频的候选编号（`_t1_` 里的 1）改成你选的，再运行一次。
路线 A 直接运行下面几格。最后拼出 8 镜头成片，和第 6 章的版本对比。
""", """
### Stitch the 8-shot version

The 8-shot storyboard `storyboards/lap_8shots.json` redoes only keyframes K4 and K5 and shots 4–6; the other keyframes come from chapter 4 and the other shots from chapter 5.
The old shot 5 is split into shot 5 (T7) and shot 6 (T8) with a new K5 between them, so everything after it shifts by one: the 7-shot K5, K6 and K7 are K6, K7 and K8 here, and the old shots 6 and 7 are shots 7 and 8. Compare with the map below.
Route B: in the browser, open `dream8_keyframes` to generate K4 and K5 and check them against the storyboard (if one is wrong, edit its scene description and generate again), run the picker cell below and reload the page. Next open `dream8_keyframes_edit` to make the car in K4 and K5 match `dream7_K1.png`, check them, run the picker cell again (it takes the newest version of each keyframe, which is the edit) and reload the page. Then open `dream8_shot_04` to `dream8_shot_06` to generate the videos, come back, change the video take number in the picker cell (the 1 in `_t1_`) to the ones you chose, and run it again.
For route A just run the cells below. At the end you stitch the 8-shot film and compare it with the chapter 6 version.
"""),
    code("""
show(PROJECT / "assets" / "storyboard_map_8shots.png", width=1000)
""", """
show(PROJECT / "assets" / "storyboard_map_8shots_en.png", width=1000)
"""),
    code("""
pick({k: f"{k}_*.png" for k in ("K4", "K5")}, COMFY / "output" / "dream8", COMFY / "input" / "dream8_{}.png")
pick({s: f"{s}_t1_*" for s in ("shot_04", "shot_05", "shot_06")}, COMFY / "output" / "video" / "dream8", COMFY / "output" / "video" / "dream8" / "selected" / "{}.mp4")
"""),
    code("""
for k in ("K4", "K5"):
    copy_missing(PROJECT / "examples" / "keyframes" / f"dream8_{k}.png", COMFY / "input" / f"dream8_{k}.png")
for i in (4, 5, 6):
    copy_missing(MEDIA / f"dream8_shot_0{i}.mp4", COMFY / "output" / "video" / "dream8" / "selected" / f"shot_0{i}.mp4")
"""),
    code("""
!"{PY}" "{PROJECT}/scripts/stitch_lap.py" --shots lap_8shots.json
play(PROJECT / "output" / "dream_circuit_8shots.mp4", width=900)
""", """
!"{PY}" "{PROJECT}/scripts/stitch_lap.py" --shots lap_8shots.json --en
play(PROJECT / "output" / "dream_circuit_8shots_en.mp4", width=900)
"""),
    md("""
## 第 8 章：总结和练习

- 单个提示词适合一个动作，不适合一整圈；把任务拆成镜头，每个镜头只做一件事。
- 关键帧是镜头之间的“合同”：它画了什么，模型就会往哪里开。
- 出问题先归类（分镜、关键帧、提示词、拼接），再到对应的那一层修。

练习：成片里下坡直道和 T9 的衔接还有问题（直道没跑完就切进了 T9）。用同样的方法拆分镜头 7，重画交界关键帧，拼出你的版本。讲解提纲见 `docs/ch8_wrapup.md`。
""", """
## Chapter 8: wrap-up and exercise

- One prompt suits one action, not a whole lap; split the task into shots, each doing one thing.
- Keyframes are the contract between shots: the model drives toward whatever they show.
- When something goes wrong, classify it first (storyboard, keyframes, prompts, stitching), then fix it in that layer.

Exercise: the film still has a problem where the downhill straight meets T9 (it cuts into T9 before the straight ends). Use the same method to split shot 7, redraw the boundary keyframe, and stitch your own version. Outline (in Chinese): `docs/ch8_wrapup.md`.
"""),
]

STOP = [
    md("""
## 结束

用完后停止 ComfyUI 和隧道，公开 URL 随之失效。
""", """
## Finish

When you are done, stop ComfyUI and the tunnel; the public URL stops working.
"""),
    code("""
!bash "{PROJECT}/scripts/start_comfyui_cloud.sh" stop
"""),
]

if __name__ == "__main__":
    for en, suffix in ((False, ""), (True, "_en")):
        for name, cells in (("local", LOCAL + CHAPTERS), ("cloud", CLOUD + CHAPTERS + STOP)):
            out = os.path.join(common.PROJECT, "notebooks", f"{name}{suffix}.ipynb")
            json.dump(notebook(cells, en), open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print("wrote", out)
