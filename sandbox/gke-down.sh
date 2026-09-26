#!/usr/bin/env bash
# Delete the GKE cluster. gcloud asks for confirmation first.
set -euo pipefail
. "$(dirname "$0")/env.sh"
. "$HERE/lib.sh"
need_gcp
g container clusters delete "$GKE_CLUSTER" --zone "$GKE_ZONE"
