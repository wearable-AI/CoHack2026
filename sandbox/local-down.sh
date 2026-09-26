#!/usr/bin/env bash
# Delete the local cluster. Add --stop to also stop the colima VM.
set -euo pipefail
. "$(dirname "$0")/env.sh"
export DOCKER_CONTEXT="colima-$COLIMA_PROFILE"

kind delete cluster --name "$LOCAL_CLUSTER" --kubeconfig "$KUBECONFIG"
[ "${1:-}" = "--stop" ] && colima stop --profile "$COLIMA_PROFILE"
exit 0
