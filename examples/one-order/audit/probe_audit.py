"""Auditor probe: run OneOrder the way check.py does, but log what each _audit call sees.
Monkeypatches in this process only. Edits no file."""
import importlib.util
import os
import sys
from collections import Counter
from pathlib import Path

os.environ["VANIM_AUDIT"] = "1"
ANIM = Path(__file__).resolve().parents[3] / "vizln" / "anim"
sys.path.insert(0, str(ANIM))
from manim import tempconfig, Line, Arc, Dot, Text  # noqa: E402
import vanim  # noqa: E402

CLIP = Path(__file__).resolve().parent.parent / "clip.py"
spec = importlib.util.spec_from_file_location("clip_under_test", CLIP)
mod = importlib.util.module_from_spec(spec)
sys.path.insert(0, str(CLIP.parent))
spec.loader.exec_module(mod)

log = Counter()
widths = Counter()
orig_audit = vanim.Clip._audit
orig_ink = vanim.Clip._audit_ink
seen = {"store_labels_checked": 0, "arcs_max": 0, "texts_max": 0}
checked = set()


def audit(self):
    cam = self.camera.frame
    widths[round(cam.width, 2)] += 1
    log["_audit calls"] += 1
    return orig_audit(self)


def ink(self, onscreen, here_board):
    log["_audit_ink calls"] += 1
    paths = self._leaves((Line, Arc), here_board, exclude=(Dot,))
    arcs = [p for p in paths if type(p).__name__ == "Ellipse" and p.get_stroke_opacity() >= 0.3]
    seen["arcs_max"] = max(seen["arcs_max"], len(arcs))
    seen["texts_max"] = max(seen["texts_max"], len(onscreen))
    if any(t.text in ("postgresql", "redis") for t in onscreen):
        seen["store_labels_checked"] += 1
    for t in onscreen:
        checked.add(t.text)
    allt = [t.text for t in self._visible_texts()]
    if "postgresql" in allt:
        log["postgresql visible (fill>=0.3)"] += 1
    return orig_ink(self, onscreen, here_board)


vanim.Clip._audit = audit
vanim.Clip._audit_ink = ink

with tempconfig({"dry_run": True, "quality": "low_quality", "disable_caching": True,
                 "verbosity": "ERROR", "progress_bar": "none"}):
    mod.OneOrder().render()

print(dict(log))
print("camera widths seen by _audit:", dict(widths), "FRAME_W =", vanim.FRAME_W)
print(seen)
print("hits:", vanim.AUDIT_HITS)
print("distinct strings the text checks ever tested:", len(checked))
for s in sorted(checked):
    print("   ", repr(s))
