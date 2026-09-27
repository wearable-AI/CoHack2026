"""Auditor's independent re-derivation from evidence/ only. Does not import derive.py."""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

EX = Path(__file__).resolve().parent.parent
EV = EX / "evidence"
ORDER = "7c8c01c4-ba22-11f1-903b-b295684fc89c"


def trace(name):
    d = json.loads((EV / name).read_text())
    assert len(d["data"]) == 1, name
    return d["data"][0]


def tags(s):
    return {t["key"]: t["value"] for t in s.get("tags", [])}


CO = trace("02-jaeger-trace-a4013e836e1b.json")
AC = trace("14-jaeger-trace-d02a3f06dec1.json")
FR = trace("15-jaeger-trace-0138fcfe9e56.json")
T0 = min(s["startTime"] for s in CO["spans"])


def ms(us):
    return round((us - T0) / 1000, 1)


def svc(tr, s):
    return tr["processes"][s["processID"]]["serviceName"]


print("T0 (checkout trace min startTime, us):", T0)
roots = [s for s in CO["spans"] if not s["references"]]
for r in roots:
    print("checkout root:", r["spanID"], r["operationName"], svc(CO, r), "start_ms", ms(r["startTime"]),
          "dur_ms", round(r["duration"] / 1000, 1))

print("\n== spans per trace")
for n, tr in (("checkout", CO), ("accounting", AC), ("fraud", FR)):
    print(n, tr["traceID"][:8], len(tr["spans"]), "services", sorted({svc(tr, s) for s in tr["spans"]}))
print("total spans", len(CO["spans"]) + len(AC["spans"]) + len(FR["spans"]))

print("\n== order id tag on spans")
for n, tr in (("checkout", CO), ("accounting", AC), ("fraud", FR)):
    hits = [(svc(tr, s), s["operationName"], k, ms(s["startTime"])) for s in tr["spans"]
            for k, v in tags(s).items() if ORDER in str(v)]
    print(n, len(hits), hits[:6])
    hits_logs = [(svc(tr, s), s["operationName"]) for s in tr["spans"] for lg in s.get("logs", [])
                 for f in lg.get("fields", []) if ORDER in str(f.get("value"))]
    print(n, "span-events naming order:", len(hits_logs), hits_logs[:4])

print("\n== producer spans in checkout trace")
prod = [s for s in CO["spans"] if tags(s).get("span.kind") == "producer"]
for p in prod:
    t = tags(p)
    print(p["spanID"], svc(CO, p), p["operationName"], "start_ms", ms(p["startTime"]),
          "end_ms", ms(p["startTime"] + p["duration"]), {k: v for k, v in t.items() if k.startswith("messaging")})
PUB = prod[0]

print("\n== consumer spans, references and offsets")
for n, tr in (("accounting", AC), ("fraud", FR)):
    for s in tr["spans"]:
        t = tags(s)
        if t.get("span.kind") != "consumer":
            continue
        ff = [r for r in s["references"] if r["refType"] == "FOLLOWS_FROM"]
        print(n, s["spanID"], s["operationName"], "start", ms(s["startTime"]), "end",
              ms(s["startTime"] + s["duration"]), "offset", t.get("messaging.kafka.message.offset"),
              "partition", t.get("messaging.kafka.destination.partition", t.get("messaging.destination.partition.id")),
              "FOLLOWS_FROM", [(r["traceID"][:8], r["spanID"]) for r in ff],
              "matches publish span:", any(r["spanID"] == PUB["spanID"] and r["traceID"] == CO["traceID"] for r in ff),
              "queue_time_ms", t.get("kafka.record.queue_time_ms"))
    rt = [s for s in tr["spans"] if not s["references"]]
    for r in rt:
        print(n, "root", r["operationName"], "start", ms(r["startTime"]), "end", ms(r["startTime"] + r["duration"]))

print("\n== publish -> consume deltas (raw microseconds, rounded at the end)")
pub_us = PUB["startTime"]
ac_recv = next(s for s in AC["spans"] if s["operationName"] == "receive orders")
fr_proc = next(s for s in FR["spans"] if s["operationName"] == "process orders")
fr_recv = next(s for s in FR["spans"] if s["operationName"] == "receive orders")
print("publish start ms", ms(pub_us))
print("accounting receive END - publish start:", round((ac_recv["startTime"] + ac_recv["duration"] - pub_us) / 1000, 2))
print("accounting receive START - publish start:", round((ac_recv["startTime"] - pub_us) / 1000, 2))
print("fraud process START - publish start:", round((fr_proc["startTime"] - pub_us) / 1000, 2))
print("fraud receive END - publish start:", round((fr_recv["startTime"] + fr_recv["duration"] - pub_us) / 1000, 2))
print("clip formula, accounting: round(178.1-175.5,1) =", round(178.1 - 175.5, 1))
print("clip formula, fraud:      round(178.7-175.5,1) =", round(178.7 - 175.5, 1))

