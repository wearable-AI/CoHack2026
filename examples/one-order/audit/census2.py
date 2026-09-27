"""Audit 02 census: bursts, flashes and unflashed hops in the new flow.json, by the clip's own loops."""
import json
from pathlib import Path

EX = Path(__file__).resolve().parent.parent
F = json.loads((EX / "flow.json").read_text())
pub = F["facts"]["publish_ms"]
sync = [e for e in F["edges"] if e["first_ms"] <= pub]
after = [e for e in F["edges"] if e["first_ms"] > pub]
bursts = []
for e in sync:
    if bursts and e["first_ms"] - bursts[-1][-1]["first_ms"] <= 3.0 and e["kind"] != "publish":
        bursts[-1].append(e)
    else:
        bursts.append([e])
print("edges", len(F["edges"]), "hops", len(F["hops"]), "flashed", len(F["edges"]), "never flashed", len(F["hops"]) - len(F["edges"]))
print("bursts before the publish:", len(bursts))
for b in bursts:
    print(f"  clock stops at {b[0]['first_ms']:5}  lights: " + ", ".join(f"{e['from']}->{e['to']} ({e['first_ms']})" for e in b))
print("after the publish:", [(e["from"], e["to"], e["first_ms"]) for e in after])
stops = [b[0]["first_ms"] for b in bursts] + [e["first_ms"] for e in after]
gaps = []
for a, b in zip([0.0] + stops, stops):
    inside = [h["id"] for h in F["hops"] if a < h["t_ms"] < b]
    gaps.append((b - a, a, b, len(inside)))
g = max(gaps)
print(f"widest sweep: {g[1]} -> {g[2]} ms ({g[0]:.1f} ms), hops inside it that do not flash: {g[3]}")
print("sum of hops inside sweeps:", sum(x[3] for x in gaps))
