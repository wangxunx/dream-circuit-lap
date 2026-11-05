#!/bin/bash
# Start ComfyUI in the background on a cloud notebook and print the URL to open it, then return.
#
#   bash scripts/start_comfyui_cloud.sh         # (re)start ComfyUI and expose it
#   bash scripts/start_comfyui_cloud.sh stop    # stop ComfyUI and the tunnel
#
# Exposure:
#   - COMFY_PUBLIC_URL or ONECLICK_APP_URL set (AMD Instinct cluster): the cluster's reverse proxy already serves the port.
#   - otherwise the Radeon cloud's rc-tunnel, installed from the platform on first use; ComfyUI then listens on
#     127.0.0.1 only, and a restart keeps the tunnel and its URL (stopping a tunnel freezes its URL for 24 hours).
#     See https://amd-aim.github.io/radeon-cloud-docs/zh-cn/guides/tunnel/
#   COMFY_HARDWARE=instinct|radeon forces one of the two.
#
# Keyframes and shots use cloud nodes (Qwen Image 2.1 and MiniMax H3); only the car edit runs a local model.
# ComfyUI uses the GPU when torch sees one and runs with --cpu otherwise; COMFY_ARGS overrides this.
# Anyone with the public URL can queue jobs on your H3 key: do not share it.
#
# Adapted from https://github.com/Vivicai1005/notebook (comfyui_ltx_notebook/start_comfyui_with_tunnel.sh).
set -Eeuo pipefail

export PATH="/opt/venv/bin:/opt/rocm/bin:${PATH}"

COMFY_PORT="${COMFY_PORT:-8188}"
COMFY_DIR="${COMFY_DIR:-/comfyui_workspace/ComfyUI}"
COMFY_ARGS="${COMFY_ARGS-$(python3 -c 'import torch; print("" if torch.cuda.is_available() else "--cpu")' 2>/dev/null || echo --cpu)}"
COMFY_READY_TIMEOUT="${COMFY_READY_TIMEOUT:-120}"
COMFY_HARDWARE="${COMFY_HARDWARE:-auto}"
RC_TUNNEL="${HOME:-/root}/.local/bin/rc-tunnel"
RC_TUNNEL_INSTALL=/var/run/secrets/frp-self-service/install
TUNNEL_READY_TIMEOUT="${TUNNEL_READY_TIMEOUT:-60}"

COMFY_PID_FILE=/tmp/comfyui.pid
COMFY_LOG=/tmp/comfyui.log


stop_comfy() {
  local pid cmdline
  [[ -f "${COMFY_PID_FILE}" ]] || return 0
  pid="$(cat "${COMFY_PID_FILE}")"
  rm -f "${COMFY_PID_FILE}"
  # only kill the PID if it is still the process we started
  cmdline="$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)"
  if [[ "${pid}" =~ ^[0-9]+$ && "${cmdline}" == *"main.py --listen "*" --port ${COMFY_PORT}"* ]]; then
    echo "[stop] ComfyUI (PID ${pid})"
    kill "${pid}" 2>/dev/null || true
    for _ in $(seq 1 10); do kill -0 "${pid}" 2>/dev/null || return 0; sleep 1; done
    kill -9 "${pid}" 2>/dev/null || true
  fi
}

stop_tunnel() {
  if [[ -x "${RC_TUNNEL}" ]] && "${RC_TUNNEL}" status > /dev/null 2>&1; then
    echo "[stop] rc-tunnel"
    "${RC_TUNNEL}" stop > /dev/null
  fi
}

stop_all() {
  stop_tunnel
  stop_comfy
}

fail() {
  echo "[error] $1"
  [[ -n "${2:-}" ]] && tail -n 40 "$2"
  stop_comfy
  exit 1
}

fail_tunnel() {
  echo "[error] $1, rc-tunnel logs:"
  "${RC_TUNNEL}" logs --lines 40 || true
  stop_all
  exit 1
}

print_url() {
  echo ""
  echo "========================================"
  echo "ComfyUI URL: $1"
  echo "========================================"
  echo "Do not share this URL: anyone who opens it can queue jobs on your H3 key."
}


if [[ "${1:-}" == "stop" ]]; then
  stop_all
  exit 0
fi

