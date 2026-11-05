# Image for notebooks/cloud.ipynb and cloud_en.ipynb on AMD OneClick.
# The platform clones this project into /workspace at startup; the image provides ComfyUI, the Python packages,
# the car-edit models, and a copy of the media and fonts for platforms that cannot reach GitHub release downloads.
#
#   docker build -t dream-circuit-lap docker/
FROM crpi-xhg6joi134vrkpzq.cn-shanghai.personal.cr.aliyuncs.com/vivienfanghua/amd-oneclick-base@sha256:731ec9e8521ea33efbf9839974fe6b48e94cfc0c2b7bd3e94b4de524096b2dd8

ARG COMFYUI_COMMIT=d91ed5f5b7fa60fa18464c2ad7c80254da2f0f29

# Keep the base image's ROCm builds of torch, torchvision and torchaudio.
RUN git clone https://github.com/Comfy-Org/ComfyUI.git /comfyui_workspace/ComfyUI \
    && cd /comfyui_workspace/ComfyUI && git checkout -q ${COMFYUI_COMMIT} \
    && pip list --format=freeze | grep -E '^(torch|torchvision|torchaudio|triton)==' > /tmp/torch-constraints.txt \
    && pip install --no-cache-dir -c /tmp/torch-constraints.txt -r requirements.txt numpy 'pillow>=10' 'av>=14' \
    && rm /tmp/torch-constraints.txt

# Qwen Image 2.1 models for the car edit in chapters 4 and 7 (about 17 GB).
RUN cd /comfyui_workspace/ComfyUI/models \
    && for f in diffusion_models/qwen_image_2.1_int8_convrot.safetensors \
                text_encoders/qwen3vl_8b_int8_convrot.safetensors \
                vae/qwen_image_2.1_vae_bf16.safetensors; do \
         curl -fL --retry 3 -o "$f" "https://huggingface.co/Comfy-Org/Qwen-Image-2.1/resolve/main/$f" || exit 1; \
       done

# fetch_media.py copies these when they match media/manifest.json and falls back to them when a download fails.
RUN git clone --depth 1 https://github.com/wangxunx/dream-circuit-lap.git /tmp/dream-circuit-lap \
    && for i in 1 2 3; do python3 /tmp/dream-circuit-lap/scripts/fetch_media.py --fonts && break; [ $i = 3 ] && exit 1; sleep 30; done \
    && mkdir -p /opt/dream-circuit-lap \
    && mv /tmp/dream-circuit-lap/media /tmp/dream-circuit-lap/fonts /opt/dream-circuit-lap/ \
    && rm -rf /tmp/dream-circuit-lap
ENV DREAM_CIRCUIT_MEDIA_CACHE=/opt/dream-circuit-lap/media \
    F1_FONT_REGULAR=/opt/dream-circuit-lap/fonts/NotoSansSC-Regular.otf \
    F1_FONT_BOLD=/opt/dream-circuit-lap/fonts/NotoSansSC-Bold.otf

WORKDIR /workspace
