#!/usr/bin/env bash
# Start the fake company on a local kind cluster. Safe to run again.
set -euo pipefail
. "$(dirname "$0")/env.sh"
. "$HERE/lib.sh"
CTX=$LOCAL_CTX
export DOCKER_CONTEXT="colima-$COLIMA_PROFILE"

colima status --profile "$COLIMA_PROFILE" >/dev/null 2>&1 \
  || colima start --profile "$COLIMA_PROFILE" --cpu 6 --memory 12 --disk 60

kind get clusters 2>/dev/null | grep -qx "$LOCAL_CLUSTER" \
  || kind create cluster --name "$LOCAL_CLUSTER" --kubeconfig "$KUBECONFIG" --wait 120s

install_demo local
