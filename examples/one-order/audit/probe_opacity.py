"""Auditor probe: the fill opacity the checker sees on node labels, per audit sample. Edits no file."""
import importlib.util
import os
import sys
from pathlib import Path

os.environ["VANIM_AUDIT"] = "1"
ANIM = Path(__file__).resolve().parents[3] / "vizln" / "anim"
sys.path.insert(0, str(ANIM))
from manim import tempconfig, Text  # noqa: E402
import vanim  # noqa: E402

CLIP = Path(__file__).resolve().parent.parent / "clip.py"
spec = importlib.util.spec_from_file_location("clip_under_test", CLIP)
mod = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(CLIP.parent))
spec.loader.exec_module(mod)

NAMES = ("postgresql", "frontend", "checkout", "redis", "kafka")
mx = {}
orig = vanim.Clip._audit


def audit(self):
    for m in self.mobjects:
        for f in m.get_family():
            if isinstance(f, Text) and f.text in NAMES:
                g = f.family_members_with_points()
                if g:
                    mx[f.text] = max(mx.get(f.text, 0), max(x.get_fill_opacity() for x in g))
    return orig(self)


vanim.Clip._audit = audit
with tempconfig({"dry_run": True, "quality": "low_quality", "disable_caching": True,
                 "verbosity": "ERROR", "progress_bar": "none"}):
    sc = mod.OneOrder()
    sc.render()
print("max glyph fill opacity seen at any audit sample:", {k: round(float(v), 3) for k, v in mx.items()})
fin = {}
for m in sc.mobjects:
    for f in m.get_family():
        if isinstance(f, Text) and f.text in NAMES:
            fin.setdefault(f.text, []).append(round(float(max(x.get_fill_opacity() for x in f.family_members_with_points())), 3))
print("after render:", fin)
