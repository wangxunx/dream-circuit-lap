# 开上你的梦幻赛道：用 AI 分镜跑完一圈

[English](README.md)

手里有一张自己设计的赛道俯视图，怎么生成一段车手第一视角的视频，把它完整跑一圈？

这门课从最直接的办法（一个提示词）开始，一步步引入分镜、关键帧和逐段生成，拼出约 1 分钟、带赛段标题和小地图的成片，再用分镜修好其中最难的减速弯。所有生成都在 ComfyUI 里完成：关键帧用 Qwen Image 2.1，视频用 MiniMax H3 首尾帧，两者都在云端推理，本机不需要 GPU。

课程素材来自 [f1_circuit](https://github.com/wangxunx/f1_circuit) 项目的真实迭代过程，每一步都附有当时实际生成的结果，不花额度也能跟完全程。

## 章节

| 章节 | 内容 | 讲解提纲 | 消耗额度 |
|---|---|---|---|
| 1 | 认识赛道地图，提出任务 | [ch1_map](docs/ch1_map.md) | 无 |
| 2 | 一个提示词直接生成：15 秒、跑不完、不可控 | [ch2_single_prompt](docs/ch2_single_prompt.md) | 每次 1 段视频（可选） |
| 3 | 分镜：把一圈拆成 7 个镜头 | [ch3_storyboard](docs/ch3_storyboard.md) | 无 |
| 4 | 关键帧：每个镜头交界处一张车手视角图 | [ch4_keyframes](docs/ch4_keyframes.md) | 最多 24 张图（可选） |
| 5 | 逐段拍镜头：首尾帧生成视频 | [ch5_shots](docs/ch5_shots.md) | 最多 14 段视频（可选） |
| 6 | 拼接成片，找问题 | [ch6_problems](docs/ch6_problems.md) | 无 |
| 7 | 用分镜修好 T7–T8 减速弯 | [ch7_chicane](docs/ch7_chicane.md) | 6 张图 + 6 段视频（可选） |
| 8 | 总结和作业 | [ch8_wrapup](docs/ch8_wrapup.md) | 作业按需 |

关键帧每张 1 个额度（30 步）；视频按 H3 网关计费。

## 运行方式

两个 notebook 内容相同，都负责：安装两个节点、配置 H3 key、启动 ComfyUI、下载课程素材、安装各章工作流、拼接成片。生成图片和视频在浏览器里的 ComfyUI 完成。请在 JupyterLab / JupyterHub 里打开，notebook 里的视频才能播放。

### 本地：`notebooks/local.ipynb`

把本仓库克隆到 ComfyUI 目录里，例如 `ComfyUI/dream-circuit-lap`，然后用 ComfyUI 的 Python 环境启动 JupyterLab：

```bash
cd /path/to/ComfyUI
git clone https://github.com/wangxunx/dream-circuit-lap.git
cd dream-circuit-lap
pip install jupyterlab -r requirements.txt
jupyter lab notebooks/local.ipynb
```

ComfyUI 不在上一级目录时，设置环境变量 `COMFYUI_DIR`。

### 云端：`notebooks/cloud.ipynb`

适用于预装 ComfyUI 的 JupyterLab / JupyterHub 实例（默认 `/comfyui_workspace/ComfyUI`，可用 `COMFY_DIR` 修改）。`scripts/start_comfyui_cloud.sh` 以 `--cpu` 在后台启动 ComfyUI，打印访问地址后返回：

- AMD Instinct 集群：平台设置了 `ONECLICK_APP_URL`（或 `COMFY_PUBLIC_URL`）时，使用集群自带的反向代理。
- 其他实例：通过 radeon-tunnel 暴露端口，需要环境变量 `TUNNEL_SERVER` 和 `RADEON_TUNNEL_AUTH`（向讲师索取，notebook 会提示输入）。仓库里不保存这两个值。

> **注意：** 拿到公开 URL 的任何人都能用你的 H3 key 提交任务、消耗你的额度。不要分享这个 URL；用完运行 notebook 最后一格停止 ComfyUI 和隧道。

### H3 key

到 https://h3.oneclickamd.ai 注册。key 放在环境变量 `H3_GATEWAY_API_KEY`，或 ComfyUI 的 `user/h3_gateway_api_key.txt`（notebook 会帮你写入）。节点没有 key 输入框，key 不会写进工作流或视频元数据。

## 不用 notebook

```bash
python scripts/fetch_media.py --fonts                         # 课程素材（media/）和中文字体
python scripts/make_workflows.py --install                    # 第 3–6 章：7 镜头工作流和 docs/storyboard_dream7.md
python scripts/make_workflows.py --shots lap_8shots.json --install   # 第 7 章：8 镜头
python scripts/stitch_lap.py                                  # 拼接 7 镜头成片；--en 英文，--no-minimap 去掉小地图，--placeholder 缺镜头时预览
python scripts/stitch_lap.py --shots lap_8shots.json          # 拼接 8 镜头成片
```

`workflows/ch2_single_prompt.json` 直接拖进 ComfyUI 打开，输入图是 `assets/fictional_track_v1.png`。

## 目录

| 路径 | 内容 |
|---|---|
| `notebooks/` | 本地版和云端版 notebook |
| `docs/` | 各章讲解提纲；`storyboard_dream7.md`、`storyboard_dream8.md` 是自动生成的操作手册 |
| `storyboards/` | 分镜表：`lap_7shots.json`（第 3–6 章）、`lap_8shots.json`（第 7 章），提示词和时长的唯一来源 |
| `workflows/` | ComfyUI 工作流，由 `make_workflows.py` 生成（`ch2_single_prompt.json` 除外） |
| `examples/keyframes/` | 当时选中的关键帧，可直接复制到 ComfyUI 的 `input/` |
| `assets/` | 赛道俯视图、小地图和每个镜头的小地图路径 |
| `media/` | 历史生成的视频，由 `fetch_media.py` 按 `media/manifest.json` 下载 |
| `scripts/` | 工作流生成、拼接、素材下载和云端启动脚本 |

## 许可证

MIT，见 [LICENSE](LICENSE)。
