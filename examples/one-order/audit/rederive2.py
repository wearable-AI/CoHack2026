"""Audit 02: independent re-derivation of the new order scope, from evidence/ only.
Does not import derive.py and does not read flow.json."""
import datetime as dt
import json
from collections import Counter
from pathlib import Path

EX = Path(__file__).resolve().parent.parent
EV = EX / "evidence"
ORDER = "7c8c01c4-ba22-11f1-903b-b295684fc89c"


def trace(name):
    return json.loads((EV / name).read_text())["data"][0]


def tags(s):
    return {t["key"]: t["value"] for t in s.get("tags", [])}


def iso_us(s):
    s = s.replace("Z", "+00:00")
    head, _, tail = s.partition(".")
    if tail:
        frac, _, tz = tail.partition("+")
        s = f"{head}.{(frac + '000000')[:6]}+{tz}"
    return int(dt.datetime.fromisoformat(s).timestamp() * 1_000_000)


CO = trace("02-jaeger-trace-a4013e836e1b.json")
AC = trace("14-jaeger-trace-d02a3f06dec1.json")
FR = trace("15-jaeger-trace-0138fcfe9e56.json")
svc = lambda tr, s: tr["processes"][s["processID"]]["serviceName"]
by = {s["spanID"]: s for s in CO["spans"]}
parent = {}
for s in CO["spans"]:
    p = next((r["spanID"] for r in s["references"] if r["refType"] == "CHILD_OF"), None)
    parent[s["spanID"]] = p if p in by else None
tops = [s for s in CO["spans"] if parent[s["spanID"]] is None]
kids = {}
for sid, p in parent.items():
    if p:
        kids.setdefault(p, []).append(sid)


def subtree(sid):
    out, stack = [], [sid]
    while stack:
        x = stack.pop()
        out.append(x)
        stack += kids.get(x, [])
    return out


T_SESSION = min(s["startTime"] for s in CO["spans"])
print("== top-level requests (parent absent from the trace)")
holders = []
for t in sorted(tops, key=lambda s: s["startTime"]):
    sub = subtree(t["spanID"])
    tagged = [by[x] for x in sub if tags(by[x]).get("demo.order.id") == ORDER]
    url = tags(t).get("http.url", "")
    print(f"  {t['spanID']} {svc(CO, t)} {t['operationName']:5} {url[-28:]:28} start {(t['startTime'] - T_SESSION) / 1000:6.1f} ms"
          f"  subtree {len(sub):3}  tagged {len(tagged)}  parent-ref {t['references'][0]['spanID']}")
    if tagged:
        holders.append((t, sub, tagged))
print("top-level requests:", len(tops), " holding the order id:", len(holders),
      " subtree sizes sum:", sum(len(subtree(t['spanID'])) for t in tops))
top, sub, tagged = holders[0]
T0 = top["startTime"]
ms = lambda us: round((us - T0) / 1000, 1)
print("order request offset from session start:", (T0 - T_SESSION) / 1000, "ms; spans in it:", len(sub),
      "; others:", len(CO["spans"]) - len(sub))
first_tag = min(tagged, key=lambda s: s["startTime"])
print("first tagged span:", svc(CO, first_tag), first_tag["operationName"], "at", (first_tag["startTime"] - T0) / 1000, "ms")
print("all tagged spans:", [(svc(CO, s), s["operationName"], ms(s["startTime"])) for s in tagged])

pub = next(s for s in CO["spans"] if tags(s).get("span.kind") == "producer")
print("\n== queue timing, new origin")
print("publish in the order request:", pub["spanID"] in sub, "start", (pub["startTime"] - T0) / 1000)
ac_recv = next(s for s in AC["spans"] if s["operationName"] == "receive orders")
fr_proc = next(s for s in FR["spans"] if s["operationName"] == "process orders")
fr_recv = next(s for s in FR["spans"] if s["spanID"] == next(r["spanID"] for r in fr_proc["references"] if r["refType"] == "CHILD_OF"))
for n, s in (("accounting receive", ac_recv), ("fraud receive (parent of process)", fr_recv), ("fraud process", fr_proc)):
    st, en = s["startTime"], s["startTime"] + s["duration"]
    print(f"  {n:34} start {(st - T0) / 1000:8.2f} end {(en - T0) / 1000:8.2f}  end-publish {(en - pub['startTime']) / 1000:5.2f}"
          f"  op={tags(s).get('messaging.operation')}")
