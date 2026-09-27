"""Capture: ask the running system about one order, and keep every answer unedited.

Runtime only. No source code is read. Each question and its answer are recorded in
capture.json, including the questions that found nothing, so a reader can repeat them.

    python3 capture.py --jaeger URL --opensearch URL --out DIR [--order ID | --latest]
                       [--logs gcloud --gcp-project P | --logs kubectl --kube-context C]
"""
import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

NAMESPACE = "astronomy"


class Capture:
    def __init__(self, out):
        self.out = Path(out)
        (self.out / "evidence").mkdir(parents=True, exist_ok=True)
        self.steps = []

    def keep(self, source, question, request, name, body, count):
        """Write one answer to evidence/ as it came back, and record the step."""
        n = len(self.steps) + 1
        path = self.out / "evidence" / f"{n:02d}-{name}"
        raw = body if isinstance(body, bytes) else body.encode()
        path.write_bytes(raw)
        self.steps.append({"n": n, "source": source, "question": question, "request": request,
                           "file": f"evidence/{path.name}", "bytes": len(raw),
                           "sha256": hashlib.sha256(raw).hexdigest(), "count": count})
        print(f"{n:2d} {source:13} {question} -> {count}")
        return path

    def note(self, source, question, request, count):
        """A question whose answer is not kept, because only its count is used later."""
        n = len(self.steps) + 1
        self.steps.append({"n": n, "source": source, "question": question,
                           "request": request, "file": None, "count": count})
        print(f"{n:2d} {source:13} {question} -> {count} (not kept)")


