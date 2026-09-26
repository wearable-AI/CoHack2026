# vanim

A thin manim layer for short explainer clips.

```sh
anim/render.sh anim/examples/smoke.py --draft          # 720p30, seconds
anim/render.sh anim/examples/smoke.py                  # 2160p60, the default
anim/render.sh anim/examples/smoke.py --q qh --gif     # 1080p60, plus a gif
```

- `vanim.py`: the house style and the builders. The `visual-model` skill lists them, so
  they are not repeated here: a second copy of that list drifted out of date twice.
- `examples/smoke.py`: the template and the toolchain smoke test.
- `examples/schematic.py`: the schematic layer, `node`, `ports`, `Bay`, `net` and the net
  verbs. Copy it for any service map. Needs `assets/fetch-icons.sh` once.
- `examples/heartbeat.py`: the timeline worked example.
- `examples/faults.py`: five deliberate faults. Do not fix them.
- `.venv/`: manim, standalone. `render.sh` and `check.sh` find it. `VANIM_MANIM` and
  `VANIM_PY` override it.

The full guidance, including how to decide what is worth capturing, is in
`../skills/visual-model/SKILL.md`.

- `PATTERNS.md`: eight problem classes, the formal model for each, the shape to draw it in,
  and the paper behind it. Read this before writing a clip.
- `check.sh`: layout check with no render. Run after every edit.
- `check.sh --self-test`: proves the checker still collects. Run before believing a clean result.
- `HARNESS-NOTES.md`: every manim trap found so far, with the symptom each one shows.
- `AUDITOR.md`: the brief for a second session that measures the clip and never
  edits it. Use it on anything longer than one board.
