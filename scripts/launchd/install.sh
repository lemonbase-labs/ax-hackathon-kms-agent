#!/usr/bin/env bash
# Install the weekly launchd agent (Mon 09:00 local time).
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$HOME/Library/Logs/kms-agent"
PLIST_NAME="com.kms-agent.weekly.plist"
TEMPLATE="$REPO/scripts/launchd/$PLIST_NAME.template"
TARGET="$HOME/Library/LaunchAgents/$PLIST_NAME"

if [[ ! -x "$REPO/.venv/bin/python" ]]; then
  echo "ERROR: $REPO/.venv/bin/python not found. Run 'uv sync' first." >&2
  exit 1
fi
if [[ ! -f "$REPO/.env" ]]; then
  echo "WARNING: $REPO/.env not found — weekly_run will fail without it." >&2
fi

mkdir -p "$LOG_DIR"
mkdir -p "$(dirname "$TARGET")"

sed -e "s|__REPO__|$REPO|g" -e "s|__LOG_DIR__|$LOG_DIR|g" \
    "$TEMPLATE" > "$TARGET"

launchctl unload "$TARGET" 2>/dev/null || true
launchctl load "$TARGET"

echo "Installed: $TARGET"
echo "Logs:      $LOG_DIR/weekly.{log,err}"
echo
echo "Manually trigger now:  launchctl start com.kms-agent.weekly"
echo "Status:                launchctl list | grep kms-agent"
echo "Uninstall:             $REPO/scripts/launchd/uninstall.sh"
