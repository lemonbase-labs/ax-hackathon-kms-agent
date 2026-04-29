#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

DEV_MODE=0
if [ "${1:-}" = "--dev" ]; then
  DEV_MODE=1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "[!] uv가 설치되어 있지 않습니다."
  echo ""
  echo "터미널에서 아래 명령을 한 번만 실행하세요:"
  echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo ""
  echo "설치 후 터미널을 새로 열고 다시 실행하세요."
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[!] npm이 설치되어 있지 않습니다."
  echo ""
  echo "https://nodejs.org 에서 Node.js LTS를 설치한 후 다시 실행하세요."
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "[!] .env 파일이 없습니다. 전달받은 .env 파일을 이 폴더에 두고 다시 실행하세요."
  exit 1
fi

echo "[1/3] 의존성 확인 중... (처음 한 번은 1~2분 걸립니다)"
uv sync --quiet

if [ "$DEV_MODE" = "1" ]; then
  echo "[2/3] 프론트엔드 의존성 확인 중..."
  (cd web && npm install --silent)
  URL="http://127.0.0.1:5173"
else
  echo "[2/3] 프론트엔드 빌드 중... (처음 한 번은 1~2분 걸립니다)"
  (cd web && npm install --silent && npm run build --silent)
  URL="http://127.0.0.1:8000"
fi

(
  for _ in {1..40}; do
    sleep 0.5
    if curl -fs -o /dev/null "$URL"; then
      open "$URL"
      exit 0
    fi
  done
) &

if [ "$DEV_MODE" = "1" ]; then
  echo "[3/3] 서버 시작: 백엔드 :8000 + Vite :5173 (HMR)  (종료하려면 이 창에서 Ctrl+C)"
  uv run uvicorn kms.web:app --host 127.0.0.1 --port 8000 &
  BACKEND_PID=$!
  trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT
  (cd web && npm run dev)
else
  echo "[3/3] 서버 시작: $URL  (종료하려면 이 창에서 Ctrl+C)"
  exec uv run uvicorn kms.web:app --host 127.0.0.1 --port 8000
fi
