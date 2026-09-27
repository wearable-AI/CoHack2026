import argparse
import urllib.request
import urllib.parse
import json
import os
import sys
from datetime import datetime

def fetch_json(url, data=None):
    req = urllib.request.Request(url)
    if data:
        req.add_header('Content-Type', 'application/json')
        jsondata = json.dumps(data).encode('utf-8')
        req.data = jsondata
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return None

def fetch_jaeger_traces(jaeger_url, service, tags=None):
    query = {"service": service, "limit": 50}
    if tags:
        query["tags"] = json.dumps(tags)
    qs = urllib.parse.urlencode(query)
    url = f"{jaeger_url}/api/traces?{qs}"
    return fetch_json(url)

def fetch_opensearch_logs(os_url, query_str):
    url = f"{os_url}/otel-logs-*/_search"
    query = {
        "query": {
            "query_string": {
                "query": query_str
            }
        },
        "size": 100,
        "sort": [{"@timestamp": {"order": "asc"}}]
    }
    return fetch_json(url, data=query)

def stitch(order_id, jaeger_url, os_url):
    events = []
    
    # --- 1. Find the parent trace in Jaeger via the order ID ---
    print(f"[Jaeger] Searching for checkout trace with demo.order.id = {order_id}...")
    checkout_data = fetch_jaeger_traces(jaeger_url, "checkout", tags={"demo.order.id": order_id})
    
    trace_id = None
    spans = []
    processes = {}
    
    if checkout_data and 'data' in checkout_data and checkout_data['data']:
        trace = checkout_data['data'][0] # Pick the first match
        trace_id = trace['traceID']
        spans.extend(trace.get('spans', []))
        processes.update(trace.get('processes', {}))
        print(f"[Jaeger] Found checkout trace: {trace_id} ({len(spans)} spans)")
    else:
        print(f"[Jaeger] Warning: Could not find checkout trace for order ID {order_id}.")

    if trace_id:
        # Add parent spans to events
        for span in spans:
            process = processes.get(span['processID'], {})
            service_name = process.get('serviceName', 'unknown')
            events.append({
                'timestamp': span['startTime'],
                'source': 'jaeger',
                'service': service_name,
                'type': 'span',
                'name': span['operationName'],
                'trace_id': trace_id,
                'span_id': span['spanID']
            })

        # --- 2. Find disjoint consumer traces (accounting, fraud-detection) ---
        # The demo architecture has Kafka breaking the trace.
        # Consumers will have a span with a FOLLOWS_FROM reference pointing to the parent trace.
        for consumer in ["accounting", "fraud-detection"]:
            print(f"[Jaeger] Searching for {consumer} traces linked to {trace_id}...")
            # We can't query FOLLOWS_FROM directly via UI API easily, so we fetch recent and filter
            consumer_data = fetch_jaeger_traces(jaeger_url, consumer)
            
            if consumer_data and 'data' in consumer_data:
                for c_trace in consumer_data['data']:
                    linked = False
                    for c_span in c_trace.get('spans', []):
                        for ref in c_span.get('references', []):
                            if ref.get('refType') == 'FOLLOWS_FROM' and ref.get('traceID') == trace_id:
                                linked = True
                                break
                    if linked:
                        c_trace_id = c_trace['traceID']
                        c_spans = c_trace.get('spans', [])
                        c_procs = c_trace.get('processes', {})
                        print(f"[Jaeger] Found linked {consumer} trace: {c_trace_id} ({len(c_spans)} spans)")
                        
                        for c_span in c_spans:
                            proc = c_procs.get(c_span['processID'], {})
                            svc_name = proc.get('serviceName', consumer)
                            events.append({
                                'timestamp': c_span['startTime'],
                                'source': 'jaeger',
                                'service': svc_name,
                                'type': 'span',
                                'name': c_span['operationName'],
                                'trace_id': c_trace_id,
                                'span_id': c_span['spanID']
                            })

    # --- 3. Get OpenSearch logs ---
    print(f"[OpenSearch] Searching for logs related to order {order_id}...")
    os_data = fetch_opensearch_logs(os_url, f'"{order_id}"')
    if os_data and 'hits' in os_data and 'hits' in os_data['hits']:
        hits = os_data['hits']['hits']
        print(f"[OpenSearch] Found {len(hits)} log lines.")
        for hit in hits:
            src = hit['_source']
            # Convert @timestamp (ISO8601) to microseconds (like Jaeger uses)
            try:
                # Replace Z with +00:00 for older Python datetime support
                ts_str = src['@timestamp'].replace('Z', '+00:00')
                dt = datetime.fromisoformat(ts_str)
                ts_micro = int(dt.timestamp() * 1000000)
            except Exception:
                ts_micro = 0
            
            events.append({
                'timestamp': ts_micro,
                'source': 'opensearch',
                'service': src.get('resource.service.name', 'unknown'),
                'type': 'log',
                'message': src.get('body', ''),
                'trace_id': src.get('traceId', '')
            })

    # --- 4. Sort all events by timestamp ---
    events.sort(key=lambda x: x['timestamp'])

    return events

def main():
    parser = argparse.ArgumentParser(description="Telemetry Stitcher")
    parser.add_argument("--order-id", required=True, help="The Order ID to trace")
    parser.add_argument("--jaeger-url", default="http://localhost:8080/jaeger/ui", help="Jaeger UI API base URL")
    parser.add_argument("--opensearch-url", default="http://localhost:9200", help="OpenSearch base URL")
    parser.add_argument("--output", default="trace_data.json", help="Output JSON file path")
    args = parser.parse_args()

    print(f"Stitching distributed telemetry for Order ID: {args.order_id}\n")
    events = stitch(args.order_id, args.jaeger_url, args.opensearch_url)
    
    # Save the artifact
    with open(args.output, 'w') as f:
        json.dump(events, f, indent=2)
        
    print(f"\nStitched {len(events)} events. Saved to {args.output}")
    
    if events:
        print("\n--- Timeline Preview ---")
        for e in events[:15]:
            if e['type'] == 'span':
                print(f"[{e['source']}] {e['service']} -> {e['name']} (span)")
            else:
                msg = e['message']
                if len(msg) > 60: msg = msg[:57] + "..."
                print(f"[{e['source']}] {e['service']} -> [LOG] {msg}")
        if len(events) > 15:
            print("...")

if __name__ == "__main__":
    main()
