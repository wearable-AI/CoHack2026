#!/usr/bin/env bash
# Is the fake company healthy, and does it hold what the product reads?
#   sandbox/ready.sh local|gke
# Every check runs. The exit code is the number of failed checks.
set -uo pipefail
. "$(dirname "$0")/env.sh"
. "$HERE/lib.sh"
case "${1:-}" in
  local) CTX=$LOCAL_CTX ;;
  gke)   need_gcp; CTX="gke_${GCP_PROJECT}_${GKE_ZONE}_${GKE_CLUSTER}" ;;
  *)     die "usage: ready.sh local|gke" ;;
esac
need_ctx

FAILS=0
row() {  # PASS|FAIL|INFO, name, detail
  printf '%-5s %-24s %s\n' "$1" "$2" "$3"
  [ "$1" = FAIL ] && FAILS=$((FAILS + 1))
  return 0
}
pass_if() { if [ "$1" = true ]; then row PASS "$2" "$3"; else row FAIL "$2" "$3"; fi; }

PIDS=()
trap 'kill "${PIDS[@]}" 2>/dev/null' EXIT
forward() {  # service, remote port, local port
  k port-forward "svc/$1" "$3:$2" >/dev/null 2>&1 &
  PIDS+=($!)
  for _ in $(seq 40); do
    curl -s -o /dev/null "http://localhost:$3" && return 0
    sleep 0.5
  done
  return 1
}
WEB=18080 OS=19200 PROM=19090 FLAGS=18016
forward frontend-proxy 8080 $WEB || row FAIL "port-forward" "frontend-proxy did not answer"
forward opensearch 9200 $OS      || row FAIL "port-forward" "opensearch did not answer"
forward prometheus 9090 $PROM    || row FAIL "port-forward" "prometheus did not answer"
forward flagd 8016 $FLAGS        || true   # ofrep answers only on its API path

# 1. the company is up
pods="$(k get pods --no-headers)"
total=$(wc -l <<<"$pods" | tr -d ' ')
notready=$(awk '{split($2, a, "/"); if (a[1] != a[2] || $3 != "Running") n++} END {print n + 0}' <<<"$pods")
restarts=$(awk '{s += $4} END {print s + 0}' <<<"$pods")
pass_if "$([ "$notready" = 0 ] && echo true)" "pods ready" "$total pods, $notready not ready, $restarts restarts in total"

# 2. robot shoppers are buying
st="$(curl -s "localhost:$WEB/loadgen/stats/requests")"
pass_if "$(jq -r '.state == "running" and .total_rps > 0' <<<"$st")" "traffic" \
  "$(jq -r '"\(.state), \(.total_rps * 100 | round / 100) req/s, Locust fail ratio \(.fail_ratio * 1000 | round / 10)%"' <<<"$st")"

# 3. checkouts are traced, and carry the join key
tr="$(curl -s "localhost:$WEB/jaeger/ui/api/traces?service=checkout&operation=oteldemo.CheckoutService/PlaceOrder&limit=50&lookback=15m")"
n=$(jq '.data | length' <<<"$tr")
ids=$(jq '[.data[] | select(any(.spans[].tags[]; .key == "demo.order.id"))] | length' <<<"$tr")
plus() { [ "$1" -ge 50 ] && echo "50+" || echo "$1"; }   # the query stops at 50
pass_if "$([ "$n" -gt 0 ] && [ "$ids" = "$n" ] && echo true)" "checkout traces" "$(plus "$n") in 15 min, all of them carry demo.order.id"

# 4. the Kafka consumers link back to the checkout
acc="$(curl -s "localhost:$WEB/jaeger/ui/api/traces?service=accounting&limit=50&lookback=15m")"
an=$(jq '.data | length' <<<"$acc")
al=$(jq '[.data[] | select(any(.spans[].references[]?; .refType == "FOLLOWS_FROM"))] | length' <<<"$acc")
pass_if "$([ "$an" -gt 0 ] && [ "$al" = "$an" ] && echo true)" "consumer links" "$(plus "$an") accounting traces, all of them link back with FOLLOWS_FROM"