for n, tr in (("checkout", CO), ("accounting", AC), ("fraud", FR)):
    e = min(tr["spans"], key=lambda s: s["startTime"])
    print(f"  earliest span {n}: {e['operationName']} at {(e['startTime'] - T0) / 1000:.1f} ms")
print("  clip formula: round(77.5-74.9,1) =", round(77.5 - 74.9, 1), " round(77.8-74.9,1) =", round(77.8 - 74.9, 1))

print("\n== hops in scope (order request subtree + both consumer traces), my rule from audit 01")
scope = [(CO, by[x]) for x in sub] + [(AC, s) for s in AC["spans"]] + [(FR, s) for s in FR["spans"]]
print("spans in scope:", len(scope))
hops = []
for tr, s in scope:
    t = tags(s)
    me = svc(tr, s)
    local = {x["spanID"]: x for x in tr["spans"]}
    par = next((local[r["spanID"]] for r in s["references"] if r["refType"] == "CHILD_OF" and r["spanID"] in local), None)
    if t.get("span.kind") == "producer":
        hops.append((ms(s["startTime"]), me, "queue", "publish", s["spanID"], tr["traceID"][:8]))
    elif t.get("span.kind") == "consumer" and any(r["refType"] == "FOLLOWS_FROM" for r in s["references"]):
        hops.append((None, "queue", me, "consume", s["spanID"], tr["traceID"][:8]))
    elif (t.get("db.system") or t.get("db.system.name")) and t.get("span.kind") == "client":
        hops.append((ms(s["startTime"]), me, f"{t.get('db.system') or t.get('db.system.name')}:{t.get('server.address')}",
                     "store", s["spanID"], tr["traceID"][:8]))
    elif par is not None and svc(tr, par) != me:
        hops.append((ms(s["startTime"]), svc(tr, par), me, "call", s["spanID"], tr["traceID"][:8]))
print("hops:", len(hops), "distinct spans:", len({h[4] for h in hops}), Counter(h[3] for h in hops))
print("spans inside one service:", len(scope) - len(hops))
edges = {}
for h in hops:
    edges.setdefault((h[1], h[2]), []).append(h)
print("edges:", len(edges))
for (a, b), hs in edges.items():
    ts = [h[0] for h in hs if h[0] is not None]
    print(f"  {a:>16} -> {b:<26} n={len(hs)} first={min(ts) if ts else 'consume'} traces={sorted({h[5] for h in hs})}")
print("nodes:", len({h[1] for h in hops} | {h[2] for h in hops}))
store_first = {}
for h in sorted([h for h in hops if h[3] == "store"], key=lambda h: h[0]):
    store_first.setdefault((h[1], h[2]), h[5])
print("store copy -> trace of its first write:", store_first)
post = sorted(h for h in hops if h[0] is not None and h[0] > ms(pub["startTime"]) and h[5] == "a4013e83")
print("checkout-trace hops after the publish:", [(h[0], h[1], h[2]) for h in post])

print("\n== log lines naming the order, new origin; trace ids they carry")
o16 = json.loads((EV / "16-opensearch-by-order.json").read_text())["hits"]["hits"]
for h in o16:
    s = h["_source"]
    print(f"  {ms(iso_us(s['@timestamp'])):6} opensearch {s['resource']['service.name']:16} trace {s.get('traceId', '')[:8]}")
for e in json.loads((EV / "18-cloudlogging-by-order.json").read_text()):
    print(f"  {ms(iso_us(e['timestamp'])):6} cloud-log  {e['resource']['labels']['container_name']:16} trace field: {e.get('trace', 'absent')}"
          f"  text has a trace id: {'trace_id=' in e.get('textPayload', '')}")

print("\n== the six lines stamped 1970: @timestamp vs observedTimestamp, and the matching spans")
o17 = json.loads((EV / "17-opensearch-by-trace.json").read_text())["hits"]["hits"]
lags = []
for h in o17:
    s = h["_source"]
    if s["@timestamp"].startswith("1970"):
        print(f"  {s['resource']['service.name']:9} {str(s['body'])[:22]:22} observed {ms(iso_us(s['observedTimestamp'])):7} ms  span {s.get('spanId')}"
              f"  span start {ms(by[s['spanId']]['startTime']) if s.get('spanId') in by else 'n/a'}")
    else:
        lags.append((iso_us(s["observedTimestamp"]) - iso_us(s["@timestamp"])) / 1000)
print(f"  observed minus event time on the other {len(lags)} lines: min {min(lags):.1f} ms, max {max(lags):.1f} ms")
