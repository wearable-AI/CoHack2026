#!/usr/bin/env bash
# Enable the APIs, then compare the cluster's vCPUs with the project's limits.
set -euo pipefail
. "$(dirname "$0")/env.sh"
. "$HERE/lib.sh"
need_gcp

g services enable compute.googleapis.com container.googleapis.com logging.googleapis.com

region="${GKE_ZONE%-*}"
per="$(g compute machine-types describe "$GKE_MACHINE" --zone "$GKE_ZONE" --format='value(guestCpus)')"
echo "cluster needs: $GKE_NODES x $GKE_MACHINE = $((GKE_NODES * per)) vCPUs"
echo "metric limit usage"
g compute project-info describe --flatten=quotas \
  --format='value(quotas.metric,quotas.limit,quotas.usage)' | grep -E '^CPUS_ALL_REGIONS\s'
g compute regions describe "$region" --flatten=quotas \
  --format='value(quotas.metric,quotas.limit,quotas.usage)' \
  | grep -E '^(CPUS|IN_USE_ADDRESSES|SSD_TOTAL_GB|DISKS_TOTAL_GB)\s'
