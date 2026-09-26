# Names shared by every sandbox script. Change them here and nowhere else.
# shellcheck shell=bash

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CHART_VERSION=0.42.1          # opentelemetry-demo chart, app 3.1.0
RELEASE=astronomy
NAMESPACE=astronomy

LOCAL_CLUSTER=cohack
LOCAL_CTX=kind-cohack
COLIMA_PROFILE=cohack

GKE_CLUSTER=cohack
GKE_ZONE=us-central1-a
GKE_NODES=3                   # measured on kind: 2.8 cores, 7.1 GiB at 5 users
GKE_MACHINE=e2-standard-2     # 6 vCPUs, under a free trial's vCPU cap
GCP_CONFIG=cohack

# Isolation: the sandbox has its own kubeconfig and its own gcloud
# configuration, so no other cluster or cloud account is visible to it.
export KUBECONFIG="$HERE/.kubeconfig"
export CLOUDSDK_ACTIVE_CONFIG_NAME="$GCP_CONFIG"

# GCP_ACCOUNT and GCP_PROJECT live in .env.local, which git ignores.
if [ -f "$HERE/.env.local" ]; then
  # shellcheck disable=SC1091
  . "$HERE/.env.local"
fi
