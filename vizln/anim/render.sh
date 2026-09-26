#!/usr/bin/env bash
# Render a vanim clip, and optionally make a GIF.
#
#   render.sh clip.py [Scene] [--q qm|qh|qk] [--draft] [--gif] [--keep]
#
# Quality defaults to qk (2160p60). --draft is qm (720p30,
# seconds). 720p30 is the floor; -ql is refused. Working files are deleted after
# the mp4 is copied out, unless --keep.
#
# Output lands next to the clip as <Scene>.mp4 (and <Scene>.gif with --gif).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CLIP=""; SCENE=""; Q="qk"; GIF=0; KEEP=0
while [ $# -gt 0 ]; do
  case "$1" in
    --q) Q="$2"; shift 2 ;;
    --gif) GIF=1; shift ;;
    --draft) Q="qm"; shift ;;
    --keep) KEEP=1; shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) if [ -z "$CLIP" ]; then CLIP="$1"; else SCENE="$1"; fi; shift ;;
  esac
done
[ -n "$CLIP" ] || { echo "usage: render.sh clip.py [Scene] [--q qh] [--gif]" >&2; exit 2; }
[ -f "$CLIP" ] || { echo "no such clip: $CLIP" >&2; exit 2; }

# 720p30 is the floor. -ql is 480p15 and always looks broken on a code panel.
case "$Q" in
  ql) echo "note: -ql is 480p; raising to 720p30 (-qm)"; Q="qm" ;;
  qm|qh|qk|qp) ;;
  *) echo "unknown quality '$Q'; use qm (720p30), qh (1080p60) or qk (4k)" >&2; exit 2 ;;
esac

# interpreter: an override, then the venv next to this script
MANIM="${VANIM_MANIM:-}"
for c in "$HERE/.venv/bin/manim"; do
  [ -n "$MANIM" ] && break
  [ -x "$c" ] && MANIM="$c"
done
[ -n "$MANIM" ] || { echo "no manim found; set VANIM_MANIM" >&2; exit 1; }

CLIP_DIR="$(cd "$(dirname "$CLIP")" && pwd)"
CLIP_FILE="$(basename "$CLIP")"

# every Clip subclass in the file, if no scene was named
if [ -z "$SCENE" ]; then
  SCENE=$(grep -Eo '^class[[:space:]]+([A-Za-z_][A-Za-z0-9_]*)\(Clip\)' "$CLIP" | head -1 | awk '{print $2}' | cut -d'(' -f1)
  [ -n "$SCENE" ] || { echo "no 'class X(Clip)' found; name the scene" >&2; exit 2; }
fi

export PYTHONPATH="$HERE:${PYTHONPATH:-}"
MEDIA="$CLIP_DIR/.vanim-media"

echo "rendering $SCENE from $CLIP_FILE at -$Q"
T0=$SECONDS
"$MANIM" "-$Q" --progress_bar none --media_dir "$MEDIA" "$CLIP_DIR/$CLIP_FILE" "$SCENE" >/dev/null
ELAPSED=$((SECONDS - T0))

SRC=$(find "$MEDIA/videos" -name "$SCENE.mp4" -type f | head -1)
[ -n "$SRC" ] || { echo "render produced no mp4" >&2; exit 1; }
OUT="$CLIP_DIR/$SCENE.mp4"
cp "$SRC" "$OUT"
# manim encodes at its own default. a second pass at crf 16 keeps thin strokes and
# small glyphs clean, which is most of what "looks low quality" turns out to be.
TMP="$(mktemp -t vanim-enc).mp4"
if ffmpeg -y -v error -i "$OUT" -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p "$TMP" 2>/dev/null; then
  mv "$TMP" "$OUT"
else
  rm -f "$TMP"
fi
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT" 2>/dev/null | cut -d. -f1)
echo "mp4  → $OUT  ($(du -h "$OUT" | cut -f1))  rendered in ${ELAPSED}s"
# A render much slower than the clip is long is a defect to explain, not the tool's
# nature. The cost is per mobject per output frame, so the usual cause is N mobjects
# on screen where one would do: see HARNESS-NOTES.md, "Footage is one ImageMobject".
if [ -n "$DUR" ] && [ "$DUR" -gt 0 ] && [ "$ELAPSED" -gt $((DUR * 3)) ]; then
  echo "note: ${ELAPSED}s to render ${DUR}s of clip. Over 3x is worth explaining." >&2
  echo "      Usual cause: many mobjects on screen per frame. See HARNESS-NOTES.md." >&2
fi

if [ "$GIF" = 1 ]; then
  PAL="$(mktemp -t vanim-pal).png"
  ffmpeg -y -v error -i "$OUT" -vf "fps=15,scale=960:-1:flags=lanczos,palettegen" "$PAL"
  ffmpeg -y -v error -i "$OUT" -i "$PAL" \
    -lavfi "fps=15,scale=960:-1:flags=lanczos[x];[x][1:v]paletteuse" "$CLIP_DIR/$SCENE.gif"
  rm -f "$PAL"
  echo "gif  → $CLIP_DIR/$SCENE.gif  ($(du -h "$CLIP_DIR/$SCENE.gif" | cut -f1))"
fi

# manim keeps every partial movie file; that is the part that grows without bound
if [ "$KEEP" = 0 ]; then
  rm -rf "$MEDIA"
else
  echo "kept working files in $MEDIA"
fi
