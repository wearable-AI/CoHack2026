# vizln

Short, accurate explainer animations of how software systems behave. An AI coding agent builds
them, a script checks the layout, and a second agent session audits every frame.

`vizln` is a compact spelling of "visualization".

## The problem

Races, lag, retries, rollouts and lifecycles are sequences. Prose and static diagrams flatten a
sequence into one picture, and the reader has to replay it in their head. Animation fixes that,
but hand-made animation is slow, and it drifts from the truth: a number typed into a frame is a
number that nobody checks again.

## What is here

| Part | Where | What it does |
|---|---|---|
| A method | `anim/PATTERNS.md` | Classify the problem by its structure before you draw. Eight rows, each with a formal model, a picture shape and a paper. Row 8 is "no clip", because half of the honest answers are no. |
| A harness | `anim/vanim.py` | A thin layer on manim. A clock drives live builders: timelines, counters, plotted curves, code panels, service schematics. The reader watches a quantity change. Each number comes from data. |
| A layout checker | `anim/check.sh` | Runs the scene with no render and reports five faults: off-frame, overlap, too-small, ink-over-text, dot-collision. `--self-test` proves that it still catches five deliberate faults, because it once reported clean while it collected nothing. |
| An auditor protocol | `anim/AUDITOR.md` | A second agent session measures the clip and never edits it. On one clip its first report, "37 `VGroup`, 9 `FadeIn`, 0 `Dot`", settled an argument about whether the clip was animated at all. It later found a 9-second freeze from one clock value that did not change across three frames. |
| An agent skill | `skills/visual-model/SKILL.md` | Loads all of the above into a Claude Code session: classify, write the one sentence, build, check, audit. |
| Trap log | `anim/HARNESS-NOTES.md` | Every manim fault that reached a rendered frame, symptom first, with the guard for each. |
| Case notes | `docs/CASE-NOTES.md` | Three finished pieces of work and the process behind each one. |

## Demo

| Clip | Row | The one sentence it lands |
|---|---|---|
| `demo/Heartbeat.mp4` | 1, two clocks | The work you lose on a pod stop is the gap between your last heartbeat and the last one the server persisted. |
| `demo/Schematic.mp4` | 4, a boundary | A store stays dim until something writes to it, so the frame records what happened. |
| `demo/Smoke.mp4` | 7, a code panel | One beat per thing the reader must see. |

Each clip also has a `.gif`.

## Quick start

Needs Python 3 and ffmpeg (`brew install ffmpeg`). If pip has to build from source, it also
needs cairo, pango and pkg-config. Run each command from this `vizln/` folder.

```sh
python3 -m venv anim/.venv
anim/.venv/bin/pip install -r requirements.txt
assets/fetch-icons.sh                            # Google Cloud icons, for the schematic layer

anim/check.sh --self-test                        # prove the checker still collects
anim/check.sh  anim/examples/heartbeat.py        # layout check, no render
anim/render.sh anim/examples/heartbeat.py --draft            # 720p30, seconds
anim/render.sh anim/examples/heartbeat.py --q qh --gif       # 1080p60 plus a gif
```

## Write a clip

```python
from vanim import *

class Lag(Clip):
    TITLE = "A read model lags, so it cannot confirm a write"

    def story(self):
        clock = self.tracker(0)
        tl = self.timeline(["write committed", "index updated"], t_max=10, step=2)
        self.add(tl.playhead(clock))
        self.add(tl.live_step(0, [2], clock))
        self.add(tl.live_step(1, [7], clock))
        self.sweep(clock, 10, 3.0, say="the list is stale for five seconds")
```

Then read `skills/visual-model/SKILL.md`, section "Craft", before the second clip.

## Credits

- [manim Community Edition](https://www.manim.community/), MIT.
- `third_party/manimce-best-practices/`: MIT, copyright 2026 Adithya S Kolavi. Included
  unchanged, except that the `attention/` example and a duplicate PDF were left out.
- The wiring primitives (`Port`, `Bay`, `net`, the blob threshold) borrow the idea from
  [manim-eng](https://github.com/overegneered/manim-eng), MIT, and reimplement it.
- Google Cloud icons: `assets/fetch-icons.sh` downloads them from Google. They are not stored
  here.