print("\n== hops, my own rule: child span whose service differs from its parent's; plus client spans to a store; "
      "plus producer; plus consumer spans with FOLLOWS_FROM")
hops = []
for tr in (CO, AC, FR):
    by = {s["spanID"]: s for s in tr["spans"]}
    for s in tr["spans"]:
        t = tags(s)
        me = svc(tr, s)
        par = next((by[r["spanID"]] for r in s["references"] if r["refType"] == "CHILD_OF" and r["spanID"] in by), None)
        if t.get("span.kind") == "producer":
            hops.append((ms(s["startTime"]), me, f"queue:{t.get('messaging.destination.name')}", "publish", s["spanID"]))
        elif t.get("span.kind") == "consumer" and any(r["refType"] == "FOLLOWS_FROM" for r in s["references"]):
            hops.append((ms(s["startTime"]), f"queue:{t.get('messaging.destination.name')}", me, "consume", s["spanID"]))
        elif t.get("db.system") or t.get("db.system.name"):
            if t.get("span.kind") == "client":
                sysn = t.get("db.system") or t.get("db.system.name")
                hops.append((ms(s["startTime"]), me, f"{sysn}:{t.get('server.address', t.get('net.peer.name', '?'))}",
                             "store", s["spanID"]))
        elif par is not None and svc(tr, par) != me:
            hops.append((ms(s["startTime"]), svc(tr, par), me, "call", s["spanID"]))
hops.sort()
print("hop count", len(hops), "distinct spans", len({h[4] for h in hops}))
print("by kind", Counter(h[3] for h in hops))
edges = Counter((h[1], h[2], h[3]) for h in hops)
print("edges", len(edges))
for (a, b, k), c in sorted(edges.items(), key=lambda kv: min(h[0] for h in hops if (h[1], h[2], h[3]) == kv[0])):
    first = min(h[0] for h in hops if (h[1], h[2], h[3]) == (a, b, k))
    print(f"  {a:>16} -> {b:<34} {k:<8} n={c:<3} first={first}")
nodes = sorted({h[1] for h in hops} | {h[2] for h in hops})
print("nodes", len(nodes), nodes)

print("\n== client->server pairs where the client span is in one service and the server child in another "
      "(this is what 'call' picks up). Parent/child pairs across services NOT picked up by a rule above:")
miss = 0
for tr in (CO,):
    by = {s["spanID"]: s for s in tr["spans"]}
    for s in tr["spans"]:
        par = next((by[r["spanID"]] for r in s["references"] if r["refType"] == "CHILD_OF" and r["spanID"] in by), None)
        if par is not None and svc(tr, par) != svc(tr, s) and s["spanID"] not in {h[4] for h in hops}:
            miss += 1
            print("  missed", svc(tr, par), "->", svc(tr, s), s["operationName"])
print("missed", miss)

print("\n== db/cache client spans by service and system")
dbs = Counter()
for tr in (CO, AC, FR):
    for s in tr["spans"]:
        t = tags(s)
        if t.get("db.system") or t.get("db.system.name"):
            dbs[(svc(tr, s), t.get("db.system") or t.get("db.system.name"), t.get("span.kind"),
                 t.get("server.address", t.get("net.peer.name")))] += 1
for k, v in dbs.items():
    print(" ", k, v)

print("\n== first time the order id appears as a span tag in the checkout trace")
first = sorted((ms(s["startTime"]), svc(CO, s), s["operationName"]) for s in CO["spans"]
               if any(ORDER in str(v) for v in tags(s).values()))
print(first[:3])
print("\n== ops of frontend-proxy server spans (the 7 entry calls)")
for s in sorted(CO["spans"], key=lambda s: s["startTime"]):
    if svc(CO, s) == "frontend-proxy":
        print("  ", ms(s["startTime"]), s["operationName"], tags(s).get("http.url", tags(s).get("url.full", ""))[:80])
