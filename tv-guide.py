#!/usr/bin/env python3
"""snow-globe daily TV guide generator. Outputs a formatted schedule for today.

  python3 tv-guide.py            # the programs
  python3 tv-guide.py --bumps    # also name the bump that airs after each program
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Seconds per bump. Must match BUMP_DURATION in app.js and the real length of
# every file in bumps/ (bumps/src/build.py --check verifies the files).
BUMP_DURATION = 12

BLOCKS = [
    {"name": "morning",   "start": 8,  "end": 12, "label": "☀️ morning"},
    {"name": "afternoon", "start": 12, "end": 18, "label": "🌤️ afternoon"},
    {"name": "evening",   "start": 18, "end": 22, "label": "🌆 evening"},
    {"name": "latenight", "start": 22, "end": 26, "label": "🌙 late night"},
    {"name": "deadhours", "start": 2,  "end": 8,  "label": "🌑 dead hours"},
]

def seeded_random(seed):
    """Mulberry32 PRNG matching the JS implementation."""
    seed = seed & 0xFFFFFFFF
    def rng():
        nonlocal seed
        seed = (seed + 0x6D2B79F5) & 0xFFFFFFFF
        t = ((seed ^ (seed >> 15)) * (1 | seed)) & 0xFFFFFFFF
        t = (t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF) ^ t) & 0xFFFFFFFF
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return rng

def shuffle_for_today(playlist, block_name, day=None):
    # Seeded by the date the block starts (matches app.js), so late night keeps
    # one order across midnight.
    now = day or datetime.now()
    day_seed = now.year * 10000 + now.month * 100 + now.day
    seed = day_seed + ord(block_name[0]) * 1000
    rng = seeded_random(seed)
    shuffled = list(playlist)
    for i in range(len(shuffled) - 1, 0, -1):
        j = int(rng() * (i + 1))
        shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
    return shuffled

def load_bumps():
    """The video bumps, from bumps/manifest.js (written by bumps/src/build.py)."""
    path = os.path.join(SCRIPT_DIR, "bumps", "manifest.js")
    if not os.path.exists(path):
        return []
    text = open(path, encoding="utf-8").read()
    m = re.search(r"window\.SG_VIDEO_BUMPS\s*=\s*(\[.*\]);", text, re.S)
    return json.loads(m.group(1)) if m else []

def bump_order(bumps, block_name, day=None):
    """Mirror of bumpOrder() in app.js: the bumps allowed in this block, shuffled
    with the block's day seed + 7919. Slot n airs order[n % len(order)]."""
    now = day or datetime.now()
    day_seed = now.year * 10000 + now.month * 100 + now.day
    rng = seeded_random(day_seed + ord(block_name[0]) * 1000 + 7919)
    order = [b for b in bumps if not b.get("blocks") or block_name in b["blocks"]]
    for i in range(len(order) - 1, 0, -1):
        j = int(rng() * (i + 1))
        order[i], order[j] = order[j], order[i]
    return order

def format_duration(secs):
    m, s = divmod(int(secs), 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h}h{m:02d}m"
    return f"{m}m"

def format_time(dt):
    return dt.strftime("%-I:%M %p").lower()

def generate_guide(show_bumps=False):
    now = datetime.now()
    bumps = load_bumps() if show_bumps else []
    today = now.strftime("%A, %B %-d, %Y")
    
    lines = []
    lines.append(f"# 📺 snow-globe — TV Guide")
    lines.append(f"**{today}**\n")
    
    # Order blocks by time of day: dead hours, morning, afternoon, evening, late night
    display_order = ["deadhours", "morning", "afternoon", "evening", "latenight"]
    
    for block_name in display_order:
        block = next(b for b in BLOCKS if b["name"] == block_name)
        
        playlist_path = os.path.join(SCRIPT_DIR, "playlists", f"{block_name}.json")
        if not os.path.exists(playlist_path):
            continue
        
        with open(playlist_path) as f:
            playlist = json.load(f)
        
        shuffled = shuffle_for_today(playlist, block_name)
        order = bump_order(bumps, block_name) if bumps else []
        
        start_hour = block["start"] if block["start"] < 24 else block["start"] - 24
        end_hour = block["end"] if block["end"] < 24 else block["end"] - 24
        
        lines.append(f"### {block['label']} ({start_hour}:00–{end_hour}:00)")
        lines.append("```")
        
        current_time = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
        if block_name == "deadhours":
            current_time = current_time  # already correct
        
        # Compute block end as a datetime for reliable comparison
        block_end = now.replace(hour=end_hour % 24, minute=0, second=0, microsecond=0)
        if block["end"] >= 24:
            block_end += timedelta(days=1)
        if block_end <= current_time:
            block_end += timedelta(days=1)
        
        # The site loops the playlist until the block ends, so the guide does too.
        i = 0
        while shuffled and current_time < block_end:
            video = shuffled[i % len(shuffled)]
            time_str = format_time(current_time)
            dur_str = format_duration(video["duration"])
            lines.append(f"  {time_str:>10}  {video['title']}  ({dur_str})")
            if order:
                lines.append(f"  {'':>10}    · bump: {order[i % len(order)]['id']}")
            current_time += timedelta(seconds=video["duration"] + BUMP_DURATION)
            i += 1
        
        lines.append("```")
        lines.append("")
    
    lines.append("*schedule reshuffles daily · same videos, new order*")
    return "\n".join(lines)

if __name__ == "__main__":
    print(generate_guide(show_bumps="--bumps" in sys.argv))
