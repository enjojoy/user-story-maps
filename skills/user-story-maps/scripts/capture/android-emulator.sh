#!/usr/bin/env bash
# Capture a clean screenshot from a running Android emulator / device via adb.
#
#   android-emulator.sh <screen-id> [options]
#     -o DIR      output folder            (default: docs/story-map/screens)
#     -s SERIAL   adb device serial        (see `adb devices`; needed if several are connected)
#     -u URL      open a deep link first   (e.g. myapp://settings) and wait
#     -w SECONDS  wait before capturing    (default: 2)
#     -n          do NOT enable demo mode (keep the real status bar)
#
# Demo mode gives a clean status bar (09:41, full battery/wifi, no notification icons).
# Navigate to the screen by hand or with a deep link, then run this once per screen.
set -euo pipefail
command -v adb >/dev/null || { echo "adb not found - install Android platform-tools." >&2; exit 1; }

OUT="docs/story-map/screens"; SERIAL=""; URL=""; WAIT=2; DEMO=1
ID="${1:?usage: android-emulator.sh <screen-id> [-o DIR] [-s SERIAL] [-u URL] [-w SECONDS] [-n]}"; shift
while getopts "o:s:u:w:n" opt; do
  case $opt in o) OUT=$OPTARG;; s) SERIAL=$OPTARG;; u) URL=$OPTARG;; w) WAIT=$OPTARG;; n) DEMO=0;; *) exit 1;; esac
done
ADB=(adb); [[ -z "$SERIAL" ]] || ADB=(adb -s "$SERIAL")

if [[ $DEMO == 1 ]]; then
  "${ADB[@]}" shell settings put global sysui_demo_allowed 1
  b() { "${ADB[@]}" shell am broadcast -a com.android.systemui.demo -e command "$@" >/dev/null; }
  b enter; b clock -e hhmm 0941; b battery -e level 100 -e plugged false
  b network -e wifi show -e level 4; b network -e mobile show -e datatype none -e level 4
  b notifications -e visible false
fi
[[ -z "$URL" ]] || "${ADB[@]}" shell am start -a android.intent.action.VIEW -d "$URL" >/dev/null
sleep "$WAIT"
mkdir -p "$OUT"
"${ADB[@]}" exec-out screencap -p > "$OUT/$ID.png"
echo "saved $OUT/$ID.png"
[[ $DEMO == 0 ]] || b exit
# Reminder: use a DEMO account only. Never commit screenshots that show real names, emails or tokens.
