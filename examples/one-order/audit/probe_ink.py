"""Auditor probe: why does check.py not report the cylinder lip crossing the store label?"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "vizln" / "anim"))
from vanim import *  # noqa: E402,F403

n = node(cylinder, (0, 0), ["postgresql", "astronomy-db"], TEAL_, w=1.9, h=0.62)
top = n.shape[3]
label = n.body[0]
x0, y0, _ = label.get_corner(DL)
x1, y1, _ = label.get_corner(UR)
print("classes in cylinder:", [type(m).__name__ for m in n.shape])
print("top is Arc:", isinstance(top, Arc))
print(f"label 'postgresql' box x {x0:.3f}..{x1:.3f} y {y0:.3f}..{y1:.3f}")
pts25 = [top.point_from_proportion(i / 24.0) for i in range(25)]
inside25 = [p for p in pts25 if x0 < p[0] < x1 and y0 < p[1] < y1]
print("25 samples inside label box:", len(inside25), [(round(p[0], 3), round(p[1], 3)) for p in inside25])
pts400 = [top.point_from_proportion(i / 399.0) for i in range(400)]
inside400 = [p for p in pts400 if x0 < p[0] < x1 and y0 < p[1] < y1]
print("400 samples inside label box:", len(inside400))
ys = sorted(p[1] for p in pts400 if x0 < p[0] < x1)
print(f"lip y range across the label's x span: {ys[0]:.3f}..{ys[-1]:.3f}")
g_bottom = min(g.get_bottom()[1] for g in label.family_members_with_points())
print(f"lowest glyph point {g_bottom:.3f}")
