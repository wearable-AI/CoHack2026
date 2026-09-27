"""Auditor: how long the on-screen clock holds one value. Tolerant pixel diff, 60 fps."""
from pathlib import Path

import numpy as np

raw = np.fromfile(Path(__file__).parent / "clock.gray", dtype=np.uint8).reshape(-1, 50, 300).astype(int)
changed = [False] + [int((np.abs(raw[i] - raw[i - 1]) > 60).sum()) > 8 for i in range(1, len(raw))]
lit = [int((f > 90).sum()) > 20 for f in raw]
runs, start = [], 0
for i in range(1, len(raw) + 1):
    if i == len(raw) or changed[i]:
        runs.append((start, i - start, lit[start]))
        start = i
print("frames", len(raw), "value changes", sum(changed))
print("holds of 0.5 s or longer while the clock is on screen (start s, length s):")
for s, n, on in runs:
    if n >= 30 and on:
        print(f"  {s / 60:6.2f}  {n / 60:5.2f}")
print("longest hold on screen:", max(n for s, n, on in runs if on) / 60, "s")
first_on = next(i for i, v in enumerate(lit) if v)
last_on = len(lit) - 1 - next(i for i, v in enumerate(reversed(lit)) if v)
print(f"clock on screen from {first_on / 60:.2f} s to {last_on / 60:.2f} s")
