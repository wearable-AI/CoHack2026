---
name: visual-model
description: Classify a program or a behaviour as a formal problem class, then build a short animated model of it with manim. Use when asked to formally model something, to explain how a mechanism actually works, to visualise a diff, a workflow, a race, a rollout, a lag or an analyzer, or to make a clip, video, animation or figure for a pull request, ticket or doc. Routes to the reading list in docs/REFERENCES.md and the pattern catalogue in anim/PATTERNS.md.
---

# Model it, then draw it

Two steps, and the first one is the work. Toolchain in `anim/` at the repository root.

## Sources, all on disk. Read them rather than recalling the API.

| Path | What it is |
|---|---|
| the installed `manim` package (`pip show -f manim`) | library source, same version as installed |
| `docs.manim.community` | guides, tutorials, examples, reference |
| `third_party/manimce-best-practices/rules/` | 23 topic rules: timing, updaters, text, colour, camera |
| `anim/HARNESS-NOTES.md` | faults found here, symptom-first |
| `docs/REFERENCES.md` | the papers behind `PATTERNS.md` |
| `docs/CASE-NOTES.md` | three finished pieces, and the process behind each |

**The cost model, which no manim doc states:** the renderer does per-mobject work on **every
output frame**, so *mobject count* is the scaling variable, not duration or complexity. A
`Group` of N things costs N times one, visible or not. Treat a render time an order of
magnitude off its siblings as a defect to explain. `render.sh` prints its elapsed time and
warns past 3x the clip length.

## Read the case notes before the first clip of a piece of work

`docs/CASE-NOTES.md` holds three finished pieces. Each one is short.

| Case | Read it for |
|---|---|
| A, an architecture explainer | the builder-and-auditor pair, nine briefs that each superseded the last, and the traps that cost hours |
| B, a race | the smallest shape: four boards, 68 seconds, one race, every figure derived |
| C, a clip series | a series of one-sentence clips, and five forms tried against one frozen fact file, then three promoted |

Three habits from them, and each one changed a result:

**Run a second session as an auditor.** The brief is
`anim/AUDITOR.md`. It renders, pulls frames, counts mobjects and
reports. It never edits. Its first report on case A was "37 `VGroup`, 9 `FadeIn`,
0 `Dot`, `MoveAlongPath`, `TracedPath` or `Create`", which settled an argument
that looking at the clip had not settled. "Make it more animated" had already
been said and had changed nothing.

**Derive every figure into one file, and assert the joins.** A clip reads
`facts.json`, and a script in `derive/` builds it from the evidence with asserts
across sources. No clip types a number. Keys are stable identifiers, never
labels containing numbers, so a caption cannot drift from the figure it names.

**Say which frames are this instance and which are the class**, and put the
distinction where a machine can check it. A frame that shows a count from one
run says so in its source line, with `self.source(...)`. A frame that shows what
the code always does carries no count.

**Budget for the arc.** Case A took nine briefs and eight rebuilds, and nobody
could have written the ninth brief at the start. Each one was a reaction to
seeing the previous clip. Keep the superseded renders in `superseded/`.

## Step 1: classify before you draw

Read `anim/PATTERNS.md`: eight problem classes, each with a formal model, a picture shape and a
paper. Classify by **structure, not topic**. A Temporal heartbeat, a Kubernetes grace period
and a lagging read model are one row.

Then write **the one sentence the clip must land**, before any Python. If you cannot write it,
no picture will rescue the model.

Row 8 is "no clip", and half of honest answers are no:

- One static diagram carries it, or the point is a number or a table.
- The reader must copy text out of it. Video is not selectable.
- The change is small and local.

Make a clip only for a **sequence**: an order of events, a state that changes, a walk where
each step depends on the last, or one structure through many lenses.

## Step 2: build it

One file, one `Clip` subclass, one `story()` method. One idea per beat: about 0.45 s of
animation and at least 0.8 s of rest. Length follows content; there is no time budget.

