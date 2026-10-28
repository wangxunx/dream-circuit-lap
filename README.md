# Drive Your Dream Circuit: an AI-Storyboarded Onboard Lap

[中文](README.zh.md)

You have a top-down map of a race track you designed. How do you turn it into an onboard video that drives one full lap?

This course starts with the most direct approach (a single prompt), then introduces storyboarding, keyframes and shot-by-shot generation, stitches a one-minute film with sector titles and a minimap, and finally uses the storyboard to fix the hardest part, the T7–T8 chicane. Everything is generated in ComfyUI: keyframes with Qwen Image 2.1 and shots with MiniMax H3 first-last-frame video. Both run in the cloud, so no local GPU is needed.

The material comes from the real iterations of the [f1_circuit](https://github.com/wangxunx/f1_circuit) project. Every step ships with the results generated at the time, so you can follow the whole course without spending credits.

The notebooks and lecture outlines are in Chinese.

## Chapters

| Chapter | Topic | Outline | Credits |
|---|---|---|---|
| 1 | The track map and the task | [ch1_map](docs/ch1_map.md) | none |
| 2 | One prompt: 15 s, cannot finish the lap, hard to control | [ch2_single_prompt](docs/ch2_single_prompt.md) | 1 video per run (optional) |
| 3 | Storyboard: split the lap into 7 shots | [ch3_storyboard](docs/ch3_storyboard.md) | none |
| 4 | Keyframes: one onboard image at each shot boundary | [ch4_keyframes](docs/ch4_keyframes.md) | up to 24 images (optional) |
| 5 | Shots: first-last-frame video, one shot at a time | [ch5_shots](docs/ch5_shots.md) | up to 14 videos (optional) |
| 6 | Stitch the film and find the problems | [ch6_problems](docs/ch6_problems.md) | none |
| 7 | Fix the T7–T8 chicane with the storyboard | [ch7_chicane](docs/ch7_chicane.md) | 6 images + 6 videos (optional) |
| 8 | Wrap-up and homework | [ch8_wrapup](docs/ch8_wrapup.md) | as needed |

## Running

Both notebooks do the same work: install the two nodes, configure the H3 key, start ComfyUI, download the course media, install the workflows for each chapter and stitch the films. Images and videos are generated in ComfyUI in the browser. Open the notebooks in JupyterLab or JupyterHub so the embedded videos play.

- **Local, `notebooks/local.ipynb`**: clone this repository inside your ComfyUI directory (e.g. `ComfyUI/dream-circuit-lap`) and run JupyterLab from ComfyUI's Python environment, or set `COMFYUI_DIR`.
- **Cloud, `notebooks/cloud.ipynb`**: for JupyterLab/JupyterHub instances with ComfyUI at `/comfyui_workspace/ComfyUI` (override with `COMFY_DIR`). `scripts/start_comfyui_cloud.sh` starts ComfyUI with `--cpu` in the background and prints the URL. It uses the AMD Instinct cluster proxy when `ONECLICK_APP_URL` or `COMFY_PUBLIC_URL` is set, and radeon-tunnel otherwise; the tunnel needs `TUNNEL_SERVER` and `RADEON_TUNNEL_AUTH` from your workshop organiser.

> Anyone with the public URL can queue jobs on your H3 key. Do not share it, and stop ComfyUI with the last notebook cell when you are done.

Register at https://h3.oneclickamd.ai for an H3 key. Put it in `H3_GATEWAY_API_KEY` or ComfyUI's `user/h3_gateway_api_key.txt`; the notebooks write the file for you.

Without the notebooks:

```bash
python scripts/fetch_media.py --fonts                                # course media and a CJK font
python scripts/make_workflows.py --install                           # chapters 3-6, 7 shots
python scripts/make_workflows.py --shots lap_8shots.json --install   # chapter 7, 8 shots
python scripts/stitch_lap.py                                         # 7-shot film; --en, --no-minimap, --placeholder
python scripts/stitch_lap.py --shots lap_8shots.json                 # 8-shot film
```

## License

MIT, see [LICENSE](LICENSE).
