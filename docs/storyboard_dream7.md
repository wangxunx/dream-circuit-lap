# 梦幻赛道 · 第一人称一圈（7 个镜头）：分镜与生成手册（lap_7shots.json）

7 个镜头，一圈约 51 秒；加上片头、片尾和接缝处的交叉淡化，成片约 56 秒。
本文件由 `scripts/make_workflows.py` 根据 `storyboards/lap_7shots.json` 生成。要改提示词或时长，请改 `lap_7shots.json` 后重新运行脚本，不要直接改本文件。

下文的 `input/`、`output/`、`user/` 都指 ComfyUI 目录下的文件夹；`scripts/`、`workflows/`、`examples/` 指本项目目录下的文件夹。

## 整体流程

1. 关键帧：用 Qwen Image 2.1 为每个镜头的交界处生成一张车手视角图片，K0 到 K7 共 8 张。
2. 视频：第 i 个镜头用 K(i-1) 作首帧、K(i) 作尾帧，交给 MiniMax H3 首尾帧节点生成。相邻镜头共用交界帧，所以能接上。
3. 拼接：`stitch_lap.py` 把 7 段按顺序接起来，接缝处做交叉淡化，叠加赛段标题和右下角的小地图，再加上片头和片尾。

## 准备

- 在 ComfyUI 的 `custom_nodes/` 里安装 [ComfyUI-AMD-Qwen-Image-2.1](https://github.com/wangxunx/ComfyUI-AMD-Qwen-Image-2.1) 和 [ComfyUI-AMD-MiniMaxH3](https://github.com/wangxunx/ComfyUI-AMD-MiniMaxH3)。
- 启动 ComfyUI，并确认 `H3_GATEWAY_API_KEY` 已配置（或 `user/h3_gateway_api_key.txt` 存在）。
- 工作流在 `workflows/`，可以直接拖进 ComfyUI 打开。运行过 `make_workflows.py --install` 的话，ComfyUI 左侧 **工作流** 面板里能直接看到以 `dream7_` 开头的条目。
- 额度估算：关键帧每张 1 个额度（30 步），视频按网关计费。全部生成一遍约为 8 张图（每改一次多 1 张）加 14 段视频。
- 统一车身的编辑用本地 Qwen Image 2.1 模型，不花额度，但需要本机 GPU 和约 17 GB 的模型文件（见下面“统一车身和灯架”）。

## 第 1 步：试拍（强烈建议先做）

1. 打开 `dream7_keyframes_pilot`，点运行，只生成 K0 和 K1。
2. 对照分镜检查（见下一步），定稿后复制为 `input/dream7_K0.png` 和 `input/dream7_K1.png`（命令见下面“复制到 input”）。
3. 打开 `dream7_keyframes_edit_pilot`，点运行，把 K1 的车统一成 K0 那辆，检查后覆盖 `input/dream7_K1.png`（见下面“统一车身和灯架”）。
4. 打开 `dream7_shot_01`，点运行。看三件事：画风是否满意；视频开头和结尾是否贴近两张关键帧；速度感和方向是否对。
5. 满意了再继续。不满意就先改 `lap_7shots.json` 里的 `style`、`scene` 或 `motion`，重新运行 `make_workflows.py`，再重拍。

## 第 2 步：生成全部关键帧

打开 `dream7_keyframes`，点运行，每张关键帧生成 1 张图。逐张对照下面“关键帧画面”和小地图检查：

- 前方路面的走向和分镜一致：该左转的图里，路就要往左弯；远端只该有一个弯时，不能画出两个。
- 距离和比例对得上：直道有多长、离弯道多远。
- 画面里该有的东西都在，比如起终点的灯架、看台、红车。
- 镜头高度、构图和赛车外观与其他关键帧一致。

不对就在工作流里改这张图提示词开头的场景描述（`Photorealistic onboard` 之前的部分），再点运行，ComfyUI 只会重新生成改过的那张（ComfyUI 重启过的话会全部重新生成，可以先选中不用重做的 Save Image 节点按 Ctrl+M 静音）。节点没有随机种子，提示词不变时重新生成也是同一张图，所以要改的是描述，不是多生成几次。满意后把新的场景描述写回 `lap_7shots.json` 的 `keyframes[].scene`，否则下次重新运行 `make_workflows.py --install` 时会被覆盖。

### 复制到 input

关键帧输出在 `output/dream7/`，每重新生成一次编号加 1。把定稿的那一张复制进 `input/`，文件名必须和镜头工作流里的一致：

```bash
cd /path/to/ComfyUI
cp output/dream7/K0_00001_.png input/dream7_K0.png   # 00001 换成你定稿的那一版
cp output/dream7/K1_00001_.png input/dream7_K1.png   # 00001 换成你定稿的那一版
cp output/dream7/K2_00001_.png input/dream7_K2.png   # 00001 换成你定稿的那一版
cp output/dream7/K3_00001_.png input/dream7_K3.png   # 00001 换成你定稿的那一版
cp output/dream7/K4_00001_.png input/dream7_K4.png   # 00001 换成你定稿的那一版
cp output/dream7/K5_00001_.png input/dream7_K5.png   # 00001 换成你定稿的那一版
cp output/dream7/K6_00001_.png input/dream7_K6.png   # 00001 换成你定稿的那一版
cp output/dream7/K7_00001_.png input/dream7_K7.png   # 00001 换成你定稿的那一版
```

想跳过这一步、直接试视频的话，可以把项目自带的关键帧复制进去：`cp examples/keyframes/dream7_*.png /path/to/ComfyUI/input/`。

## 第 3 步：统一车身和灯架

文生图的每张关键帧各画各的车：halo 顶上的部件、车身颜色、机位高低都可能不同。同一个镜头的首尾帧如果是两辆车，视频中途就会换车，相邻镜头又共用关键帧，所以要在拍镜头之前把所有关键帧统一成同一辆车。

打开 `dream7_keyframes_edit`，点运行：以 `input/dream7_K0.png` 为参考图，把 K1、K2、K3、K4、K5、K6、K7 里的车改成和 K0 一致；K7 还会把起跑灯架改成和 K0 一样、灯全部熄灭。结果在 `output/dream7/K1_edit_00001_.png` 这样的文件里。

这一步用本地 Qwen Image 2.1 模型，不花额度：网关的图像编辑在 16:9 下会把整张图弄出颗粒和过度锐化。需要以下模型（约 17 GB），缺的话打开工作流时 ComfyUI 会提示下载，也可以手动下载：

```bash
cd /path/to/ComfyUI
wget -P models/diffusion_models https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/diffusion_models/qwen_image_2.1_int8_convrot.safetensors
wget -P models/text_encoders https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/text_encoders/qwen3vl_8b_int8_convrot.safetensors
wget -P models/vae https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/vae/qwen_image_2.1_vae_bf16.safetensors
```

检查车和参考图是同一辆、机位高度一致，路面、弯道、红车、看台这些场景内容没被改掉。不满意就补一句编辑指令或换一个 KSampler 的 seed 再运行。满意后覆盖 input 里的关键帧：

```bash
cd /path/to/ComfyUI
cp output/dream7/K1_edit_00001_.png input/dream7_K1.png
cp output/dream7/K2_edit_00001_.png input/dream7_K2.png
cp output/dream7/K3_edit_00001_.png input/dream7_K3.png
cp output/dream7/K4_edit_00001_.png input/dream7_K4.png
cp output/dream7/K5_edit_00001_.png input/dream7_K5.png
cp output/dream7/K6_edit_00001_.png input/dream7_K6.png
cp output/dream7/K7_edit_00001_.png input/dream7_K7.png
```

编辑指令在 `lap_7shots.json` 的 `keyframe.match`，灯架那一句在对应关键帧的 `match`。

## 第 4 步：逐段生成视频

依次打开 `dream7_shot_01` 到 `dream7_shot_07`，每个点一次运行，会生成 2 条候选。选好的那条复制为 `output/video/dream7/selected/shot_0X.mp4`（每个工作流左侧的说明里有现成命令）。

## 第 5 步：逐段检查

- 转向方向是否和分镜一致（最常见的错误）。
- 有没有突然切镜、画面倒放或倒车。
- 赛车和镜头位置有没有中途变化。
- 开头和结尾两帧是否贴近关键帧，否则拼接处会跳。

## 第 6 步：拼接成片

在本项目目录下运行（ComfyUI 不在上一级目录时，加 `--comfyui /path/to/ComfyUI` 或设置 `COMFYUI_DIR`）：

```bash
python scripts/stitch_lap.py        # 中文版
python scripts/stitch_lap.py --en   # 英文版
```

脚本读取 ComfyUI 的 `output/video/dream7/selected/shot_0X.mp4`；某个镜头没有 selected 文件时，会用 `output/video/dream7/` 里该镜头最新的一条。成片写到本项目目录的 `output/dream_circuit_7shots.mp4`，英文版是 `output/dream_circuit_7shots_en.mp4`。

还没生成任何视频时，可以加 `--placeholder` 先预览节奏、标题和小地图：缺失的镜头会用关键帧（如果有）或占位画面代替。

## 每个镜头的分镜

### 镜头 1：起终点直道（8 秒）

- 首帧 / 尾帧：K0（起点：停在起终点线上）→ K1（直道尽头：刹车点前）
- 弯道：无弯，全圈最长直道
- 海拔：12 m → 9 m，略下坡
- 速度：0 → 约 320 km/h

视频提示词（只描述“怎么动”，后面会自动接上统一规则和风格设定）：

```text
The start lights go out and the car launches from the grid, accelerating hard down the long, slightly downhill straight. It tucks into the slipstream of the red car ahead and edges slightly left out of the tow as the speed builds to about 320 km/h. The grandstand on the right streaks past and the braking boards rush towards the camera at the end of the straight.
```

### 镜头 2：重刹弯 T1–T2（6 秒）

- 首帧 / 尾帧：K1（直道尽头：刹车点前）→ K2（出 T2：前方开始爬坡）
- 弯道：T1 左 105° 发夹弯 · T2 右侧小弯
- 海拔：9 m → 13 m，T1 处为全圈最低点 8 m
- 速度：约 320 → 85 km/h

视频提示词（只描述“怎么动”，后面会自动接上统一规则和风格设定）：

```text
Very late, very heavy braking from top speed: the nose dips hard and the car dives down the inside, to the LEFT of the red car, and overtakes it under braking. The road turns sharply LEFT through a tight hairpin, then a quick short flick to the RIGHT, and the car accelerates away as the road begins to rise.
```

### 镜头 3：爬坡弯组 T3–T5（8 秒）

- 首帧 / 尾帧：K2（出 T2：前方开始爬坡）→ K3（T5 坡顶：前方大半径左弯）
- 弯道：T3 左 · T4 右 · T5 左（坡顶）
- 海拔：13 m → 33 m，从 T1 谷底算起爬升约 24 m
- 速度：带速通过，约 200–250 km/h

视频提示词（只描述“怎么动”，后面会自动接上统一规则和风格设定）：

```text
Climbing the steep hill at speed through linked bends: a LEFT, then a RIGHT, then a LEFT, flowing one into the next without lifting off. Compression at the bottom of the climb, the horizon tilting with each change of direction, and the car goes light over the blind crest at the top as the sky fills the upper frame.
```

### 镜头 4：高速大半径弯 T6（7 秒）

- 首帧 / 尾帧：K3（T5 坡顶：前方大半径左弯）→ K4（出 T6：短直道与减速弯）
- 弯道：T6 左 约 100° 长弯，半径约 320 m
- 海拔：33 m → 42 m，全圈最高点
- 速度：近乎全油门，约 260–280 km/h

视频提示词（只描述“怎么动”，后面会自动接上统一规则和风格设定）：

```text
Flat out through a long, wide, smooth LEFT-hand sweeping curve on the highest part of the circuit. The car holds one constant arc and the scenery sweeps steadily from left to right across the frame, with a panoramic valley view on the right. Calm, fast and smooth, no sharp steering.
```

### 镜头 5：短直道与减速弯 T7–T8（7 秒）

- 首帧 / 尾帧：K4（出 T6：短直道与减速弯）→ K5（出减速弯：前方长下坡）
- 弯道：T7 右 · T8 左（S 形减速弯）
- 海拔：42 m → 40 m
- 速度：约 250 → 90 km/h，全圈最慢

视频提示词（只描述“怎么动”，后面会自动接上统一规则和风格设定）：

```text
A short burst of acceleration along the short straight, then hard braking into a tight chicane: a sharp flick to the RIGHT immediately followed by a sharp flick to the LEFT, the car bouncing over the red-and-white kerbs. The slowest, most technical moment of the lap, then the car straightens up and accelerates.
```

### 镜头 6：下坡弯 T9（7 秒）

- 首帧 / 尾帧：K5（出减速弯：前方长下坡）→ K6（出 T9：前方中速右弯）
- 弯道：T9 左，中速
- 海拔：40 m → 17 m，下降约 25 m
- 速度：约 260 → 150 km/h

视频提示词（只描述“怎么动”，后面会自动接上统一规则和风格设定）：

```text
Accelerating down a long, steep downhill straight, the horizon low and the valley opening up ahead. Braking while still going downhill, the nose dips, and the car turns into a medium-speed LEFT-hand corner at the bottom of the slope, then straightens onto flat ground.
```

### 镜头 7：最后赛段 T10–T11（8 秒）

- 首帧 / 尾帧：K6（出 T9：前方中速右弯）→ K7（终点：冲过起终点线）
- 弯道：T10 右，中速 · T11 左，流畅长弯
- 海拔：17 m → 12 m
- 速度：约 160 → 280 km/h

视频提示词（只描述“怎么动”，后面会自动接上统一规则和风格设定）：

```text
A medium-speed RIGHT-hand bend, then a long flowing LEFT-hand curve that opens onto the main straight. The driver unwinds the steering and goes full throttle; the start/finish line, the light gantry and the grandstand on the right come into view, and the car flashes across the line.
```

## 关键帧画面

### K0：起点：停在起终点线上

```text
The car is stationary on the starting grid, sitting exactly on the chequered start/finish line painted across a long, wide straight. A start light gantry with five red lights spans the track overhead ahead. On the right side a large covered grandstand packed with spectators and a pit building with a pit wall. A red race car waits on the grid a few metres ahead, slightly to the right. The straight runs far ahead to the vanishing point, slightly downhill.
```

### K1：直道尽头：刹车点前

```text
Travelling at about 320 km/h at the far end of a long straight, strong motion blur on the verges. Three white braking marker boards stand on the right verge. Just ahead the track turns sharply LEFT into a tight hairpin with a red-and-white kerb on the inside left. The red race car is directly ahead, slightly to the right, a few car lengths away.
```

### K2：出 T2：前方开始爬坡

```text
Accelerating out of a corner; the red car is no longer in view. The road ahead starts to climb a steep green hillside and snakes LEFT, then RIGHT, then LEFT up the slope, with red-and-white kerbs on each apex. The horizon is high in the frame because of the climb.
```

### K3：T5 坡顶：前方大半径左弯

```text
At high speed right on the crest of a hill; the road levels out on high ground and opens into a wide, long LEFT-hand sweeping curve. Big sky, panoramic view over a green valley on the right side, distant hills on the horizon.
```

### K4：出 T6：短直道与减速弯

```text
Exiting a long fast left-hand curve onto a short straight on high ground. Ahead a tight chicane: the track kinks sharply RIGHT then immediately LEFT, marked by tall red-and-white kerbs. Open sky, hills in the distance.
```

### K5：出减速弯：前方长下坡

```text
Just after a tight chicane, the track drops away ahead into a long straight that descends diagonally down the hillside. The valley and distant hills lie below, the horizon sits low in the frame. Far down at the bottom of the slope the road bends LEFT.
```

### K6：出 T9：前方中速右弯

```text
On flat ground at the bottom of a hill, just after a left-hand corner, on a short straight. Ahead a medium-speed RIGHT-hand bend with a red-and-white kerb on the right side, then the road continues out of sight. Trees and grass on both sides.
```

### K7：终点：冲过起终点线

```text
Flashing across the chequered start/finish line at high speed on the long main straight. The start light gantry passes overhead with its lights off. The large covered grandstand packed with spectators and the pit wall stream past on the right side, motion blur on the edges.
```

## 统一风格设定（自动附加在每条提示词后面）

```text
Photorealistic onboard racing footage filmed by a T-cam mounted just above and behind the driver's helmet of a dark-blue open-wheel single-seater race car with a white nose. Only the halo safety bar, the top of the cockpit and the front wing tips are visible at the bottom of the frame; the camera height and framing never change. Sunny afternoon, clear blue sky, warm consistent sunlight. Grey asphalt circuit with white edge lines, red-and-white striped kerbs on every corner, green grass run-off, blue barrier walls, rolling green hills and scattered trees in the distance. Cinematic, sharp, natural colours, 16:9. No on-screen text, no logos, no watermark.
```

视频额外附加：

```text
Single continuous take from the same onboard camera, no cuts, no camera switch, the car always moves forward and never reverses, no on-screen text, no watermark.
```
