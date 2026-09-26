#!/usr/bin/env bash
# Download Google's Cloud architecture icon set into assets/gcp-icons/.
# The icons are Google's and are not stored in this repository.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
URL="https://cloud.google.com/static/icons/files/google-cloud-icons.zip"
ZIP="$(mktemp -t gcp-icons).zip"
curl -fsSL "$URL" -o "$ZIP"
rm -rf "$HERE/gcp-icons"
mkdir -p "$HERE/gcp-icons"
unzip -q "$ZIP" -d "$HERE/gcp-icons"
rm -f "$ZIP"
echo "icons -> $HERE/gcp-icons ($(find "$HERE/gcp-icons" -name '*.svg' | wc -l | tr -d ' ') svg)"
