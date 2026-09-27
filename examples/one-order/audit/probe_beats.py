"""Auditor probe: after each beat in a dry run, the opacity of one node's label glyphs and of
its outline. Tells whether fade_to (m.animate on each glyph) takes effect in the checker's run."""
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

orig_beat = vanim.Clip.beat
rows = []
census = []
NODE_TEXTS = {n["id"].replace(" ", "") for n in mod.F["nodes"]} | {"postgresql", "redis", "kafka", "orders"}


def beat(self, *a, **k):
    r = orig_beat(self, *a, **k)
    fam = [f for m in self.mobjects for f in m.get_family()]
    labels = [f for f in fam if isinstance(f, Text) and f.text in NODE_TEXTS]
    census.append((k.get("say"), len(self.mobjects), len(labels),
                   sum(1 for f in labels if max(x.get_fill_opacity() for x in f.family_members_with_points()) >= 0.3)))
    lab = None
    for m in self.mobjects:
        for f in m.get_family():
            if isinstance(f, Text) and f.text == "frontend-proxy":
                lab = f
    if lab is not None:
        g = lab.family_members_with_points()
        rows.append((k.get("say"), round(float(max(x.get_fill_opacity() for x in g)), 3)))
    return r


vanim.Clip.beat = beat
with tempconfig({"dry_run": True, "quality": "low_quality", "disable_caching": True,
                 "verbosity": "ERROR", "progress_bar": "none"}):
    mod.OneOrder().render()
for say, op in rows[:6]:
    print(f"after beat say={say!r}: 'frontend-proxy' label max glyph fill = {op}")
print("beats sampled:", len(rows), "max over all beats:", max(op for _, op in rows))
print("per beat: (say, top-level mobjects, node-label Texts in scene family, of which fill >= 0.3)")
for row in census[:8]:
    print("  ", row)
print("beats:", len(census), "peak top-level mobjects:", max(r[1] for r in census),
      "node-label Texts left after the last map beat:", [r[2] for r in census][-6:],
      "labels ever >= 0.3 as Text:", max(r[3] for r in census))
