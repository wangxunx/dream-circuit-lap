# Drive Your Dream Circuit: an AI-Storyboarded Onboard Lap

[中文](README.zh.md)

You have a top-down map of a race track you designed. How do you turn it into an onboard video that drives one full lap?

This project starts with the most direct approach (a single prompt), then introduces storyboarding, keyframes and shot-by-shot generation, stitches a one-minute film with sector titles and a minimap, and finally uses the storyboard to fix the hardest part, the T7–T8 chicane. Everything is generated in ComfyUI: keyframes with Qwen Image 2.1 and shots with MiniMax H3 first-last-frame video. Both run in the cloud, so no local GPU is needed.

The material comes from the real iterations of the [f1_circuit](https://github.com/wangxunx/f1_circuit) project. Every step ships with the results generated at the time, so you can follow every step without spending credits.

The notebooks and lecture outlines are in Chinese.

## Chapters

| Chapter | Topic | Outline | Credits |
|---|---|---|---|
| 1 | The track map and the task | [ch1_map](docs/ch1_map.md) | none |
| 2 | One prompt: 15 s, cannot finish the lap, hard to control | [ch2_single_prompt](docs/ch2_single_prompt.md) | 1 video per run (optional) |
| 3 | Storyboard: split the lap into 7 shots | [ch3_storyboard](docs/ch3_storyboard.md) | none |
| 4 | Keyframes: one onboard image at each shot boundary | [ch4_keyframes](docs/ch4_keyframes.md) | 8 images, plus 1 per revision (optional) |
| 5 | Shots: first-last-frame video, one shot at a time | [ch5_shots](docs/ch5_shots.md) | up to 14 videos (optional) |
| 6 | Stitch the film and find the problems | [ch6_problems](docs/ch6_problems.md) | none |
| 7 | Fix the T7–T8 chicane with the storyboard | [ch7_chicane](docs/ch7_chicane.md) | 2 images + 6 videos (optional) |
| 8 | Wrap-up and exercise | [ch8_wrapup](docs/ch8_wrapup.md) | as needed |

## Running

Pick one of three ways:

| Way | For | Needs |
|---|---|---|
| [1. ComfyUI only](#1-comfyui-only) | You know ComfyUI and just want to reproduce the workflows | A local ComfyUI (Windows or Linux) |
| [2. Local notebook](#2-local-notebook) | You want the lecture notes next to the steps | A local ComfyUI plus JupyterLab |
| [3. Cloud notebook](#3-cloud-notebook) | You do not want to set up anything locally | A JupyterLab instance with ComfyUI preinstalled |

All three need an H3 key: register at https://h3.oneclickamd.ai. Put it in ComfyUI's `user/h3_gateway_api_key.txt` (both notebooks prompt for it and write the file) or in `H3_GATEWAY_API_KEY`. The nodes have no key input, so the key never ends up in workflows or video metadata.

The two notebooks share the same chapter cells. Every step that costs credits can use the bundled media instead (route A), or you generate in ComfyUI and pick your takes back in the notebook (route B).

### 1. ComfyUI only

Use the Python environment that runs ComfyUI for `python` and `pip`. With the Windows portable build, replace `python` with `..\..\python_embeded\python.exe` and `pip` with `..\..\python_embeded\python.exe -m pip` inside `dream-circuit-lap`.

1. Install [ComfyUI](https://github.com/Comfy-Org/ComfyUI#installing) if needed, then the two cloud nodes:

   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/wangxunx/ComfyUI-AMD-Qwen-Image-2.1.git
   git clone https://github.com/wangxunx/ComfyUI-AMD-MiniMaxH3.git
   ```

2. Create `ComfyUI/user/h3_gateway_api_key.txt` containing only your key.
3. Clone this repository inside the ComfyUI directory and install the workflows:

   ```bash
   cd ComfyUI
   git clone https://github.com/wangxunx/dream-circuit-lap.git
   cd dream-circuit-lap
   pip install -r requirements.txt
   python scripts/fetch_media.py --fonts                               # bundled media (media/, about 72 MB) and a CJK font
   python scripts/make_workflows.py --install                          # chapters 4-6, 7 shots
   python scripts/make_workflows.py --shots lap_8shots.json --install  # chapter 7, 8 shots
   ```

4. Start ComfyUI in CPU mode, since only cloud nodes are used: `python main.py --cpu` in the ComfyUI directory (`run_cpu.bat` for the Windows portable build). Open http://127.0.0.1:8188, close the Templates dialog shown on first launch, and press `w` for the workflow list. Restart ComfyUI if it was running before the nodes were installed; press F5 if the workflows do not show up.
5. Follow the chapters. Each workflow has a note on its left listing what to prepare; [storyboard_dream7.md](docs/storyboard_dream7.md) and [storyboard_dream8.md](docs/storyboard_dream8.md) collect the frames, prompts and copy commands for every shot.
   - **Ch. 2**: drag `workflows/ch2_single_prompt.json` onto the canvas, upload `assets/fictional_track_v1.png` in the Load Image node, press Run. The historical takes are `media/ch2_single_prompt_*.mp4`.
   - **Ch. 4**: run `dream7_keyframes_pilot` (K0, K1), then `dream7_keyframes`. Check each image against the storyboard; if it is wrong, edit the scene description at the start of that node's prompt and run again. Copy the final images from `ComfyUI/output/dream7/` to `ComfyUI/input/dream7_K0.png` … `dream7_K7.png`, or copy `examples/keyframes/dream7_K*.png` there.
   - **Ch. 5**: press F5, run `dream7_shot_01` … `dream7_shot_07`. Copy your picks from `ComfyUI/output/video/dream7/` to `ComfyUI/output/video/dream7/selected/shot_01.mp4` …, or copy `media/dream7_shot_0X.mp4` there.
   - **Ch. 6**: `python scripts/stitch_lap.py` writes `output/dream_circuit_7shots.mp4` in this repository. Options: `--en`, `--no-minimap`, `--placeholder`.
   - **Ch. 7**: run `dream8_keyframes`, put K4 and K5 at `input/dream8_K4.png` and `dream8_K5.png`, press F5, run `dream8_shot_04` … `dream8_shot_06` and put the picks in `output/video/dream8/selected/`. The bundled versions are `examples/keyframes/dream8_K*.png` and `media/dream8_shot_0X.mp4`. Then `python scripts/stitch_lap.py --shots lap_8shots.json`.

   A Load Image node outlined in red with a "Media input missing" or "errors found" toast means its image is not in `ComfyUI/input/` yet; add it and press F5.

### 2. Local notebook

Needs a local ComfyUI in a conda or venv environment; the notebook installs the nodes and writes the key. The embedded Python of the Windows portable build is not a good fit for JupyterLab, so use way 1 or 3 there.

1. Start JupyterLab:

   ```bash
   conda activate comfyui                 # the environment that runs ComfyUI
   cd /path/to/ComfyUI
   git clone https://github.com/wangxunx/dream-circuit-lap.git
   cd dream-circuit-lap
   pip install jupyterlab -r requirements.txt
   jupyter lab --ServerApp.root_dir=. notebooks/local.ipynb
   ```

   Keep `--ServerApp.root_dir=.`: without it JupyterLab serves only `notebooks/` and the videos 404. Set `COMFYUI_DIR` if ComfyUI is not the parent directory.
2. Open the `http://127.0.0.1:8888/lab?token=...` URL printed in the terminal. On a remote machine (e.g. Cursor or VS Code Remote SSH), forward port 8888 in the Ports panel if it is not forwarded automatically.
3. Run section 0 cell by cell with `Shift+Enter`. Finished steps are skipped; paste the key into the input box when asked. Starting ComfyUI takes a few seconds. An existing ComfyUI on port 8188 is reused; restart it if it was started before the nodes were installed.
4. Open http://127.0.0.1:8188 (forward port 8188 if needed) and close the Templates dialog shown on first launch.
5. Run "准备素材" (prepare media), then press `w` in ComfyUI for the `ch2_single_prompt`, `dream7_*` and `dream8_*` workflows; press F5 if they are missing.
6. First pass, route A: keep pressing `Shift+Enter` to the end. No credits are spent and you see all historical clips and both films.
7. Second pass, route B: from chapter 4, generate in ComfyUI as the notebook describes, run the picker cells (fill in your take numbers for the videos first), press F5 in ComfyUI and continue.

ComfyUI keeps running in the background after JupyterLab is closed (log in ComfyUI's `user/comfyui_dream_circuit.log`) and is reused next time.

### 3. Cloud notebook

For JupyterLab/JupyterHub images with ComfyUI at `/comfyui_workspace/ComfyUI` (override with `COMFY_DIR`). ComfyUI runs with `--cpu` in the background and does not use the GPU.

1. In the platform's JupyterLab, open **File → New → Terminal** and run `git clone https://github.com/wangxunx/dream-circuit-lap.git`. Clone it where the file browser can see it (the terminal starts there) so the videos play.
2. Open `dream-circuit-lap/notebooks/cloud.ipynb` from the file browser.
3. Run section 0 cell by cell with `Shift+Enter`, pasting the key when asked. The launch cell picks the route automatically: the AMD Instinct cluster proxy when `ONECLICK_APP_URL` or `COMFY_PUBLIC_URL` is set, otherwise radeon-tunnel, which prompts for `TUNNEL_SERVER` and `RADEON_TUNNEL_AUTH` from your platform provider. Neither value is stored in this repository.
4. Open the printed `ComfyUI URL` in a new tab and close the Templates dialog if it appears.

   > Anyone with this URL can queue jobs on your H3 key. Do not share it.

5. Continue as in steps 5–7 of the local notebook.
6. Run the last cell when you are done to stop ComfyUI and the tunnel.

## License

MIT, see [LICENSE](LICENSE).
