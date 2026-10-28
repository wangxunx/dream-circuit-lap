# 梦幻赛道 · 第一人称一圈（8 个镜头）：分镜与生成手册（lap_8shots.json）

8 个镜头，一圈约 54 秒；加上片头、片尾和接缝处的交叉淡化，成片约 58 秒。
本文件由 `scripts/make_workflows.py` 根据 `storyboards/lap_8shots.json` 生成。要改提示词或时长，请改 `lap_8shots.json` 后重新运行脚本，不要直接改本文件。

下文的 `input/`、`output/`、`user/` 都指 ComfyUI 目录下的文件夹；`scripts/`、`workflows/`、`examples/` 指本课程目录下的文件夹。

## 整体流程

1. 关键帧：用 Qwen Image 2.1 为每个镜头的交界处生成一张车手视角图片，K0 到 K8 共 9 张。
2. 视频：第 i 个镜头用 K(i-1) 作首帧、K(i) 作尾帧，交给 MiniMax H3 首尾帧节点生成。相邻镜头共用交界帧，所以能接上。
3. 拼接：`stitch_lap.py` 把 8 段按顺序接起来，接缝处做交叉淡化，叠加赛段标题和右下角的小地图，再加上片头和片尾。

## 复用的素材

下面这些不用重新生成：

- K0（起点：停在起终点线上）：复用 `input/dream7_K0.png`
- K1（直道尽头：刹车点前）：复用 `input/dream7_K1.png`
- K2（出 T2：前方开始爬坡）：复用 `input/dream7_K2.png`
- K3（T5 坡顶：前方大半径左弯）：复用 `input/dream7_K3.png`
- K6（出减速弯：前方长下坡）：复用 `input/dream7_K5.png`
- K7（出 T9：前方中速右弯）：复用 `input/dream7_K6.png`
- K8（终点：冲过起终点线）：复用 `input/dream7_K7.png`
- 镜头 1（起终点直道）：复用 `output/video/dream7/selected/shot_01.mp4`
- 镜头 2（重刹弯 T1–T2）：复用 `output/video/dream7/selected/shot_02.mp4`
- 镜头 3（爬坡弯组 T3–T5）：复用 `output/video/dream7/selected/shot_03.mp4`
- 镜头 7（下坡弯 T9）：复用 `output/video/dream7/selected/shot_06.mp4`
- 镜头 8（最后赛段 T10–T11）：复用 `output/video/dream7/selected/shot_07.mp4`

## 准备

