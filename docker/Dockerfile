# Image for notebooks/cloud.ipynb and cloud_en.ipynb on AMD OneClick.
# The platform clones this project into /workspace at startup; the image provides ComfyUI and the Python packages.
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

WORKDIR /workspace
