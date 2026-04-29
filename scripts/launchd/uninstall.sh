#!/usr/bin/env bash
set -euo pipefail

TARGET="$HOME/Library/LaunchAgents/com.kms-agent.weekly.plist"

if [[ -f "$TARGET" ]]; then
  launchctl unload "$TARGET" 2>/dev/null || true
  rm "$TARGET"
  echo "Removed: $TARGET"
else
  echo "Not installed."
fi
