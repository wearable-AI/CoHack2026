"""Derive: build flow.json from the saved evidence only. No network, no source code.

    python3 derive.py <capture-dir>

Reads capture.json and evidence/, writes flow.json and DERIVATION.md next to them.
Every join is asserted. The script exits 1 if one fails, and writes nothing.
"""
import datetime as dt
import json
import sys
from pathlib import Path


def tag(span, *keys):
    tags = {t["key"]: t["value"] for t in span.get("tags", [])}
    return next((tags[k] for k in keys if k in tags), None)


def iso_us(s):
    """ISO time with up to nanoseconds, to epoch microseconds."""
    s = s.replace("Z", "+00:00")
    head, _, rest = s.partition(".")
    if rest:
        frac, tz = rest[:rest.index("+")] if "+" in rest else rest, rest[rest.index("+"):] if "+" in rest else ""
        s = f"{head}.{frac[:6].ljust(6, '0')}{tz}"
    return int(dt.datetime.fromisoformat(s).timestamp() * 1_000_000)


def short(x):
    return x[:8]


def main():
    base = Path(sys.argv[1])
    cap = json.loads((base / "capture.json").read_text())
    steps = {s["file"]: s for s in cap["steps"] if s["file"]}
    order = cap["order_id"]
    joins, fails = [], []

    def check(what, ok, got, evidence):
        joins.append({"what": what, "ok": bool(ok), "got": got, "evidence": evidence})
        if not ok:
            fails.append(what)

    # ---- traces ------------------------------------------------------------
    traces = {}
    for f in steps:
        if "jaeger-trace-" in f:
            t = json.loads((base / f).read_text())["data"][0]
            traces[t["traceID"]] = (t, f)
    tid = cap["checkout_trace"]
    order_of = {x["trace"]: x["service"] for x in cap["linked_traces"]}
    ckt, ckt_file = traces[tid]

    # ---- scope: a shopper's session can share one trace across many requests.
    # The order is the one top-level request whose subtree holds the order id.
    ck = {s["spanID"]: s for s in ckt["spans"]}

    def up(s):
        while True:
            p = next((r["spanID"] for r in s.get("references", []) if r["refType"] == "CHILD_OF"), None)
            if p not in ck:
                return s
            s = ck[p]

    tagged = [s for s in ckt["spans"] if tag(s, "demo.order.id") == order]
    tops = {up(s)["spanID"] for s in ckt["spans"]}
    holders = {up(s)["spanID"] for s in tagged}
    check("exactly one top-level request in the trace holds the order id", len(holders) == 1,
          f"{len(holders)} of {len(tops)} top-level requests", ckt_file)
    req = ck[next(iter(holders))]
    in_order = {s["spanID"] for s in ckt["spans"] if up(s)["spanID"] == req["spanID"]}
    order_span = min(tagged, key=lambda s: s["startTime"])
    t0 = req["startTime"]

    def ms(us):
        return round((us - t0) / 1000, 1)

    spans, language = {}, {}
    for trid, (t, f) in traces.items():
        proc = {k: v["serviceName"] for k, v in t["processes"].items()}
        for p in t["processes"].values():
            lang = next((g["value"] for g in p.get("tags", []) if g["key"] == "telemetry.sdk.language"), None)
            if lang:
                language[p["serviceName"]] = lang
        for s in t["spans"]:
            spans[s["spanID"]] = dict(s, svc=proc[s["processID"]], trace=trid, file=f)

    check("the checkout trace carries the order id",
          any(tag(s, "demo.order.id") == order for s in ckt["spans"]),
          f"demo.order.id={order} on trace {short(tid)}", ckt_file)

    producers = [s for s in spans.values() if s["spanID"] in in_order and tag(s, "span.kind") == "producer"]
    check("checkout published the order to a queue", len(producers) == 1,
          f"{len(producers)} producer span(s)", ckt_file)
    pub = producers[0]
    queue = f"{tag(pub, 'messaging.system')} · {tag(pub, 'messaging.destination.name')}"

    # ---- hops: every call that crosses a boundary, inside the order's scope ----
    hops = []
    for s in spans.values():
        if s["trace"] == tid and s["spanID"] not in in_order:
            continue
        parent = next((spans.get(r["spanID"]) for r in s.get("references", [])
                       if r["refType"] == "CHILD_OF"), None)
        cite = {"file": s["file"], "span": s["spanID"]}
        if parent and parent["svc"] != s["svc"]:
            hops.append({"from": parent["svc"], "to": s["svc"], "kind": "call", "op": s["operationName"],
                         "t_ms": ms(s["startTime"]), "dur_ms": round(s["duration"] / 1000, 1),
                         "trace": short(s["trace"]), "cite": cite})
        db = tag(s, "db.system.name", "db.system")
        if db and tag(s, "span.kind") == "client":
            store = f"{db} · {tag(s, 'server.address', 'db.namespace') or db}"
            hops.append({"from": s["svc"], "to": store, "kind": "store", "op": s["operationName"],
                         "t_ms": ms(s["startTime"]), "dur_ms": round(s["duration"] / 1000, 1),
                         "trace": short(s["trace"]), "cite": cite})
    hops.append({"from": pub["svc"], "to": queue, "kind": "publish", "op": pub["operationName"],
                 "t_ms": ms(pub["startTime"]), "dur_ms": round(pub["duration"] / 1000, 1),
                 "trace": short(tid), "cite": {"file": ckt_file, "span": pub["spanID"]}})

    offsets = {}
    for trid, svc in order_of.items():
        t, f = traces[trid]
        link = next(((s, r) for s in t["spans"] for r in s.get("references", [])
                     if r["refType"] == "FOLLOWS_FROM"), (None, None))
        s, r = link
        check(f"the {svc} trace links back to checkout's queue span",
              r is not None and r["spanID"] == pub["spanID"] and r["traceID"] == tid,
              f"FOLLOWS_FROM {short(r['spanID']) if r else 'none'} = publish span {short(pub['spanID'])}", f)
        consumer = spans[s["spanID"]]
        offsets[svc] = tag(consumer, "messaging.kafka.message.offset")
        # One rule for every consumer: the order is in hand when the receive span ends.
        # A receive span covers the blocking poll, so it can open before the message
        # exists. Use the linked span if it is the receive, else its receive ancestor.
        rcv = consumer
        while rcv is not None and tag(rcv, "messaging.operation") != "receive":
            rcv = next((spans.get(r["spanID"]) for r in rcv.get("references", []) if r["refType"] == "CHILD_OF"), None)
        start, end = consumer["startTime"], consumer["startTime"] + consumer["duration"]
        if rcv is not None:
            at = rcv["startTime"] + rcv["duration"]
            rule = ("the receive span ends: the message is in hand" if rcv is consumer else
                    f"its parent receive span ends: the message is in hand, before `{consumer['operationName']}` starts")
        else:
            at, rule = start, "no receive span: the linked span starts after the message arrived"
        check(f"{svc} has the order only after checkout published it",
              at >= pub["startTime"], f"{svc} at {ms(at)} ms, publish at {ms(pub['startTime'])} ms", f)
        hops.append({"from": queue, "to": svc, "kind": "consume", "op": consumer["operationName"],
                     "t_ms": ms(at), "t_rule": rule, "span_start_ms": ms(start), "span_end_ms": ms(end),
                     "dur_ms": round(consumer["duration"] / 1000, 1),
                     "trace": short(trid), "cite": {"file": f, "span": consumer["spanID"]}})
    if len(offsets) > 1:
        check("the consumers read the same Kafka message", len(set(offsets.values())) == 1,
              ", ".join(f"{k} offset {v}" for k, v in offsets.items()), "consumer spans")
    hops.sort(key=lambda h: h["t_ms"])
    for i, h in enumerate(hops, 1):
        h["id"] = f"h{i:02d}"
    check("each hop comes from a different span", len({h["cite"]["span"] for h in hops}) == len(hops),
          f"{len(hops)} hops, {len({h['cite']['span'] for h in hops})} distinct spans", "all traces")

    # ---- logs ----------------------------------------------------------------
    logs, seen = [], set()
    ids = set(traces)
    for f, s in steps.items():
        if s["source"] == "opensearch":
            for hit in json.loads((base / f).read_text())["hits"]["hits"]:
                if hit["_id"] in seen:
                    continue
                seen.add(hit["_id"])
                src = hit["_source"]
                res = src.get("resource", {})
                attrs = src.get("attributes", {}) or {}
                body = str(src.get("body", ""))
                field = "body" if order in body else next(
                    (f"attributes.{k}" for k, v in attrs.items() if order in json.dumps(v)), None)
                # some SDKs send no event time, and OpenSearch then stores 1970-01-01
                when, time_field = src["@timestamp"], "@timestamp"
                if when.startswith("1970-01-01") and src.get("observedTimestamp"):
                    when, time_field = src["observedTimestamp"], "observedTimestamp"
                logs.append({"store": "opensearch", "service": res.get("service.name") or res.get("service", {}).get("name"),
                             "t_ms": ms(iso_us(when)), "time_field": time_field, "text": body[:160],
                             "trace": short(src.get("traceId") or "") or None,
                             "names_order": field is not None, "order_field": field,
                             "cite": {"file": f, "id": hit["_id"]}})
        elif s["source"] == "cloud-logging":
            for e in json.loads((base / f).read_text() or "[]"):
                text = (e.get("textPayload") or json.dumps(e.get("jsonPayload", ""))).strip()
                logs.append({"store": "cloud-logging", "service": e["resource"]["labels"]["container_name"],
                             "t_ms": ms(iso_us(e["timestamp"])), "text": text[:160], "trace": None,
                             "names_order": order in text, "order_field": "textPayload" if order in text else None,
                             "cite": {"file": f, "id": e["insertId"]}})
        elif s["source"] == "pod-stdout":
            for row in json.loads((base / f).read_text()):
                logs.append({"store": "pod-stdout", "service": row["service"], "t_ms": None,
                             "text": row["text"][:160], "trace": None, "names_order": order in row["text"],
                             "cite": {"file": f, "line": row["line"]}})
    logs.sort(key=lambda x: (x["t_ms"] is None, x["t_ms"] or 0))

    for f, s in steps.items():
        if s["question"].endswith("contain the order id") or "contain the order id" in s["question"]:
            mine = [x for x in logs if x["cite"]["file"] == f]
            check(f"every {s['source']} line found by order id really names it",
                  all(x["names_order"] for x in mine), f"{sum(x['names_order'] for x in mine)} of {len(mine)}", f)
    by_trace = [x for x in logs if x["store"] == "opensearch" and x["trace"]]
    check("every OpenSearch line with a trace id belongs to one of the order's traces",
          all(any(t.startswith(x["trace"]) for t in ids) for x in by_trace),
          f"{len(by_trace)} lines, trace ids in {sorted(short(t) for t in ids)}", "opensearch files")
    for trid, svc in order_of.items():
        mine = [x for x in logs if x["trace"] == short(trid) and x["names_order"]]
        check(f"the order id also reaches the {svc} trace: a log line names the order and carries that trace id",
              len(mine) > 0, f"{len(mine)} line(s), store {', '.join(sorted({x['store'] for x in mine})) or 'none'}",
              "opensearch files")

    if fails:
        for j in joins:
            print(("PASS " if j["ok"] else "FAIL ") + j["what"] + " | " + j["got"])
        sys.exit(f"{len(fails)} join(s) failed; flow.json not written")

    # ---- structure, computed from the hops ----------------------------------
    nodes = {}
    for h in hops:
        for n in (h["from"], h["to"]):
            nodes.setdefault(n, {"id": n, "first_ms": h["t_ms"]})
            nodes[n]["first_ms"] = min(nodes[n]["first_ms"], h["t_ms"])
    for n in nodes.values():
        n["kind"] = ("queue" if n["id"] == queue else "store" if " · " in n["id"] else "service")
        if n["id"] in language:
            n["language"] = language[n["id"]]   # the process's telemetry.sdk.language
    # depth: the longest chain of calls that reaches a box, so each callee sits to
    # the right of all its callers
    depth = {n: 0 for n in nodes}
    for _ in range(len(nodes) + 1):
        moved = False
        for h in hops:
            if depth[h["to"]] < depth[h["from"]] + 1:
                depth[h["to"]] = depth[h["from"]] + 1
                moved = True
        if not moved:
            break
    else:
        sys.exit("the call graph has a cycle, so depth is undefined")
    for n in nodes.values():
        n["depth"] = depth.get(n["id"], 0)
    edges = {}
    for h in hops:
        e = edges.setdefault((h["from"], h["to"]), {"from": h["from"], "to": h["to"], "kind": h["kind"],
                                                    "count": 0, "first_ms": h["t_ms"], "hops": []})
        e["count"] += 1
        e["hops"].append(h["id"])

    stores = {}
    for st in ("opensearch", "cloud-logging", "pod-stdout"):
        mine = [x for x in logs if x["store"] == st and x["names_order"]]
        if any(x["store"] == st for x in logs):
            stores[st] = {"lines_naming_order": len(mine),
                          "services": sorted({x["service"] for x in mine})}
    trace_rows = []
    consume_at = {h["trace"]: h["t_ms"] for h in hops if h["kind"] == "consume"}
    for trid, (t, f) in traces.items():
        proc = {k: v["serviceName"] for k, v in t["processes"].items()}
        root = min(t["spans"], key=lambda s: s["startTime"])
        mine = [s for s in t["spans"] if trid != tid or s["spanID"] in in_order]
        trace_rows.append({"id": trid, "short": short(trid), "role": "checkout" if trid == tid else order_of[trid],
                           "spans": len(t["spans"]), "order_spans": len(mine),
                           "services": sorted({proc[s["processID"]] for s in mine}),
                           "order_ms": ms(order_span["startTime"]) if trid == tid else consume_at[short(trid)],
                           "root_op": root["operationName"], "root_opened_ms": ms(root["startTime"])})
    trace_rows.sort(key=lambda r: r["order_ms"])
    spans_total = sum(r["spans"] for r in trace_rows)
    spans_scope = sum(r["order_spans"] for r in trace_rows)

    flow = {
        "order_id": order, "order_short": short(order), "cluster": cap["cluster"],
        "captured_at": cap["captured_at"],
        "traces": trace_rows,
        "nodes": sorted(nodes.values(), key=lambda n: (n["depth"], n["first_ms"])),
        "edges": sorted(edges.values(), key=lambda e: e["first_ms"]),
        "hops": hops,
        "logs": logs,
        "stores": {"jaeger": {"traces": len(trace_rows), "spans": spans_total}, **stores},
        "scope": {"rule": "the one top-level request in the checkout trace whose subtree holds demo.order.id",
                  "top_level_requests": len(tops), "order_request_spans": len(in_order),
                  "other_request_spans": len(ckt["spans"]) - len(in_order),
                  "order_request_op": f"{spans[req['spanID']]['svc']} {req['operationName']}",
                  "order_request_offset_ms": round((req["startTime"] - min(s["startTime"] for s in ckt["spans"])) / 1000, 1)},
        "facts": {"spans_total": spans_total, "spans_in_scope": spans_scope, "hops": len(hops),
                  "spans_inside_one_service": spans_scope - len(hops),
                  "publish_ms": next(h["t_ms"] for h in hops if h["kind"] == "publish"),
                  "consume_ms": {h["to"]: h["t_ms"] for h in hops if h["kind"] == "consume"},
                  "checkout_ms": next(h["dur_ms"] for h in hops if h["op"].endswith("PlaceOrder") and h["to"] == "checkout"),
                  "queue": queue, "evidence_files": len(steps), "questions": len(cap["steps"]),
                  "publish_span": short(pub["spanID"]), "kafka_offsets": offsets,
                  "joins_passed": len(joins)},
        "joins": joins,
    }
    (base / "flow.json").write_text(json.dumps(flow, indent=1))
    (base / "DERIVATION.md").write_text(report(cap, flow))
    print(f"flow.json: {len(nodes)} nodes, {len(edges)} edges, {len(hops)} hops, {len(logs)} log lines, "
          f"{len(joins)} joins, all passed")


