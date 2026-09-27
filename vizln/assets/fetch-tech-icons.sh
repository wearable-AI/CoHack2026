#!/usr/bin/env bash
# Download language and technology icons from devicon (MIT) into assets/tech-icons/.
# The icons are not stored in this repository.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/tech-icons"
BASE="https://cdn.jsdelivr.net/gh/devicons/devicon@latest/icons"
mkdir -p "$OUT"
# name-in-our-data  devicon-folder  file
while read -r name folder file; do
  curl -fsSL "$BASE/$folder/$file" -o "$OUT/$name.svg" && echo "$name"
done <<'EOF'
go go go-original-wordmark.svg
dotnet dotnetcore dotnetcore-original.svg
cpp cplusplus cplusplus-original.svg
nodejs nodejs nodejs-plain.svg
rust rust rust-original.svg
ruby ruby ruby-plain.svg
php php php-original.svg
java java java-original.svg
kafka apachekafka apachekafka-original.svg
postgresql postgresql postgresql-original.svg
redis redis redis-original.svg
EOF
