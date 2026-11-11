#!/bin/sh
# Render the Blender scenes, one at a time, at low priority (the machine is shared).
# Frames go to $SG_BUMP_WORK/renders/<scene>/0001.jpg ... 0288.jpg. Interrupted
# renders resume: existing frames are skipped.
#   sh bumps/src/render_all.sh              # all scenes
#   sh bumps/src/render_all.sh station      # one
HERE="$(cd "$(dirname "$0")" && pwd)"
W="${SG_BUMP_WORK:-/mnt/ssd240gb/anna/snow-globe-bumps}"
BLENDER="${BLENDER:-/snap/bin/blender}"
[ $# -eq 0 ] && set -- station tvfield train pingpong sponsor
for sc in "$@"; do
  nice -n 15 "$BLENDER" -b --python "$HERE/scenes/$sc.py" -- --out "$W/renders/$sc" > "$W/work/$sc.log" 2>&1
  echo "$sc: $(ls "$W/renders/$sc" | grep -c '^[0-9]\{4\}\.jpg$') frames"
done