def report(cap, f):
    L = [f"# How flow.json was made", "",
         f"Order `{f['order_id']}`, captured {f['captured_at']} from the `{f['cluster']}` cluster.",
         "No source code was read. Every service, edge, time and count below comes from the runtime",
         "data in `evidence/`, which the capture step saved unedited.", "",
         "## 0. What counts as the order", "",
         f"The checkout trace holds {f['scope']['top_level_requests']} top-level requests: the shopper's whole "
         f"session shares one trace. The order is the one request whose subtree holds `demo.order.id`: "
         f"`{f['scope']['order_request_op']}`, {f['scope']['order_request_spans']} spans, which began "
         f"{f['scope']['order_request_offset_ms']} ms into the trace. The other "
         f"{f['scope']['other_request_spans']} spans are browsing and cart requests, and are left out.",
         "The top-level requests all name a parent that is not in the trace: the shopper's own span",
         "was never exported, so the session's origin is not in the evidence.",
         "All times below are milliseconds after that request began.", "",
         "## Limits", "",
         "- **Three traces is a lower bound.** The consumer search asked only the services that are not",
         "  in the checkout trace, for 300 s after the order, up to 500 traces each, and it kept only the",
         "  counts of those answers. A linked trace in a service inside the checkout trace was not sought.",
         "- **Cloud Logging was searched in `textPayload` only.** A line with the id in `jsonPayload` would",
         "  not match. So \"none from checkout\" holds for text lines.",
         "- **Cross-node times include clock offset.** Services on different nodes stamp their own spans,",
         "  and nothing here measures the offset between node clocks.",
         "- **The clip lights each edge once, at its first hop.** Every hop is listed in section 7.", ""]
    L += [
         "## 1. What the agent asked, and what came back", "",
         "| # | Store | Question | Answer | Kept as |", "|---|---|---|---|---|"]
    for s in cap["steps"]:
        L.append(f"| {s['n']} | {s['source']} | {s['question']} | {s['count']} | "
                 f"{'`' + s['file'] + '`' if s['file'] else 'count only'} |")
    L += ["", "## 2. How the pieces were joined", ""]
    for j in f["joins"]:
        L.append(f"- {'PASS' if j['ok'] else 'FAIL'}: {j['what']}. {j['got']} (`{j['evidence']}`)")
    L += ["", "## 3. The three traces", "",
          "Checkout's time is the first span tagged with the order id. A consumer's time is the moment",
          "it had the order, by the rule in section 6. A consumer's root span opened before that: it waits.",
          "So the consumers' traces were already open. The order entered them, it did not start them.", "",
          "| Trace | Role | Spans (in the order's scope) | Has the order at | Earliest span, opened at | Services |",
          "|---|---|---|---|---|---|"]
    for t in f["traces"]:
        L.append(f"| `{t['short']}` | {t['role']} | {t['spans']} ({t['order_spans']}) | {t['order_ms']} ms | "
                 f"`{t['root_op']}`, {t['root_opened_ms']} ms | {', '.join(t['services'])} |")
    fx = f["facts"]
    L += ["", "## 4. What was kept, and what was collapsed", "",
          f"{fx['spans_in_scope']} spans in the order's scope became {fx['hops']} hops between {len(f['nodes'])} nodes. "
          f"A hop is a call that crosses from one service to another, a write to a store, the queue "
          f"publish, or a queue read. {fx['spans_inside_one_service']} spans stayed inside one service "
          f"and are not drawn.", "",
          "## 5. Where the order's log lines are", "", "| Store | Lines that name the order | Services |", "|---|---|---|"]
    for k, v in f["stores"].items():
        if k != "jaeger":
            L.append(f"| {k} | {v['lines_naming_order']} | {', '.join(v['services'])} |")
    L += ["", "| ms | Store | Service | Field that names the order | Text |", "|---|---|---|---|---|"]
    for x in f["logs"]:
        if x["names_order"]:
            L.append(f"| {x['t_ms']} | {x['store']} | {x['service']} | `{x.get('order_field')}` | "
                     f"{x['text'][:70].replace('|', '/')} |")
    L += ["", "## 6. The queue hop", ""]
    for h in f["hops"]:
        if h["kind"] in ("publish", "consume"):
            extra = (f" Span {h['span_start_ms']} to {h['span_end_ms']} ms. Rule: {h['t_rule']}."
                     if h["kind"] == "consume" else "")
            L.append(f"- {h['t_ms']} ms: {h['from']} → {h['to']} (`{h['op']}`, trace `{h['trace']}`).{extra}")
    L += ["", "## 7. Every hop, in time order", "", "| Hop | ms | From | To | Kind | Trace |",
          "|---|---|---|---|---|---|"]
    for h in f["hops"]:
        L.append(f"| {h['id']} | {h['t_ms']} | {h['from']} | {h['to']} | {h['kind']} | `{h['trace']}` |")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()
