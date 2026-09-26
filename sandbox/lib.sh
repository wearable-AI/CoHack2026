# Guards and helpers. Every kubectl and helm call names its context.
# shellcheck shell=bash

die() { echo "error: $*" >&2; exit 1; }

k() { kubectl --context "$CTX" -n "$NAMESPACE" "$@"; }
h() { helm --kube-context "$CTX" -n "$NAMESPACE" "$@"; }
g() { gcloud --project "$GCP_PROJECT" "$@"; }

need_ctx() {
  kubectl config get-contexts -o name 2>/dev/null | grep -qx "$CTX" \
    || die "context $CTX is not in $KUBECONFIG"
}

need_gcp() {
  [ -n "${GCP_ACCOUNT:-}" ] && [ -n "${GCP_PROJECT:-}" ] \
    || die "set GCP_ACCOUNT and GCP_PROJECT in sandbox/.env.local (see .env.local.example)"
  gcloud config configurations describe "$GCP_CONFIG" >/dev/null 2>&1 \
    || die "no gcloud configuration '$GCP_CONFIG'. See sandbox/README.md"
  local active
  active="$(gcloud auth list --filter=status:ACTIVE --format='value(account)')"
  [ "$active" = "$GCP_ACCOUNT" ] \
    || die "gcloud configuration '$GCP_CONFIG' uses '$active', expected '$GCP_ACCOUNT'"
}

install_demo() {
  need_ctx
  helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts >/dev/null 2>&1 || true
  helm repo update open-telemetry >/dev/null
  h upgrade --install "$RELEASE" open-telemetry/opentelemetry-demo \
    --version "$CHART_VERSION" --create-namespace --wait --timeout 20m
  k get pods
  echo "store, Jaeger, Grafana and flags: sandbox/forward.sh $1, then http://localhost:8080"
}
