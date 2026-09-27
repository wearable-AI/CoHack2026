"""Auditor census: vocabulary of clip.py by class, in the source and at run time (from flow.json)."""
import json
import re
from collections import Counter
from pathlib import Path

EX = Path(__file__).resolve().parent.parent
src = (EX / "clip.py").read_text()
F = json.loads((EX / "flow.json").read_text())

names = ["VGroup", "Line", "Arrow", "Dot", "Circle", "Rectangle", "FadeIn", "FadeOut", "Create", "Write",
         "ShowPassingFlash", "MoveAlongPath", "TracedPath", "Transform", "always_redraw", "ValueTracker",
         "T", "node", "box", "capsule", "cylinder", "pulse", "fade_to", "fade_now", "tracker", "live_text",
         "sweep", "beat", "board", "travel", "chain", "show", "source", "animate"]
c = Counter()
for n in names:
    c[n] = len(re.findall(rf"(?<![\w.]){n}\(" if n != "animate" else r"\.animate\.", src))
print("source call sites:", {k: v for k, v in c.items() if v})
print("zero in source:", [k for k, v in c.items() if not v])

nodes = [n for n in F["nodes"] if n["kind"] != "store"]
stores_drawn = [e for e in F["edges"] if e["kind"] == "store"]
publish = F["facts"]["publish_ms"]
sync = [e for e in F["edges"] if e["first_ms"] <= publish]
after = [e for e in F["edges"] if e["first_ms"] > publish]
bursts = []
for e in sync:
    if bursts and e["first_ms"] - bursts[-1][-1]["first_ms"] <= 3.0 and e["kind"] != "publish":
        bursts[-1].append(e)
    else:
        bursts.append([e])
print("\nrun time, derived from flow.json by the clip's own loops:")
print("  boxes drawn:", len(nodes) + len(stores_drawn), f"({len(nodes)} service/queue boxes + {len(stores_drawn)} store cylinders, "
      f"one per writer; distinct nodes in flow.json = {len(F['nodes'])})")
print("  wires (Line):", len(F["edges"]))
print("  FadeIn in the first beat:", len(nodes) + len(stores_drawn) + len(F["edges"]), "+ 3 trace chips later")
print("  ShowPassingFlash (one per edge, first hop only):", len(F["edges"]), "of", len(F["hops"]), "hops")
print("  hops never individually flashed:", len(F["hops"]) - len(F["edges"]))
print("  bursts before the publish:", len(bursts), [round(b[0]["first_ms"], 1) for b in bursts])
print("  edges after the publish:", len(after), [e["first_ms"] for e in after])
print("  pulse calls at run time:", len(after))
between = [h for h in F["hops"] if 28.1 < h["t_ms"] < 104.5]
print("  hops between 28.1 and 104.5 ms (clock sweeps with no flash):", len(between))
post = [h for h in F["hops"] if h["t_ms"] > publish and h["trace"] == "a4013e83"]
print("  checkout-trace hops after the publish:", [(h["id"], h["t_ms"], h["from"], h["to"]) for h in post])