- 在 ComfyUI 的 `custom_nodes/` 里安装 [ComfyUI-AMD-Qwen-Image-2.1](https://github.com/wangxunx/ComfyUI-AMD-Qwen-Image-2.1) 和 [ComfyUI-AMD-MiniMaxH3](https://github.com/wangxunx/ComfyUI-AMD-MiniMaxH3)。
- 启动 ComfyUI，并确认 `H3_GATEWAY_API_KEY` 已配置（或 `user/h3_gateway_api_key.txt` 存在）。
- 工作流在 `workflows/`，可以直接拖进 ComfyUI 打开。运行过 `make_workflows.py --install` 的话，ComfyUI 左侧 **工作流** 面板里能直接看到以 `dream8_` 开头的条目。
- 额度估算：关键帧每张 1 个额度（30 步）；视频按网关计费。全部生成一遍约为 6 张图加 6 段视频。

## 第 1 步：生成新关键帧

打开 `dream8_keyframes`，点运行。挑选时重点看：

- 镜头高度和构图一致（halo 防护杆、座舱顶部在画面底部的位置差不多）。
- 赛车外观一致。
- 前方路面的走向和分镜一致：该左转的图里，路就要往左弯。

### 挑选与复制

关键帧输出在 `output/dream8/`，挑好后复制进 `input/`，文件名必须和镜头工作流里的一致：

```bash
cd /path/to/ComfyUI
cp output/dream8/K4_t1_00001_.png input/dream8_K4.png   # 把 t1 换成你选的候选
cp output/dream8/K5_t1_00001_.png input/dream8_K5.png   # 把 t1 换成你选的候选
```

想跳过这一步、直接试视频的话，可以把课程自带的关键帧复制进去：`cp examples/keyframes/dream8_*.png /path/to/ComfyUI/input/`。

## 第 2 步：逐段生成视频

依次打开 `dream8_shot_04` 到 `dream8_shot_06`，每个点一次运行，会生成 2 条候选。选好的那条复制为 `output/video/dream8/selected/shot_0X.mp4`（每个工作流左侧的说明里有现成命令）。

## 第 3 步：逐段检查

- 转向方向是否和分镜一致（最常见的错误）。
- 有没有突然切镜、画面倒放或倒车。
- 赛车和镜头位置有没有中途变化。
- 开头和结尾两帧是否贴近关键帧，否则拼接处会跳。

## 第 4 步：拼接成片

在课程目录下运行（ComfyUI 不在上一级目录时，加 `--comfyui /path/to/ComfyUI` 或设置 `COMFYUI_DIR`）：

```bash
python scripts/stitch_lap.py --shots lap_8shots.json        # 中文版
python scripts/stitch_lap.py --shots lap_8shots.json --en   # 英文版
```

脚本读取 ComfyUI 的 `output/video/dream8/selected/shot_0X.mp4`；某个镜头没有 selected 文件时，会用 `output/video/dream8/` 里该镜头最新的一条。复用的镜头直接读取分镜文件里 `clip` 指定的视频。成片写到课程目录的 `output/dream_circuit_8shots.mp4`，英文版是 `output/dream_circuit_8shots_en.mp4`。

还没生成任何视频时，可以加 `--placeholder` 先预览节奏、标题和小地图：缺失的镜头会用关键帧（如果有）或占位画面代替。

## 每个镜头的分镜

### 镜头 1：起终点直道（8 秒）

- 首帧 / 尾帧：K0（起点：停在起终点线上）→ K1（直道尽头：刹车点前）
- 来源：复用 `output/video/dream7/selected/shot_01.mp4`，不用重新生成
- 弯道：无弯，全圈最长直道
- 海拔：12 m → 9 m，略下坡
- 速度：0 → 约 320 km/h

视频提示词（只描述“怎么动”，后面会自动接上统一规则和风格设定）：

```text
The start lights go out and the car launches from the grid, accelerating hard down the long, slightly downhill straight. It tucks into the slipstream of the red car ahead and edges slightly left out of the tow as the speed builds to about 320 km/h. The grandstand on the right streaks past and the braking boards rush towards the camera at the end of the straight.
```

### 镜头 2：重刹弯 T1–T2（6 秒）

- 首帧 / 尾帧：K1（直道尽头：刹车点前）→ K2（出 T2：前方开始爬坡）
- 来源：复用 `output/video/dream7/selected/shot_02.mp4`，不用重新生成
- 弯道：T1 左 105° 发夹弯 · T2 右侧小弯
- 海拔：9 m → 13 m，T1 处为全圈最低点 8 m
- 速度：约 320 → 85 km/h

视频提示词（只描述“怎么动”，后面会自动接上统一规则和风格设定）：

```text
Very late, very heavy braking from top speed: the nose dips hard and the car dives down the inside, to the LEFT of the red car, and overtakes it under braking. The road turns sharply LEFT through a tight hairpin, then a quick short flick to the RIGHT, and the car accelerates away as the road begins to rise.
```

### 镜头 3：爬坡弯组 T3–T5（8 秒）

- 首帧 / 尾帧：K2（出 T2：前方开始爬坡）→ K3（T5 坡顶：前方大半径左弯）
- 来源：复用 `output/video/dream7/selected/shot_03.mp4`，不用重新生成
- 弯道：T3 左 · T4 右 · T5 左（坡顶）
- 海拔：13 m → 33 m，从 T1 谷底算起爬升约 24 m
- 速度：带速通过，约 200–250 km/h

视频提示词（只描述“怎么动”，后面会自动接上统一规则和风格设定）：

```text
Climbing the steep hill at speed through linked bends: a LEFT, then a RIGHT, then a LEFT, flowing one into the next without lifting off. Compression at the bottom of the climb, the horizon tilting with each change of direction, and the car goes light over the blind crest at the top as the sky fills the upper frame.
```

### 镜头 4：高速弯 T6 与短直道（7 秒）

- 首帧 / 尾帧：K3（T5 坡顶：前方大半径左弯）→ K4（短直道尽头：T7 右弯刹车点）
- 弯道：T6 左 约 100° 长弯，接约 300 m 短直道
- 海拔：33 m → 42 m，全圈最高点
- 速度：近乎全油门，约 260 → 300 km/h

视频提示词（只描述“怎么动”，后面会自动接上统一规则和风格设定）：

```text
Flat out through a long, wide, smooth LEFT-hand sweeping curve on the highest part of the circuit. The car holds one constant arc and the scenery sweeps steadily from left to right across the frame, with a panoramic valley view on the right. Calm, fast and smooth, no sharp steering. Over the last few seconds the curve straightens onto a short, dead-straight straight and the car runs flat out towards a sharp RIGHT-hand corner at its end.
```

### 镜头 5：减速弯 T7（右）（5 秒）

- 首帧 / 尾帧：K4（短直道尽头：T7 右弯刹车点）→ K5（出 T7：前方 T8 急左弯）
- 弯道：T7 右 约 70°，减速弯前半
- 海拔：42 m → 41 m
- 速度：约 300 → 95 km/h

视频提示词（只描述“怎么动”，后面会自动接上统一规则和风格设定）：

```text
Hard braking at the end of the short straight, the nose dipping hard as the speed falls from about 300 to 95 km/h; the road stays straight while braking, with no left turn before the corner. Then the driver turns the steering wheel hard to the RIGHT and the car turns sharply RIGHT through a tight corner of about seventy degrees, clipping the red-and-white kerb on the inside right. The view rotates far to the right and the whole scenery swings steadily to the left across the frame, so that the road the car was on disappears off the left edge. The shot ends just out of this right-hander, with a tight left-hand corner close ahead. Only one turn in this shot, and it is to the RIGHT.
```

### 镜头 6：减速弯 T8（左）（5 秒）

- 首帧 / 尾帧：K5（出 T7：前方 T8 急左弯）→ K6（出减速弯：前方长下坡）
- 弯道：T8 左 约 90°，减速弯后半
- 海拔：41 m → 40 m
- 速度：约 95 → 120 km/h，全圈最慢的一段

视频提示词（只描述“怎么动”，后面会自动接上统一规则和风格设定）：

```text
At low speed, just out of a right-hand corner, the car turns sharply LEFT through a tight corner of almost ninety degrees, bouncing over the tall red-and-white kerb on the inside left, the view rotating to the left and the scenery swinging to the right across the frame. The exit of this left-hander is right on the crest of the hill: as the car turns, the long downhill straight swings into view from the left, and as the driver unwinds the steering the road ahead becomes one dead-straight line dropping steeply down the hillside, with the valley opening up below. After the left turn there are no more corners and no right-hand bend; the car simply accelerates straight down the hill, the view tilting smoothly downwards as it goes over the crest.
```

### 镜头 7：下坡弯 T9（7 秒）

- 首帧 / 尾帧：K6（出减速弯：前方长下坡）→ K7（出 T9：前方中速右弯）
- 来源：复用 `output/video/dream7/selected/shot_06.mp4`，不用重新生成
- 弯道：T9 左，中速
- 海拔：40 m → 17 m，下降约 25 m
- 速度：约 260 → 150 km/h

视频提示词（只描述“怎么动”，后面会自动接上统一规则和风格设定）：

```text
Accelerating down a long, steep downhill straight, the horizon low and the valley opening up ahead. Braking while still going downhill, the nose dips, and the car turns into a medium-speed LEFT-hand corner at the bottom of the slope, then straightens onto flat ground.
```

### 镜头 8：最后赛段 T10–T11（8 秒）

- 首帧 / 尾帧：K7（出 T9：前方中速右弯）→ K8（终点：冲过起终点线）
- 来源：复用 `output/video/dream7/selected/shot_07.mp4`，不用重新生成
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

### K4：短直道尽头：T7 右弯刹车点

```text
On a short, dead-straight, level straight on high ground, at the braking point about one hundred metres before a tight corner. The road runs straight ahead and then turns sharply to the RIGHT: at the far end the left-hand white edge line and a blue barrier wall sweep across the view from left to right, and a red-and-white kerb marks the inside of the corner on the right-hand side. After that corner the track disappears out of sight to the right; no left-hand bend is visible anywhere ahead. Open sky, hills in the distance.
```

### K5：出 T7：前方 T8 急左弯

```text
At low speed on high ground, the car points straight down a very short straight. Only about forty metres ahead the road turns sharply to the LEFT: at the far end the right-hand white edge line and a blue barrier wall sweep across the view from right to left, and a tall red-and-white kerb marks the inside of the corner on the left-hand side. Beyond that corner the ground falls away out of sight. Both road edges between the car and the corner are straight; no right-hand bend is visible anywhere ahead. Open sky, hills in the distance.
```

### K6：出减速弯：前方长下坡

```text
Just after a tight chicane, the track drops away ahead into a long straight that descends diagonally down the hillside. The valley and distant hills lie below, the horizon sits low in the frame. Far down at the bottom of the slope the road bends LEFT.
```

### K7：出 T9：前方中速右弯

```text
On flat ground at the bottom of a hill, just after a left-hand corner, on a short straight. Ahead a medium-speed RIGHT-hand bend with a red-and-white kerb on the right side, then the road continues out of sight. Trees and grass on both sides.
```

### K8：终点：冲过起终点线

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
