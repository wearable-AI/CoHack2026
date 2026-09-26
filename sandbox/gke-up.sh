#!/usr/bin/env bash
# Start the fake company on a small GKE cluster in your own GCP project.
# Needs sandbox/.env.local and the gcloud configuration from README.md.
set -euo pipefail
. "$(dirname "$0")/env.sh"
. "$HERE/lib.sh"
need_gcp
CTX="gke_${GCP_PROJECT}_${GKE_ZONE}_${GKE_CLUSTER}"

g services enable container.googleapis.com logging.googleapis.com

g container clusters describe "$GKE_CLUSTER" --zone "$GKE_ZONE" >/dev/null 2>&1 \
  || g container clusters create "$GKE_CLUSTER" --zone "$GKE_ZONE" \
       --num-nodes "$GKE_NODES" --machine-type "$GKE_MACHINE" --disk-size 50 \
       --logging=SYSTEM,WORKLOAD --monitoring=SYSTEM --release-channel regular

# writes the context into the sandbox kubeconfig only
g container clusters get-credentials "$GKE_CLUSTER" --zone "$GKE_ZONE"

install_demo gke