def fetch(url, body=None):
    req = urllib.request.Request(url)
    if body is not None:
        req.add_header("Content-Type", "application/json")
        req.data = json.dumps(body).encode()
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def tag(span, key):
    return next((t["value"] for t in span.get("tags", []) if t["key"] == key), None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jaeger", required=True, help="Jaeger query API base, ending in /api")
    ap.add_argument("--opensearch", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--order")
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--logs", choices=["gcloud", "kubectl", "none"], default="none")
    ap.add_argument("--gcp-project")
    ap.add_argument("--kube-context")
    ap.add_argument("--cluster", default="unknown", help="a label for capture.json")
    ap.add_argument("--window-s", type=int, default=300,
                    help="how long after the order to look for consumer traces")
    a = ap.parse_args()
    if not (a.order or a.latest):
        sys.exit("give --order ID or --latest")

    c = Capture(a.out)
    J = a.jaeger.rstrip("/")

    # 1. find the order's checkout trace
    if a.latest:
        q = {"service": "checkout", "operation": "oteldemo.CheckoutService/PlaceOrder",
             "limit": 20, "lookback": "15m"}
        question = "the most recent checkout traces"
    else:
        q = {"service": "checkout", "tags": json.dumps({"demo.order.id": a.order}),
             "limit": 5, "lookback": "6h"}
        question = f"checkout traces tagged demo.order.id={a.order}"
    url = f"{J}/traces?{urllib.parse.urlencode(q)}"
    raw = fetch(url)
    found = json.loads(raw)["data"]
    with_id = [t for t in found if any(tag(s, "demo.order.id") for s in t["spans"])]
    c.keep("jaeger", question, "GET " + url, "jaeger-search-checkout.json", raw, len(with_id))
    if not with_id:
        sys.exit("no checkout trace carries demo.order.id")
    trace = max(with_id, key=lambda t: min(s["startTime"] for s in t["spans"]))
    order = next(tag(s, "demo.order.id") for s in trace["spans"] if tag(s, "demo.order.id"))
    tid = trace["traceID"]

    # 2. the whole checkout trace
    url = f"{J}/traces/{tid}"
    raw = fetch(url)
    trace = json.loads(raw)["data"][0]
    c.keep("jaeger", f"the full trace {tid}", "GET " + url, f"jaeger-trace-{tid[:12]}.json", raw,
           len(trace["spans"]))
    pub = [s for s in trace["spans"] if tag(s, "span.kind") == "producer"]
    t_start = min(s["startTime"] for s in trace["spans"])
    in_trace = {trace["processes"][s["processID"]]["serviceName"] for s in trace["spans"]}

    # 3. which other traces point back at this one? ask every service Jaeger knows,
    #    in a window after the order, and keep only traces with a link to this trace.
    url = f"{J}/services"
    services = sorted(json.loads(fetch(url))["data"])
    c.note("jaeger", "the services Jaeger has seen", "GET " + url, len(services))
    linked = []
    for svc in services:
        if svc in in_trace:
            continue
        q = {"service": svc, "start": t_start, "end": t_start + a.window_s * 1_000_000, "limit": 500}
        url = f"{J}/traces?{urllib.parse.urlencode(q)}"
        got = json.loads(fetch(url))["data"]
        hits = [t for t in got
                if any(r["refType"] == "FOLLOWS_FROM" and r["traceID"] == tid
                       for s in t["spans"] for r in s.get("references", []))]
        c.note("jaeger", f"{svc} traces in the {a.window_s}s after the order that link to {tid[:12]}",
               "GET " + url, len(hits))
        linked += [(svc, t["traceID"]) for t in hits]

    # 4. the whole linked traces
    for svc, ltid in linked:
        url = f"{J}/traces/{ltid}"
        raw = fetch(url)
        c.keep("jaeger", f"the full {svc} trace {ltid}", "GET " + url,
               f"jaeger-trace-{ltid[:12]}.json", raw, len(json.loads(raw)["data"][0]["spans"]))

    # 5. OpenSearch: lines that name the order, and lines tied to any of the traces
    OS = a.opensearch.rstrip("/")
    for what, qs in [("log lines that contain the order id", f'"{order}"'),
                     ("log lines with one of the trace ids",
                      " OR ".join(f"traceId:{t}" for t in [tid] + [x for _, x in linked]))]:
        body = {"query": {"query_string": {"query": qs}}, "size": 200,
                "sort": [{"@timestamp": {"order": "asc"}}]}
        url = f"{OS}/otel-logs-*/_search"
        raw = fetch(url, body)
        n = len(json.loads(raw)["hits"]["hits"])
        name = "opensearch-by-order.json" if "order id" in what else "opensearch-by-trace.json"
        c.keep("opensearch", what, f"POST {url} {json.dumps(body)}", name, raw, n)

    # 6. stdout logs: Cloud Logging on GKE, or the pods' own stdout on a local cluster
    if a.logs == "gcloud":
        flt = (f'resource.type="k8s_container" AND resource.labels.namespace_name="{NAMESPACE}" '
               f'AND textPayload:"{order}"')
        cmd = ["gcloud", "logging", "read", flt, "--freshness=6h", "--format=json",
               f"--project={a.gcp_project}"]
        raw = subprocess.run(cmd, check=True, capture_output=True).stdout
        c.keep("cloud-logging", "container stdout lines that contain the order id",
               " ".join(cmd[:3]) + f" '{flt}' " + " ".join(cmd[4:]),
               "cloudlogging-by-order.json", raw, len(json.loads(raw or b"[]")))
    elif a.logs == "kubectl":
        rows = []
        for svc in sorted(in_trace | {s for s, _ in linked}):
            cmd = ["kubectl", "--context", a.kube_context, "-n", NAMESPACE, "logs",
                   f"deploy/{svc}", "--since=6h", "--all-containers"]
            r = subprocess.run(cmd, capture_output=True, text=True)
            rows += [{"service": svc, "line": i + 1, "text": line}
                     for i, line in enumerate(r.stdout.splitlines()) if order in line]
        c.keep("pod-stdout", "pod stdout lines that contain the order id",
               "kubectl logs deploy/<each service> --since=6h, filtered for the order id",
               "stdout-by-order.json", json.dumps(rows, indent=1), len(rows))

    manifest = {"order_id": order, "checkout_trace": tid, "cluster": a.cluster,
                "captured_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "producer_spans": [s["spanID"] for s in pub],
                "linked_traces": [{"service": s, "trace": t} for s, t in linked],
                "steps": c.steps}
    (c.out / "capture.json").write_text(json.dumps(manifest, indent=2))
    print(f"\norder {order}: {len(linked)} linked traces, "
          f"{sum(1 for s in c.steps if s['file'])} files in {c.out}/evidence")


if __name__ == "__main__":
    main()
