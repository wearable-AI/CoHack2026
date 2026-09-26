#!/usr/bin/env bash
# Join a GKE cluster that a teammate already created. Writes only the
# sandbox kubeconfig, and changes nothing in the project.
set -euo pipefail
. "$(dirname "$0")/env.sh"
. "$HERE/lib.sh"
need_gcp
CTX="gke_${GCP_PROJECT}_${GKE_ZONE}_${GKE_CLUSTER}"

g container clusters get-credentials "$GKE_CLUSTER" --zone "$GKE_ZONE"
k get pods
echo "next: sandbox/forward.sh gke"
