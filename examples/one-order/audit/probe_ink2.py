"""Audit 02 probe: the new store node (lip 0.09, label shifted down 0.05) against its label.
Builds the node exactly as clip.py:88-97 does. Edits no file."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "vizln" / "anim"))
from vanim import *  # noqa: E402,F403

PX = 1080 / 8.0   # pixels per manim unit at 1080p


def measure(lines, lip, shift):
    n = node(lambda c, w, h, color: cylinder(c, w, h, color, lip=lip), (0, 0), lines, TEAL_, w=1.9, h=0.62)
    n.body.shift(DOWN * shift)
    top, bot = n.shape[3], n.shape[0]
    arc = np.array([top.point_from_proportion(i / 1999.0) for i in range(2000)])
    front = arc[arc[:, 1] <= top.get_center()[1]]          # the lower half of the top ellipse
    back = arc[arc[:, 1] > top.get_center()[1]]
    barc = np.array([bot.point_from_proportion(i / 1999.0) for i in range(2000)])
    bback = barc[barc[:, 1] >= bot.get_center()[1]]         # the upper half of the bottom ellipse
    out = {}
    for label, which in ((lines[0], n.body[0]), (lines[1], n.body[1])):
        pts = np.vstack([g.points for g in which.family_members_with_points()])
        x0, x1 = pts[:, 0].min(), pts[:, 0].max()
        f = front[(front[:, 0] >= x0) & (front[:, 0] <= x1)]
        b = bback[(bback[:, 0] >= x0) & (bback[:, 0] <= x1)]
        out[label] = dict(glyph_top=pts[:, 1].max(), glyph_bottom=pts[:, 1].min(),
                          front_lip_lowest=f[:, 1].min(), bottom_rim_highest=b[:, 1].max())
    return out


for lines in (["postgresql", "astronomy-db"], ["redis", "valkey-cart"]):
    for lip, shift, tag in ((0.13, 0.0, "audit 01 (lip 0.13, no shift)"), (0.09, 0.05, "audit 02 (lip 0.09, shift 0.05)")):
        m = measure(lines, lip, shift)
        a, b = m[lines[0]], m[lines[1]]
        print(f"{lines[0]:10} {tag}")
        print(f"   first line : glyph y {a['glyph_bottom']:.3f}..{a['glyph_top']:.3f}; front lip lowest y over its span {a['front_lip_lowest']:.3f}"
              f"  -> overlap {max(0, a['glyph_top'] - a['front_lip_lowest']) * PX:.1f} px at 1080p"
              f"  (glyph bottom below lip: {a['glyph_bottom'] < a['front_lip_lowest']})")
        print(f"   second line: glyph y {b['glyph_bottom']:.3f}..{b['glyph_top']:.3f}; bottom rim highest y over its span {b['bottom_rim_highest']:.3f}"
              f"  -> overlap {max(0, b['bottom_rim_highest'] - b['glyph_bottom']) * PX:.1f} px at 1080p")
