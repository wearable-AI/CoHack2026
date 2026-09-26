#!/usr/bin/env bash
# kubectl against the sandbox only:  sandbox/kc.sh logs deploy/checkout
# Set SANDBOX_CTX to the GKE context to use the cloud cluster instead.
set -euo pipefail
. "$(dirname "$0")/env.sh"
exec kubectl --context "${SANDBOX_CTX:-$LOCAL_CTX}" -n "$NAMESPACE" "$@"