**Prefer a clock to a slideshow.** Beats revealing finished shapes read as a diagram with
steps. A `ValueTracker` driving live builders reads as a thing happening. Use `beat()` for the
verdict at the end, after the clock stops.

**Drive every number from data, never a typed literal**, so no figure can drift from the
analysis behind it.

```python
from vanim import *

class Heartbeat(Clip):
    TITLE = "A heartbeat you record is not a heartbeat the server has"
    SUB   = "Temporal activity  ·  pod stopped by a rollout"

    def story(self):
        clock = self.tracker(0)
        self.live_text(lambda: f"{done(clock.get_value()):,}", [2.6, 2.7, 0],
                       font_size=26, color=RED_)          # a number that moves

        tl = self.timeline(["rows imported", "server checkpoint"], t_max=180, step=30)
        self.add(tl.playhead(clock))                       # the line that walks
        self.add(tl.live_span(0, 0, clock, cap=145))       # a bar that grows
        self.add(tl.live_step(1, [0, 60, 120], clock))     # ticks that arrive
        self.add(tl.at_time(tl.cut(145, label="SIGTERM"), 145, clock))

        self.sweep(clock, 58, 2.0, hold=0.6, say="it heartbeats every ten seconds")
        self.sweep(clock, 145, 3.0, hold=0.4, say="watch the gap open", color=RED_)
        self.beat(*self.show(tl.band(120, 145, color=RED_)),
                  say="the retry redoes everything after the last flush", color=RED_)
```

### `vanim` aids you, it does not fence you in

**Core, always.** `T()`, `Clip`, `story()`, `beat()`, `board()`, `travel()`, `tracker()`, the
palette, the size floor, the audit. These fix real manim faults and carry the house style.

**Catalogue, optional.** `timeline()`, `grid()`, `chain()`, `code()`, `film()`.

**Raw manim is first-class and needs no apology.** A shape `vanim` lacks is an accident of
history, not a boundary. Use it twice and it becomes a builder; use it once and it stays in the
clip. The checker watches raw manim too, so you keep the safety net.

### Reaching into manim

| You want | Reach for |
|---|---|
| an axis with ticks and numbers, linear or log | `NumberLine(scaling=LogBase())`, `Axes` |
| a state machine, laid out in layers | `DiGraph(layout="partite", partitions=[...])` |
| a label that sits **on** an edge, placed for you | `LabeledArrow`, `LabeledLine` |
| a curved or per-edge-styled graph edge | `DiGraph(edge_type=..., edge_config={...})` |
| "this interval is exactly this wide" | `BraceBetweenPoints`, `BraceLabel` |
| slow through the interesting part, fast through the dead part | `ChangeSpeed` |
| a message travelling a route, and its trail | `MoveAlongPath`, `TracedPath` |
| a screen recording played inside a clip | `self.film()`. **Never** a `Group` + `ShowSubmobjectsOneByOne`: that is quadratic and cost 8 m 32 s against 35.8 s on one real clip |
| a publish, a fan-out, a snapshot delivery | `Broadcast`, which is expanding rings |
| a pulse that runs **along** a wire and stops | `ShowPassingFlash` |
| ring a thing without fighting an updater | `Circumscribe`, `FocusOn`, `Flash` |
| a real record, or a claim-and-evidence set | `Table`, `IntegerTable`, `DecimalTable` |
| an adjacency or dependency matrix | `Matrix` |
| a number that counts, not a rebuilt string | `DecimalNumber`, `Integer` plus `set_value` |

Do **not** reach for `three_d` or `vector_field` for a service topology. A topology is a graph,
not a volume, and depth spends a channel to buy nothing.

### The vanim calls

