#!/usr/bin/env bash
# Turn the OpenTelemetry Demo monorepo into a fake company's GitHub org:
# one repo per service, one for the protos, one for the platform.
#
#   fake-org.sh build           write the repos into sandbox/.org/, local only
#   fake-org.sh publish <org>   create each repo in <org> and push. You run this.
set -euo pipefail
. "$(dirname "$0")/env.sh"

UPSTREAM=https://github.com/open-telemetry/opentelemetry-demo
REF=3.1.0                                  # matches CHART_VERSION's app version
OUT="$HERE/.org"
SRC="$OUT/_upstream"

SERVICES=(accounting ad agent cart chatbot checkout currency email fraud-detection
          frontend frontend-proxy image-provider load-generator mcp payment
          product-catalog quote recommendation react-native-app shipping)
PLATFORM_SRC=(flagd flagd-ui grafana jaeger kafka opamp-server opensearch
              otel-collector postgresql prometheus shared telemetry-docs)

readme() {  # name, what, upstream path
  cat > "$OUT/$1/README.md" <<EOF
# $1

$2

Part of the Astronomy Shop sandbox. Imported from
[open-telemetry/opentelemetry-demo]($UPSTREAM) at \`$REF\`, path \`$3\`,
under the Apache License 2.0 (see \`LICENSE\`).
EOF
}

commit() {  # name
  git -C "$OUT/$1" init -q -b main
  git -C "$OUT/$1" add -A
  git -C "$OUT/$1" commit -q -m "import $1 from opentelemetry-demo $REF"
}

build() {
  rm -rf "$OUT"
  mkdir -p "$OUT"
  git clone -q --depth 1 --branch "$REF" "$UPSTREAM" "$SRC"

  for s in "${SERVICES[@]}"; do
    [ -d "$SRC/src/$s" ] || { echo "missing src/$s at $REF" >&2; exit 1; }
    mkdir -p "$OUT/$s"
    cp -R "$SRC/src/$s/." "$OUT/$s/"
    cp "$SRC/LICENSE" "$OUT/$s/"
    [ -f "$OUT/$s/README.md" ] && mv "$OUT/$s/README.md" "$OUT/$s/SERVICE.md"
    readme "$s" "The \`$s\` service." "src/$s"
    commit "$s"
  done

  mkdir -p "$OUT/protos"
  cp -R "$SRC/pb/." "$OUT/protos/"
  cp "$SRC/LICENSE" "$OUT/protos/"
  readme protos "The gRPC contracts that the services share." "pb"
  commit protos

  mkdir -p "$OUT/platform/src"
  for p in "${PLATFORM_SRC[@]}"; do
    [ -d "$SRC/src/$p" ] && cp -R "$SRC/src/$p" "$OUT/platform/src/"
  done
  cp -R "$SRC/kubernetes" "$OUT/platform/" 2>/dev/null || true
  cp "$SRC"/docker-compose*.yml "$SRC/.env" "$SRC/LICENSE" "$OUT/platform/" 2>/dev/null || true
  readme platform "Shared infrastructure: Kafka, the collector, the stores and the dashboards." \
    "src/{$(IFS=,; echo "${PLATFORM_SRC[*]}")}, kubernetes/, docker-compose.yml"
  commit platform

  rm -rf "$SRC"
  echo "built $(ls "$OUT" | wc -l | tr -d ' ') repos in $OUT"
}

publish() {
  local org="${1:?usage: fake-org.sh publish <org>}"
  [ -d "$OUT" ] || { echo "run: fake-org.sh build" >&2; exit 1; }
  echo "This creates $(ls "$OUT" | wc -l | tr -d ' ') public repos in github.com/$org and pushes them."
  read -r -p "Type the org name to continue: " again
  [ "$again" = "$org" ] || { echo "stopped" >&2; exit 1; }
  for d in "$OUT"/*/; do
    n="$(basename "$d")"
    gh repo create "$org/$n" --public --source "$d" --push \
      --description "Astronomy Shop sandbox: $n (from opentelemetry-demo $REF)"
  done
}

case "${1:-}" in
  build) build ;;
  publish) shift; publish "$@" ;;
  *) sed -n '2,7p' "$0"; exit 2 ;;
esac
