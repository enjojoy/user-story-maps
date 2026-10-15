#!/usr/bin/env bash
# Capture a clean screenshot from the booted iOS Simulator (macOS + Xcode only).
#
#   ios-simulator.sh <screen-id> [options]
#     -o DIR        output folder            (default: docs/story-map/screens)
#     -d NAME|UDID  device to boot if none is booted, e.g. "iPhone 16"
#     -u URL        open a deep link first   (e.g. myapp://settings) and wait
#     -w SECONDS    wait before capturing    (default: 2)
#     -m light|dark appearance               (default: leave as is)
#     --list        list available devices and exit
#
# Typical loop: navigate the app to a screen by hand (or by deep link), then run
#   ios-simulator.sh welcome ; ios-simulator.sh plant-list -u plantwaterer://list
# The file is written as <DIR>/<screen-id>.png, which is what `image:` in stories.yaml points to.
set -euo pipefail
command -v xcrun >/dev/null || { echo "xcrun not found - this script needs macOS with Xcode command line tools." >&2; exit 1; }

OUT="docs/story-map/screens"; DEVICE=""; URL=""; WAIT=2; MODE=""
if [[ "${1:-}" == "--list" ]]; then xcrun simctl list devices available; exit 0; fi
ID="${1:?usage: ios-simulator.sh <screen-id> [-o DIR] [-d DEVICE] [-u URL] [-w SECONDS] [-m light|dark]}"; shift
while getopts "o:d:u:w:m:" opt; do
  case $opt in o) OUT=$OPTARG;; d) DEVICE=$OPTARG;; u) URL=$OPTARG;; w) WAIT=$OPTARG;; m) MODE=$OPTARG;; *) exit 1;; esac
done

if ! xcrun simctl list devices booted | grep -q "(Booted)"; then
  [[ -n "$DEVICE" ]] || { echo "No simulator is booted. Pass -d \"iPhone 16\" (see --list)." >&2; exit 1; }
  xcrun simctl boot "$DEVICE"; open -a Simulator; sleep 8
fi
# Clean, identical status bar on every shot (9:41, full battery, full signal)
xcrun simctl status_bar booted override --time "9:41" --batteryState charged --batteryLevel 100 \
  --wifiBars 3 --cellularMode active --cellularBars 4 >/dev/null 2>&1 || true
[[ -z "$MODE" ]] || xcrun simctl ui booted appearance "$MODE"
[[ -z "$URL" ]] || xcrun simctl openurl booted "$URL"
sleep "$WAIT"
mkdir -p "$OUT"
xcrun simctl io booted screenshot --type=png "$OUT/$ID.png"
echo "saved $OUT/$ID.png"
# Reminder: sign in with a DEMO account only. Never commit screenshots that show real names, emails or tokens.