| Call | What it makes |
|---|---|
| `self.tracker(0)` | the clock every live thing reads |
| `self.sweep(clock, to, secs, say=...)` | run the clock, with a fast caption cross-fade |
| `self.live_text(fn, at)` | a number or string that follows the clock |
| `self.timeline(lanes, t_max)` | a time axis with named lanes; then `tick` `span` `band` `cut` `note` |
| `tl.playhead(clock, pulse_at=[...])` | a line that walks the axis and swells at listed moments |
| `tl.live_span` / `tl.live_step` / `tl.at_time` | a bar that grows, ticks that arrive, a reveal at a time |
| `tl.live_curve(fn, clock)` / `tl.live_gap(hi, lo, clock)` | a value plotted on the same axis, and the area between two |
| `self.landmark(clock, at, secs, *flashes, say=...)` | sweep to a moment, mark it, then hold |
| `self.flash(point)` | a burst that survives updaters, unlike `Indicate` |
| `self.zoom_to(target, width)` / `self.zoom_out()` | camera push and pull |
| `self.code(src, "go")` | a syntax-coloured panel, plus `lines[i]` |
| `self.grid(items, colour_of=...)` | a labelled grid, plus `cells[item]` |
| `self.chain(labels)` | boxes left to right with arrows |
| `self.film(paths, centre, width)` | real footage as a filmstrip, then `.roll()` `.mob` `.uv()` `.border()` |
| `self.mark(mob)` | a highlight box that moves to its next target |
| `self.beat(*anims, say=..., color=...)` | one beat, with the bottom readout line |
| `self.show(*mobs)` | fade-in animations for what a builder returned |
| `self.dim(mobs)` / `self.lit(mobs)` | fade a list down or up |
| `fit(mob, w, h)` | scale a group into a box so nothing leaves the frame |
| `self.source("one run, 2026-09-08")` | the provenance line, lightest ink, a top corner |

### The schematic layer, for a service map

`anim/examples/schematic.py` is the worked example. Copy it rather than rewriting the
shapes: two case studies wrote these out before they lived in `vanim`, and the
two copies drifted apart.

Three channels, one fact each. **Shape** says what kind of thing it is and how it
behaves. **Outline colour** says its role. **A badge** says which hosted product.
Colour cannot come from the badges: all 216 Google Cloud icons are the same blue.
A store stays dim until something writes to it, so the frame is a record of what
has happened and not a diagram of what exists.

| Call | What it makes |
|---|---|
| `node(box, [x, y], ["label"], TEAL_, icon="cloud_run")` | a shape, a badge and its text, with `.shape` and `.body`. It asserts the label fits |
| `box` `capsule` `cylinder` `pail` `dashedbox` | a service, an endpoint, a database, a bucket, a boundary |
| `gicon("cloud_tasks")` | one product badge in its own brand colour |
| `ports(n.shape, out=(RIGHT, 0.14))` | named attachment points. The direction belongs to the port |
| `Bay(2.2, pitch=0.22, span=(1.5, 3.0))` | a gutter of integer lanes. A lane outside the span raises |
| `net(a, b, bay=..., lane=0)` or `net(a, b, corners=[...])` | a Manhattan run. It refuses a diagonal segment |
| `w.light(TEAL_)` / `w.watch(...)` / `w.rest()` / `w.idle()` | a message went down this wire / open and carrying nothing / back to a resting weight / wired and carrying nothing |
| `pulse(n, AMBER_)` | a flash around a node's own outline |
| `fade_to(mob, 1.0)` / `fade_now(mob, 0.16)` | wake or sleep a shape. **Never `set_opacity`**: it writes fill, and manim's default fill is red |

One mobject, one dimming mechanism. `fade_to` and `self.dim` both remember a
starting opacity, so a mobject touched by both loses parts.

Colours: `BLUE_ TEAL_ GREEN_ AMBER_ PLUM_ RED_ DIM_`, and `SERIES` for N series.

## Craft: the rules a figure has to obey

Each was paid for by a render that went wrong. Evidence is in `HARNESS-NOTES.md`.

**Type and colour**

- **Never call `Text()`. Call `T()`.** Below size 24 manim rounds word gaps away. Size 12 floor.
- **Different actors, different colours.** One colour for two actors hides the handover.
- **Glass, not mud.** A shade at 0.26 fill over black reads as dirt. `GLASS_` at ~0.42 with a
  matching stroke reads as a lit surface.

**What the figure says**

