#!/bin/bash
# Start ComfyUI in the background on a cloud notebook and print the URL to open it, then return.
#
#   bash scripts/start_comfyui_cloud.sh         # (re)start ComfyUI and expose it
#   bash scripts/start_comfyui_cloud.sh stop    # stop ComfyUI and the tunnel
#
# Exposure:
#   - COMFY_PUBLIC_URL or ONECLICK_APP_URL set (AMD Instinct cluster): the cluster's reverse proxy already serves the port.
#   - otherwise radeon-tunnel, which needs TUNNEL_SERVER and RADEON_TUNNEL_AUTH from the platform or your environment.
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
TUNNEL_BIN="${TUNNEL_BIN:-/tmp/radeon-tunnel}"
TUNNEL_URL_TIMEOUT="${TUNNEL_URL_TIMEOUT:-60}"

COMFY_PID_FILE=/tmp/comfyui.pid
TUNNEL_PID_FILE=/tmp/tunnel.pid
COMFY_LOG=/tmp/comfyui.log
TUNNEL_LOG=/tmp/tunnel.log


stop_pidfile() {
  local pid_file="$1" expected="$2" pid cmdline
  [[ -f "${pid_file}" ]] || return 0
  pid="$(cat "${pid_file}")"
  rm -f "${pid_file}"
  # only kill the PID if it is still the process we started
  cmdline="$(tr '\0' ' ' < "/proc/${pid}/cmdline" 2>/dev/null || true)"
  if [[ "${pid}" =~ ^[0-9]+$ && "${cmdline}" == *"${expected}"* ]]; then
    echo "[stop] ${expected} (PID ${pid})"
    kill "${pid}" 2>/dev/null || true
    for _ in $(seq 1 10); do kill -0 "${pid}" 2>/dev/null || return 0; sleep 1; done
    kill -9 "${pid}" 2>/dev/null || true
  fi
}

stop_all() {
  stop_pidfile "${TUNNEL_PID_FILE}" "expose ${COMFY_PORT}"
  stop_pidfile "${COMFY_PID_FILE}" "main.py --listen 0.0.0.0 --port ${COMFY_PORT}"
}

fail() {
  echo "[error] $1"
  [[ -n "${2:-}" ]] && tail -n 40 "$2"
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

if [[ "${MODE}" == radeon && ( -z "${TUNNEL_SERVER:-}" || -z "${RADEON_TUNNEL_AUTH:-}" ) ]]; then
  echo "[error] radeon-tunnel needs TUNNEL_SERVER and RADEON_TUNNEL_AUTH."
  echo "        Get both from your platform provider and set them before running this script, e.g. in a notebook cell:"
  echo "        os.environ['TUNNEL_SERVER'] = 'http://<server>:<port>'; os.environ['RADEON_TUNNEL_AUTH'] = '<token>'"
  exit 1
fi
[[ -f "${COMFY_DIR}/main.py" ]] || { echo "[error] ComfyUI not found at ${COMFY_DIR} (set COMFY_DIR)"; exit 1; }

stop_all

echo "[start] ComfyUI on port ${COMFY_PORT} (${COMFY_ARGS:-GPU})"
cd "${COMFY_DIR}"
# word splitting of COMFY_ARGS is intended
# shellcheck disable=SC2086
setsid nohup python3 main.py --listen 0.0.0.0 --port "${COMFY_PORT}" ${COMFY_ARGS} > "${COMFY_LOG}" 2>&1 < /dev/null &
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

echo "[tunnel] downloading the radeon-tunnel client"
curl --noproxy '*' -fsSL "${TUNNEL_SERVER}/client" -o "${TUNNEL_BIN}" || fail "could not download ${TUNNEL_SERVER}/client"
chmod +x "${TUNNEL_BIN}"
rm -rf "${HOME:-/root}/.radeon"
export RADEON_TUNNEL_AUTH
setsid nohup "${TUNNEL_BIN}" expose "${COMFY_PORT}" > "${TUNNEL_LOG}" 2>&1 < /dev/null &
echo $! > "${TUNNEL_PID_FILE}"

for ((i = 1; i <= TUNNEL_URL_TIMEOUT; i++)); do
  sleep 1
  kill -0 "$(cat "${TUNNEL_PID_FILE}")" 2>/dev/null || fail "radeon-tunnel exited, last log lines:" "${TUNNEL_LOG}"
  URL="$(grep -Eo 'https?://[^[:space:]]+' "${TUNNEL_LOG}" | head -1 || true)"
  if [[ -n "${URL}" ]]; then
    print_url "${URL}"
    exit 0
  fi
done
fail "radeon-tunnel printed no URL within ${TUNNEL_URL_TIMEOUT}s, last log lines:" "${TUNNEL_LOG}"
