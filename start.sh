#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v uv >/dev/null 2>&1; then
  echo "[!] uv가 설치되어 있지 않습니다."
  echo ""
  echo "터미널에서 아래 명령을 한 번만 실행하세요:"
  echo "    curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo ""
  echo "설치 후 터미널을 새로 열고 다시 실행하세요."
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "[!] .env 파일이 없습니다. 전달받은 .env 파일을 이 폴더에 두고 다시 실행하세요."
  exit 1
fi

echo "[1/2] 의존성 확인 중... (처음 한 번은 1~2분 걸립니다)"
uv sync --quiet

URL="http://127.0.0.1:8000"
(
  for _ in {1..40}; do
    sleep 0.5
    if curl -fs -o /dev/null "$URL"; then
      open "$URL"
      exit 0
    fi
  done
) &

echo "[2/2] 서버 시작: $URL  (종료하려면 이 창에서 Ctrl+C)"
exec uv run uvicorn kms.web:app --host 127.0.0.1 --port 8000