- **The figure argues, the caption labels.** Two to six words. A caption doing the explaining
  means the figure is not finished.
- **Shade an interval instead of narrating it**, with `tl.window(t0, t1, label=...)`.
- **Plot the delta, not only totals.** A sawtooth of the difference returns to the same
  baseline at every write and needs no explanation. Mark each fall with its cause.
- **A quantity worth talking about deserves a plotted line**, not only a counter. The area
  between two lines is usually the whole point.
- **State the assumption the model rests on**, on its own board at the end.
- **Boards beat captions.** `board()` and `travel()` for a second granularity, `zoom_to()` for
  the one detail carrying the argument.

**Pacing**

- **A pause with nothing in it reads as lag.** `landmark()` sweeps, flashes, then holds.
- **Stop exactly on the event**, not past it, or the reader never sees the value the caption
  names. Cross a cliff as its own step.
- **One event, one pause.** Run up to the moment, blink, let the number fall inside that blink,
  hold once. See `_write()` in `anim/examples/heartbeat.py`.
- **A gradual swell reads as drift.** `Timeline.blink()` fires twice, in the colour of the
  thing that fired, at the instant it fires.
- **Ease the clock, not the counters**, so the digits decelerate with the line.
- **Never morph one caption into another.** Fade out, fade in, under half a second.

**Numbers**

- Give counters a shared column x and let `counter(label, fn, at)` align them. Hand-tuned
  offsets drift the moment a label changes length.
- Stack quantities that belong together. "at risk" under "parsed" reads as one subtraction.

**Arrows**

- **Show a quantity moving** with `transfer()`, drawn in the same beat as the cause and faded
  after. A permanent arrow becomes furniture.
- **Route below the row it leaves, never above.** `counter` exposes `out_low` and `in_low`.
- **Faint beats bold**: stroke ~1.5 at 0.55 opacity. An arrow hints at causation.

**Layout budget**

Frame is 14.22 by 8.0; title takes the top 1.2, readout the bottom 0.8. A timeline of height
4.9 at `DOWN * 0.5` fits, with `plot_h=2.0` above the lanes. Never put a caption inside the
timeline's own footprint. The title and readout leave the view while zoomed, so say what
matters before pushing in.

## Render, check, ship

```sh
render.sh clip.py [Scene] [--draft] [--q qh|qk] [--gif] [--keep]
check.sh  clip.py [Scene]          # no render, no looking
check.sh  --self-test              # before believing any clean result
```

- `--draft` is 720p30 and takes seconds: use it for every iteration. `-ql` is refused.
- Default is `-qk` 2160p60, but **ship footage at `-qh`**: at `-qk` a 1020 px recording is drawn
  ~1755 px wide and softens.
- Working files are deleted unless `--keep`. The scene name is optional.
- Use the gif for chat or an issue tracker, the mp4 for a pull request.

`check.sh` samples the mobject tree and reports five faults: text off frame, two strings
covering each other, text below the size floor, a stroke through a word, two dots closer than
their own size. It cannot judge pacing, taste, or whether a curve tells the truth. **It has
reported a false clean three times**, most recently by going blind after the first long
animation, so on a long clip treat clean as a lower bound.

**Then look at one frame per board.** Manim reports success on a layout that runs off frame.

```sh
ffmpeg -y -v error -i Scene.mp4 -vf "select='eq(n\,320)'" -vsync 0 frame.png
```

Two faults recur: a panel wider than the frame, and two panels drawn on top of each other.
`fit()` plus an explicit `move_to` prevents both.

**On anything longer than one board, hand the frames to an auditor session**
rather than reading them yourself. `anim/AUDITOR.md` is the brief.

## Two constraints worth knowing

**No LaTeX unless you install it.** Without it, `MathTex` and `Tex` fail with
`FileNotFoundError: 'latex'`. Use `Text` with
Unicode: `Text("α ⊣ γ")` renders the adjunction.

**Before changing the harness**, read `HARNESS-NOTES.md`, and add to it when a render surprises
you.