case "${COMFY_HARDWARE}" in
  instinct|radeon) MODE="${COMFY_HARDWARE}" ;;
  auto) [[ -n "${COMFY_PUBLIC_URL:-${ONECLICK_APP_URL:-}}" ]] && MODE=instinct || MODE=radeon ;;
  *) echo "[error] COMFY_HARDWARE must be auto, instinct or radeon, got ${COMFY_HARDWARE}"; exit 1 ;;
esac

if [[ "${MODE}" == radeon && -z "${FRP_BROKER_URL:-}" ]]; then
  echo "[error] rc-tunnel needs FRP_BROKER_URL, which the Radeon cloud sets on the notebook container."
  echo "        Run this from a notebook cell or a JupyterLab terminal, not an SSH session."
  echo "        If it is missing there too, the instance predates rc-tunnel: destroy it and create a new one."
  exit 1
fi
[[ -f "${COMFY_DIR}/main.py" ]] || { echo "[error] ComfyUI not found at ${COMFY_DIR} (set COMFY_DIR)"; exit 1; }

# rc-tunnel only serves services bound to 127.0.0.1; the Instinct proxy reaches the pod address
[[ "${MODE}" == radeon ]] && LISTEN=127.0.0.1 || LISTEN=0.0.0.0

stop_comfy

echo "[start] ComfyUI on port ${COMFY_PORT} (${COMFY_ARGS:-GPU})"
cd "${COMFY_DIR}"
# word splitting of COMFY_ARGS is intended
# shellcheck disable=SC2086
setsid nohup python3 main.py --listen "${LISTEN}" --port "${COMFY_PORT}" ${COMFY_ARGS} > "${COMFY_LOG}" 2>&1 < /dev/null &
echo $! > "${COMFY_PID_FILE}"

for ((i = 1; i <= COMFY_READY_TIMEOUT; i++)); do
  sleep 1
  kill -0 "$(cat "${COMFY_PID_FILE}")" 2>/dev/null || fail "ComfyUI exited during startup, last log lines:" "${COMFY_LOG}"
  curl -s -o /dev/null --max-time 2 "http://127.0.0.1:${COMFY_PORT}/" && break
  (( i == COMFY_READY_TIMEOUT )) && fail "ComfyUI was not ready after ${COMFY_READY_TIMEOUT}s, last log lines:" "${COMFY_LOG}"
done
echo "[start] ComfyUI is ready, log: ${COMFY_LOG}"

if [[ "${MODE}" == instinct ]]; then
  URL="${COMFY_PUBLIC_URL:-${ONECLICK_APP_URL:-}}"
  [[ -n "${URL}" ]] || fail "COMFY_PUBLIC_URL and ONECLICK_APP_URL are not set; open port ${COMFY_PORT}'s App URL from the cluster console"
  print_url "${URL}"
  exit 0
fi

if [[ ! -x "${RC_TUNNEL}" ]]; then
  echo "[tunnel] installing rc-tunnel"
  [[ -x "${RC_TUNNEL_INSTALL}" ]] || fail "${RC_TUNNEL_INSTALL} not found; the instance predates rc-tunnel, destroy it and create a new one"
  "${RC_TUNNEL_INSTALL}" > /dev/null || fail "rc-tunnel install failed"
fi

STATUS="$("${RC_TUNNEL}" status 2>/dev/null || true)"
if grep -Eq "^Local port: +${COMFY_PORT}$" <<< "${STATUS}" && grep -Eq '^FRPC running: +true' <<< "${STATUS}"; then
  echo "[tunnel] reusing the running rc-tunnel"
  URL="$(grep -Eo 'https://[^[:space:]]+' <<< "${STATUS}" | head -1)"
else
  # a notebook can expose one port at a time
  stop_tunnel
  URL="$("${RC_TUNNEL}" expose --port "${COMFY_PORT}" | grep -Eo 'https://[^[:space:]]+' | head -1 || true)"
  [[ -n "${URL}" ]] || fail_tunnel "rc-tunnel printed no URL"
fi

# the URL serves frp's 404 page until the tunnel is active
for ((i = 1; i <= TUNNEL_READY_TIMEOUT; i++)); do
  "${RC_TUNNEL}" status 2>/dev/null | grep -Eq '^Status: +active' && break
  (( i == TUNNEL_READY_TIMEOUT )) && fail_tunnel "rc-tunnel was not active after ${TUNNEL_READY_TIMEOUT}s"
  sleep 1
done
print_url "${URL}"
