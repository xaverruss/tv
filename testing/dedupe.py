"""Dedupe an M3U using an rtsp_sweep.py report.

Keeps the single best-measured (highest kB/s) entry per channel name and drops
the rest, so playlists from repeated scans only keep one working stream each.

Usage: python3 dedupe.py <playlist.m3u> <sweep-output.txt>   (rewrites in place)
"""
import re, sys

src = sys.argv[1]
sweep = sys.argv[2]

kb = {}
for ln in open(sweep):
    m = re.match(r"\s*(\d+)\s+.*?\s(\d+)\s+\d+qam\s+(\d+)\s+True\s+True", ln)
    if m:
        kb[int(m.group(1))] = int(m.group(3))

lines = open(src).read().splitlines()
blocks = []
i = idx = 0
while i < len(lines):
    if lines[i].startswith("#EXTINF:"):
        blk = [lines[i]]
        i += 1
        while i < len(lines) and not lines[i].startswith("#EXTINF:") and not lines[i].startswith("#EXTM3U"):
            blk.append(lines[i])
            i += 1
        idx += 1
        blocks.append((idx, blk[0].split(",", 1)[1], blk))
    else:
        i += 1

best = {}
for idx, name, blk in blocks:
    k = kb.get(idx, -1)
    if name not in best or k > best[name][1]:
        best[name] = (idx, k)
keep = {idx for idx, _ in best.values()}

out = ["#EXTM3U"]
removed = []
for idx, name, blk in blocks:
    if idx in keep:
        out += blk
    else:
        removed.append((idx, name, kb.get(idx, -1), best[name][1]))
open(src, "w").write("\n".join(out) + "\n")
print(f"{src}: {len(blocks)} -> {len(keep)} kept, {len(removed)} removed")
for idx, name, k, bk in removed:
    print(f"  idx{idx:>4} {name:<24} {k:>5} kB/s (kept {bk})")