# 5. the gap the demo shows: no edge after Kafka in Jaeger's own map
deps="$(curl -s "localhost:$WEB/jaeger/ui/api/dependencies?endTs=$(date +%s)000&lookback=3600000")"
edges=$(jq '[.data[] | select(.parent == "checkout" and (.child | test("accounting|fraud|kafka")))] | length' <<<"$deps")
pass_if "$([ "$edges" = 0 ] && echo true)" "the async gap" "$edges edges from checkout to Kafka or its consumers in Jaeger's map"

# 6. checkout's order log, in OpenSearch
q='{"query":{"bool":{"filter":[{"range":{"@timestamp":{"gte":"now-15m"}}},{"match_phrase":{"body":"order placed"}},{"match":{"resource.service.name":"checkout"}}]}}}'
ol=$(curl -s -H 'Content-Type: application/json' "localhost:$OS/otel-logs-*/_count" -d "$q" | jq -r '.count // 0')
pass_if "$([ "$ol" -gt 0 ] && echo true)" "OpenSearch order logs" "$ol checkout \"order placed\" lines in 15 min"

# 7. the consumers' order logs, in Cloud Logging
if [ "${1}" = gke ]; then
  cl=$(g logging read 'resource.type="k8s_container" AND resource.labels.namespace_name="astronomy" AND resource.labels.container_name="fraud-detection" AND textPayload:"orderId"' \
       --freshness=15m --limit=200 --format='value(textPayload)' 2>/dev/null | grep -c orderId)
  pass_if "$([ "$cl" -gt 0 ] && echo true)" "Cloud Logging order logs" "$cl fraud-detection orderId lines in 15 min"
else
  row INFO "Cloud Logging order logs" "not on the local cluster"
fi

# 8. Kafka lag is measured, for a two-clock clip
lag=$(curl -s "localhost:$PROM/api/v1/query" --data-urlencode 'query=count({__name__=~"kafka_consumer_group_lag.*"})' | jq -r '.data.result[0].value[1] // "0"')
pass_if "$([ "$lag" -gt 0 ] && echo true)" "Kafka lag metric" "$lag series in Prometheus"

# 9. incidents start switched off
for f in paymentFailure paymentUnreachable kafkaQueueProblems intlShippingSlowdown; do
  v=$(curl -s -X POST -H 'Content-Type: application/json' -d '{"context":{}}' \
        "localhost:$FLAGS/ofrep/v1/evaluate/flags/$f" | jq -r '.variant // "unknown"')
  pass_if "$([ "$v" = off ] && echo true)" "flag $f" "variant: $v"
done

# 10. the PHP service, target of the stage incident
qr=$(k get deploy quote -o jsonpath='{.status.readyReplicas}')
pass_if "$([ "${qr:-0}" -ge 1 ] && echo true)" "quote (PHP) ready" "${qr:-0} ready replicas"

# 11. headroom, where metrics-server exists
if top="$(kubectl --context "$CTX" top nodes --no-headers 2>/dev/null)"; then
  row INFO "node load" "$(awk '{printf "%s cpu %s mem %s; ", $1, $3, $5}' <<<"$top")"
fi

# 12. repos the product cites
built=$(find "$HERE/.org" -mindepth 1 -maxdepth 1 -type d ! -name _upstream 2>/dev/null | wc -l | tr -d ' ')
if [ -n "${FAKE_ORG:-}" ]; then
  pub=$(gh repo list "$FAKE_ORG" --limit 100 --json name --jq length 2>/dev/null || echo 0)
  pass_if "$([ "$pub" -ge 22 ] && echo true)" "fake org repos" "$built built, $pub published in $FAKE_ORG"
else
  row INFO "fake org repos" "$built built in sandbox/.org, not published (set FAKE_ORG in .env.local)"
fi

echo
[ "$FAILS" = 0 ] && echo "ready: every check passed" || echo "not ready: $FAILS check(s) failed"
exit "$FAILS"
