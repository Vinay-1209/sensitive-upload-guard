#!/usr/bin/env bash
# Register the native messaging host for Chromium/Chrome/Brave and Firefox (Linux).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST_NAME="com.walled.sensitive_upload_guard"
RUNNER="$ROOT/native_host/run_host.sh"
# Stable ID from extension/manifest.json "key" field
DEFAULT_CHROME_ID="apljnpgfjedkilddjnmmigilnickhpla"
CHROME_EXT_ID="${1:-$DEFAULT_CHROME_ID}"

chmod +x "$RUNNER" "$ROOT/native_host/host.py"

write_chrome_manifest() {
  local dir="$1"
  mkdir -p "$dir"
  cat >"$dir/${HOST_NAME}.json" <<EOF
{
  "name": "${HOST_NAME}",
  "description": "Sensitive Upload Guard native host",
  "path": "${RUNNER}",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://${CHROME_EXT_ID}/"
  ]
}
EOF
  echo "Wrote $dir/${HOST_NAME}.json"
}

write_firefox_manifest() {
  local dir="$1"
  mkdir -p "$dir"
  cat >"$dir/${HOST_NAME}.json" <<EOF
{
  "name": "${HOST_NAME}",
  "description": "Sensitive Upload Guard native host",
  "path": "${RUNNER}",
  "type": "stdio",
  "allowed_extensions": ["sensitive-upload-guard@local"]
}
EOF
  echo "Wrote $dir/${HOST_NAME}.json"
}

for base in \
  "$HOME/.config/google-chrome/NativeMessagingHosts" \
  "$HOME/.config/chromium/NativeMessagingHosts" \
  "$HOME/.config/BraveSoftware/Brave-Browser/NativeMessagingHosts"
do
  write_chrome_manifest "$base"
done

write_firefox_manifest "$HOME/.mozilla/native-messaging-hosts"

echo
echo "Native host installed as ${HOST_NAME}"
echo "Chrome/Chromium extension ID: ${CHROME_EXT_ID}"
echo "Firefox extension id: sensitive-upload-guard@local"
echo "Runner: ${RUNNER}"
