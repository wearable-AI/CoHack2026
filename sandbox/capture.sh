#!/usr/bin/env bash
# Capture one order from the fake company into a folder of raw evidence.
#   sandbox/capture.sh local|gke <out-dir> [order-id]     (no order id: the latest order)
set -euo pipefail
. "$(dirname "$0")/env.sh"
. "$HERE/lib.sh"
case "${1:-}" in
  local) CTX=$LOCAL_CTX; LOGS=(--logs kubectl --kube-context "$LOCAL_CTX") ;;
  gke)   need_gcp; CTX="gke_${GCP_PROJECT}_${GKE_ZONE}_${GKE_CLUSTER}"
         LOGS=(--logs gcloud --gcp-project "$GCP_PROJECT") ;;
  *)     die "usage: capture.sh local|gke <out-dir> [order-id]" ;;
esac
OUT="${2:?usage: capture.sh local|gke <out-dir> [order-id]}"
need_ctx

PIDS=()
trap 'kill "${PIDS[@]}" 2>/dev/null' EXIT
forward() {  # service, remote port, local port
  k port-forward "svc/$1" "$3:$2" >/dev/null 2>&1 &
  PIDS+=($!)
  for _ in $(seq 40); do curl -s -o /dev/null "http://localhost:$3" && return 0; sleep 0.5; done
  die "no answer from $1"
}
forward frontend-proxy 8080 28080
forward opensearch 9200 29200

if [ -n "${3:-}" ]; then WHICH=(--order "$3"); else WHICH=(--latest); fi
python3 "$HERE/../vizln/flow/capture.py" --cluster "$1" \
  --jaeger http://localhost:28080/jaeger/ui/api --opensearch http://localhost:29200 \
  --out "$OUT" "${WHICH[@]}" "${LOGS[@]}"
