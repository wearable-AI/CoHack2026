#!/usr/bin/env bash
# Open the store, Jaeger, Grafana and the flag UI on http://localhost:8080.
#   sandbox/forward.sh local|gke [port]
set -euo pipefail
PORT="${2:-8080}"
. "$(dirname "$0")/env.sh"
. "$HERE/lib.sh"
case "${1:-}" in
  local) CTX=$LOCAL_CTX ;;
  gke)   need_gcp; CTX="gke_${GCP_PROJECT}_${GKE_ZONE}_${GKE_CLUSTER}" ;;
  *)     die "usage: forward.sh local|gke [port]" ;;
esac
need_ctx
echo "http://localhost:$PORT  store /  jaeger /jaeger/ui/  grafana /grafana/  flags /feature  load /loadgen/"
k port-forward svc/frontend-proxy "$PORT:8080"
