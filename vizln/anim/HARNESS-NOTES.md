# Harness notes

**Symptoms and their guards.** Every entry here is a fault that reached a rendered frame,
written symptom-first, because the symptom is how the next session recognises it. Read this
before changing `vanim.py`, and whenever a render surprises you.

This is not the craft guide. Pacing, arrows, layout, colour and how to read a figure live under
"Craft" in the `visual-model` skill, which is what a session loads. Add findings here; add
rules there.

## Debug mechanically, not visually

`./check.sh clip.py` runs the scene with the file writer off and the audit hooks on, sampling
the mobject tree about eight times per second of clip time. It reports:

| Finding | Means |
|---|---|
| `off-frame` | a text runs past the frame edge |
| `overlap` | two different strings cover each other by more than a tenth |
| `too-small` | a text is under the size 12 floor |
| `ink-over-text` | a stroke is drawn through a word |
| `dot-collision` | two dots sit closer than their own size |

It takes seconds and needs no video. Run it after every edit. It cannot judge taste, pacing or
whether a curve tells the truth, so one look at one frame at full quality is still the last
step, not the first.

The audit lives in `Clip.update_to_time`, gated on `VANIM_AUDIT=1`, so it costs nothing in a
normal render.

## The checker lied three times. Read this before trusting it.

A layout checker that reports clean when it collected nothing is worse than no checker. This
one did exactly that repeatedly. Four causes, all fixed, all worth knowing:

1. `family_members_with_points()` on a `Text` returns the **glyphs**, which carry no `.text`.
   An audit written against it collects nothing and reports clean forever. Walk `get_family()`
   and pick out `Text` instances.
2. The overlap threshold was 25 percent, and a real collision measured 24. Now 10 percent.
3. **It went blind after the first long animation.** manim restarts the `t` passed to
   `update_to_time` at 0 for every `play()` and every `wait()`. The sampler compared `t` to a
   stored absolute value, so once `_audit_last` reached, say, 2.2, no animation shorter than
   that ever sampled again, and the value only ratcheted upward. *Symptom:* `Lifecycle: clean`
   on an eight-board, 115-second clip whose later boards were never sampled once. A 4-second
   probe sampled twice, both times before the camera had moved. *Guard:* notice the restart
   (`t < last_t`), accumulate the finished animation's duration, and sample on clip time.

   This one is the reason to distrust a clean result on a **long** clip specifically. The two
   earlier causes made it blind everywhere; this one made it blind late, which is worse,
   because the early boards look checked.

4. It only ever compared `Text` against `Text`. So the moment a clip drew something with raw
   manim, it left the safety net entirely: `timeline()` was checked, a hand-built board of
   `RoundedRectangle` and `CurvedArrow` was not. That is backwards, because it charges you the
   checker for reaching into the library. *Symptom:* `Lifecycle: clean` on a clip whose frames
   had a count sitting on an arrow and two strip-plot dots merged into one blob. *Guard:*
   `_audit_ink` and `_audit_dots`, which watch every mobject, not only text.

**Run `./check.sh --self-test` first.** It runs `examples/faults.py`, which holds one text off
the edge, two texts on top of each other, one text at size 3, an arrow through a word, and two
dots covering each other. It fails if any of the five goes unreported. Do not fix `faults.py`.

Three measurement notes on the newer pair, all learned by getting them wrong first:

- **Prefilter on boxes, then sample the path.** A bounding-box test alone is useless for a long
  diagonal arrow, whose box is mostly empty. Sampling every path against every word instead took
  a distribution board past two minutes, and a check nobody waits for is a check nobody runs.
  Box test first, sample only on a hit: 53 seconds for a 115-second clip.
- **For marks, test separation, not overlap.** Two dots read as one when the clear space between
  their edges is smaller than the marks themselves. The pair that looked merged at 720p was
  0.155 units apart with a 0.124 diameter, so a strict overlap test called it clean and was
  arithmetically right and visually wrong.
- **A `Flash` is 14 real Lines on the scene, and they cross whatever is nearby.** Filtering by
  stroke length cannot exclude them, because a `DashedLine`'s leaves are each about 0.069 long
  and a flash ray is 0.16, so any length threshold that hides the rays also blinds the check to
  every dashed rule. `Clip.flash` therefore tags its rays with `vanim_transient` and the audit
  skips them. A raw `Flash` or `Indicate` built inside a clip is **not** tagged and will report
  a hit. That is the reason to call `self.flash()`.

**Keep such probes.** Before trusting a checker run, confirm it still catches a
deliberate fault: one text off the edge, two texts on top of each other, one text at size 3.
If it says clean on that, it is broken.

Two exemptions the checker needs, or it drowns in false positives:

- **Mid-pan**, every board is half off-screen. Skip a sample if the camera moved since the last.
- **Zoomed**, things are excluded on purpose. Skip if the camera width is not the frame width.

And it must know about boards. A distance heuristic fails, because board 1's right edge lands
within a few units of board 2's camera. Boards register their centres, and a text is judged
only against the board it is nearest to.

## Faults in manim itself, and the guard for each

**A plain updater gets baked into the static image.** The cairo renderer draws non-moving
mobjects once into a static image and composites moving ones on top. A mobject you mutate
inside a hand-written updater can land in both, so two values are drawn on top of each other.
*Symptom:* a counter showing `6,505` and `3,415` superimposed. *Guard:* use `always_redraw`.

**`always_redraw` plus a cache poisons the first entry.** `always_redraw(f)` builds `m = f()`
and then calls `m.become(f())` every frame. If `f` returns a cached mobject, the first cache
entry *is* `m`, so `m.become(m)` does nothing and the value freezes at whatever it last showed.
*Symptom:* `at risk` stuck at `1,375` after it should have returned to `0`. *Guard:*
`live_text` hands out `cache[val].copy()`.

**`set_opacity` overrides fill opacity.** Fading in a band drawn at `fill_opacity=0.18` with
`set_opacity(a)` makes it solid at `a=1`. *Symptom:* a translucent grace-period band rendering
as an opaque amber block over the bars. *Guard:* `Timeline.at_time` records each part's own
fill and stroke opacity and scales them.

**A Transform between two strings is mush.** `Transform` and `FadeTransform` between two
different `Text` objects show both for most of the run. Sharing a sweep's `run_time` makes that
run seconds long. *Symptom:* an unreadable smear at the bottom of the frame. *Guard:*
`say_anim` is a `Succession` of `FadeOut` then `FadeIn`, always under half a second, played
concurrently with the sweep rather than stretched to it.

**`set_fill` on a `CurvedArrow` fills the whole arc.** A slick line becomes a solid blob.
*Symptom:* a curved causation arrow rendering as a filled wedge. *Guard:* set fill opacity to
zero, stroke the arc, and fill only `a.tip`. Arrow routing and weight are craft rather than a
fault, and live under "Craft" in the `visual-model` skill.

**`Indicate` fights an updater.** Anything with `always_redraw` is rebuilt every frame, so an
`Indicate` on it is overwritten immediately. *Guard:* `Clip.flash(point)` uses `Flash`, which
is a transient mobject at a location and owns nothing.

**Footage is one `ImageMobject` plus an updater, never a `Group` of N.** manim has no video
mobject, so a screen recording arrives as a frame sequence. The obvious spelling is a `Group`
of N `ImageMobject`s played with `ShowSubmobjectsOneByOne`, and it is quadratic:
`update_submobject_list` re-zeroes the opacity of *every earlier frame on every frame*, and
because all N belong to the animation none of them can enter the static-image cache, so the
renderer walks all N every frame. *Symptom:* a 54-second clip taking eight and a half minutes
to draft, most of it on one board. *Measured*, same 159 frames of a 1100x294 recording, same
6-second animation, same output duration:

| | Time |
|---|---|
| `Group` + `ShowSubmobjectsOneByOne` | 200.0 s |
| one mobject, `pixel_array` swapped | 3.2 s |

End to end on the real clip that was 8 m 32 s against 35.8 s, **14.3x**. *Guard:* `Clip.film()`
returns a `Filmstrip`; `.roll(run_time=)` is the animation, `.mob` the image, `.uv(u, v)` a
point inside the footage. Place overlays with `.uv()` rather than board coordinates: threading
`FILM_W`/`FILM_H` through a module-level helper is what put a highlight box on the wrong row
twice.

Two traps inside that guard. `Animation.interpolate` does **not** apply the rate function
before calling `interpolate_mobject`, so `_Roll` applies it itself; get that wrong and the
footage plays on the wrong curve rather than failing. And `ImageMobject` caches
`orig_alpha_pixel_array` from its first image, which `set_opacity` reads, so swapping
`pixel_array` leaves that cache stale. Fading a rolled filmstrip looked fine in practice, but
that is luck rather than design.

**A `Timeline` must never be scaled after it is built.** Its `x()` and `py()` return absolute
coordinates. `fit()` a timeline and every tick added later lands somewhere else.

## Type

**Never call `Text()` in a clip. Call `T()`.** manim lays glyphs out at the size you ask for,
and below roughly 24 it rounds the word gaps away: `"land each side effect at the flush"`
renders as `"land each side effectat the flush"`. Building at 48 and scaling down keeps the
metrics exactly. This was the "weird font spacing" that survived two font changes, because it
was never the font. `MarkupText` has the same fault.

`T()` also stamps `vanim_size`, because a bounding-box height lies about a word with no
ascenders: `"rows"` at size 14 measures 0.109 high and looks like a violation when it is not.

`FONT = "Helvetica"`. Chosen by rendering one string in five faces and looking:

| Face | Verdict |
|---|---|
| Helvetica | even. the only good one |
| Helvetica Neue | drops the kern after a capital: `RecordHeartbeat` reads as `Record Heartbeat` |
| Avenir Next | worse, large gaps mid-word |
| Optima, Charter | serif, uneven at small sizes |

Do not change the font without repeating that probe. `MONO` is Menlo, for identifiers, paths
and numbers that change.

## Resolution and encoding

- Default render is `-qk`, 3840x2160 at 60 fps. Render time tracks the number of mobjects on
  screen per frame far more than clip length, so no single figure holds: a 23-second clip took
  about 90 seconds, and a 54-second one took 8m32s until its filmstrip was fixed. `render.sh`
  prints its own elapsed time and warns above 3x the clip's duration.
- **Ship at `-qh` when the clip contains real footage.** At `-qk` a 1020-px-wide screen
  recording is drawn about 1755 px wide, so it upscales and softens. At `-qh` the same crop
  lands at 0.86x and 1.19x, essentially native. Judge footage at the quality you will ship.
- A 1-pixel stroke at 720p disappears into the downscale and reads as a broken glyph. That is
  what the phantom strikethrough through a lane label was. It does not exist at 4K.
- `render.sh` re-encodes at `-crf 16 -preset slow` after manim finishes. Manim's own default
  leaves visible mosquito noise around small glyphs on a black background.
- Judge type and stroke weight only at full quality. Draft at `--draft` for everything else.

## Three more traps, found the same way

**A tick that fades in after its moment is invisible during a pause on that moment.**
`live_step` now reaches full opacity **at** `t`, by ramping from `t - 0.6`.

**`CurvedArrow(color=...)` does not colour the tip.** Build it, then `.set_color()`.

**Text flush against the frame edge reads as clipped even when it fits.** The audit uses a
`SAFE = 0.30` margin, not the literal edge. That margin caught the title and two labels that
the edge test passed.

## Wiring a diagram: use `Port`, `Bay` and `net`, not hand-typed offsets

Symptom: an arrowhead points at nothing, or a vertical wire runs exactly along a
node's own border.

Cause, measured on a real clip. An edge was built as
`wire(a, b, lane=3.85)` where `b`'s x **was** 3.85. The path's last two points
came out identical, the arrowhead direction was inferred by comparing them, all
three tests failed, and the head fell through to `rotate(0)`, pointing up.
`set_points_as_corners` also got a zero-length segment.

Both faults are the same root: a lane was a float a human typed, and nothing
checked it against the space it was meant to occupy.

The three primitives make each fault impossible instead of unlikely:

- **`Port(at, direction)`**, built by `ports(mob, name=(SIDE, offset))`. The
  direction belongs to the port, so a wire cannot leave a node sideways, and
  `offset` spreads several arrivals along one face rather than stacking them.
- **`Bay(centre, pitch, span)`**. Lanes are integer indices. A lane outside the
  bay's clear `span` raises, naming the x it would have used. That is the guard
  the 3.85 case needed.
- **`net(a, b, bay, lane)`**. Corners are declared, then duplicate points are
  dropped, so the arrowhead always has a real last segment to point along.
- **`blobs(*nets, threshold=2)`**. A solder blob appears only where more than two
  nets meet a point. A T junction means they connect, a plain crossing means
  they do not, and nobody has to remember which.

Borrowed from manim-eng (MIT, `github.com/overegneered/manim-eng`) and
reimplemented, not depended on: it pins `manim <0.20` against our 0.21, and its
symbol library is electrical, so a Cloud Run job has no component there. The
blob threshold is its `AUTOBLOBBING_BLOB_THRESHOLD`.

## A dimmed shape turns red, because manim's default fill is red

Symptom: the bottoms of three database cylinders went dark red the moment the
camera zoomed away from them and `dim()` ran.

Cause, measured:

    Ellipse default fill_color : #FC6255   fill_opacity: 0.0
    after set_stroke(TEAL_), fill still  : #FC6255
    after set_opacity(0.10)              : #FC6255  0.1

`Ellipse` subclasses `Circle`, and manim's `Circle` defaults to red. A cylinder
built from an unfilled ellipse therefore carries `#FC6255` as its fill colour at
opacity 0, which is invisible until something raises the opacity. `set_stroke`
never touches fill, so the colour survives every restyle. `dim()` calls
`set_opacity`, which raises **fill and stroke together**, and the hidden red
appears.

`dim()` now repaints anything at fill_opacity 0 to `BG_` before saving state, so
raising its opacity shows nothing. Verified by computing the on-screen blend
rather than eyeballing it: `(25, 10, 8)` before, `(0, 0, 0)` after.

**The second lesson is about the test, not the code.** An earlier pass scanned
frames for reddish pixels with a `r > 60` threshold and reported the frame
clean. `#FC6255` at 10% over black is `(25, 10, 8)`, so that test could not have
failed. A clean result from a test incapable of detecting the fault is worse
than not looking. Compute the value you expect to see before choosing a
threshold.

Never rely on a manim default fill colour. Set `fill_color` and `fill_opacity`
explicitly on every shape, including the ones meant to be invisible.

---

## From case A, an architecture explainer, 2026-09-08

Summary in `../docs/CASE-NOTES.md`.

**`GrowFromEdge` scales both axes.** A progress bar animated with it grows
taller as it grows longer, so the reader sees two quantities changing where the
scene means one. *Symptom:* a load bar that "loads weirdly". *Guard:*
`stretch_to_fit_width(max(w, 1e-4))` then re-anchor the left edge by hand. The
same applies to `.scale()` about a point.

**`always_redraw` throws away an animated opacity.** `live_text` returns an
`always_redraw` holder, which calls `become()` on the mobject it first built,
every frame. `holder.animate.set_opacity(0)` therefore has no visible effect at
all. *Guard:* put a flag inside the lambda and set it between plays.

**A port offset's sign inverts between faces.** The offset runs along its own
face's axis, and that axis points down on a LEFT face and up on a RIGHT one, so
`(LEFT, +0.22)` lands 0.22 **below** centre. *Symptom:* a fan of arrivals in
reverse order, crossing each other. *Guard:* measure one port before placing a
row of them. This is not a `ports()` bug.

**One mobject, one dimming mechanism.** `vanim`'s `dim`/`lit` saves prior state
and a scene-local `fade_to` multiplies it. Point both at the same mobject and
the second save records the already-dimmed appearance, so the restore returns to
the wrong value. *Symptom:* a time strip that lost its tick labels across a zoom
and never got them back.

**`set_opacity` writes fill as well as stroke.** Already in these notes, and it
happened three more times in one clip. The durable fix is a pair of helpers that
record each part's own `(stroke, fill)` opacity once and multiply, never set. If
you find yourself calling `set_opacity` on a group, that is the bug.

**`check.sh` cannot see inside a zoom.** It skips every frame whose camera width
is not `FRAME_W` (`vanim.py:477`). A panel that only exists at another camera
width is unverified, and must be checked on a rendered frame. Two other blind
spots worth knowing: `_audit_ink` tests only `Line` and `Arc` against text, so a
filled shape over text is invisible to it, and `always_redraw` mobjects are not
in `_visible_texts()`.

**Run a second session as an auditor.** It renders, pulls frames, and measures.
It does not edit. Its first report on case A counted the mobject vocabulary,
37 `VGroup`, 9 `FadeIn`, 0 `Dot`/`MoveAlongPath`/`TracedPath`/`Create`, which
settled in one line an argument about whether the clip was animated that looking
at it had not settled. It later caught a 9-second freeze by sampling three
frames and finding the same clock value on all three.

## The schematic layer moved into `vanim`, 2026-09-23

Two case studies had each written out the same nine builders: `gicon`, `fade_to`,
`fade_now`, `node`, `box`, `capsule`, `cylinder`, `pail` and `dashedbox`. Case A
wrote them on 2026-09-08 and case C wrote them again on 2026-09-23.

The bodies agreed. The defaults and the docstrings had drifted, which is the real
cost. `gicon` is three lines in both copies. The case A copy carries the colour
policy: brand colour marks a hosted product, line art marks everything else, and
all 216 Google Cloud icons are the same blue, so node colour must stay with the
role. The second copy kept the code and lost the reason. A third session copying
the second copy would not know the rule exists.

All nine are in `vanim` now, with the reasons kept. `examples/schematic.py` is
the worked example. Both clips still define their own copies after
`from vanim import *`, so they shadow the new ones and nothing they render
changed. A new clip should not.

### Why both studies went around `Port`, `Bay` and `net`

The section above ("Wiring a diagram") told them to use these, and both
hand-typed their corners instead. The cause was not stubbornness. `net()` gave
geometry and nothing else, so the lighting verbs had to be written in the clip,
and once a clip owns `light()` it may as well own the path as well. The guard
that `Bay` gives, an exception naming the x it would have used, was therefore
unavailable to exactly the clips most likely to need it.

`net()` now returns a `Net`, which carries the four verbs both studies wrote:

- `light(color)`: full stroke and a pulse along the path. A message went down
  this wire at this moment.
- `watch(color)`: open and carrying nothing. A subscription, a lease, a held
  connection. Case A added this one because a travelling flash on
  `inbox.start()` would have drawn traffic that never happened.
- `rest()`: back to a resting weight. A net that stays lit becomes furniture.
- `idle()`: wired and carrying nothing. The state `net()` leaves a net in.

`net(a, b, corners=[...])` routes a run that one bay lane cannot reach, and it
raises on a diagonal segment, naming the pair. Ports are now required, with an
error that names `ports()` rather than an `AttributeError` on `.at`.

## Three defects case B paid for, now fixed

Case B's process notes listed six faults and said to add them here if
they recur. That rule is wrong: a fault that costs a render has already
recurred. Three were harness defects and are fixed.

- **`code()` added its panel where the call stood.** A panel built for a board at
  `RIGHT * 34` was on screen from creation, and `where` is a direction scaled by
  3.5, so it could not reach that board at all. `code(..., at=[x, y], add=False)`
  now does both. It still returns the pair `(panel, lines)`, which is the other
  half of that finding and is now in the docstring.
- **`window(label_dir=DOWN)` landed on the tick numbers.** The buff was a typed
  0.42 and the numbers sit where the font puts them. `Timeline` now records
  `numbers_bottom` from the label mobjects it drew, and `window` measures the
  clearance from it. `label_at=[x, y]` places the label yourself, which a narrow
  interval still needs.
- **`tick(height=0.3)` reached into its own `note()`.** A tick spans half its
  height either side of the lane and `note` anchored 0.12 away. `note(...,
  clears=0.3)` steps past the end of the tick. The default is unchanged, so no
  existing clip moved.

Three of the six are not harness defects and stay as craft:

- A note at exactly `t0` or `t1` of a shaded interval is crossed by its edge.
  Nudge it horizontally.
- `at_time` ramps from `t0`, so stopping the clock exactly on an event leaves
  the thing it reveals at zero opacity. Stop on the event when the point is a
  counter value. Land just past it when the point is a reveal.
- `check.sh` reported clean twice while two real collisions stood, both text
  fading in over static text on another z-layer. Clean is a lower bound.

## The checker never sees node labels, 2026-09-26

Symptom: `check.sh` reported a map clip clean while every store's top rim crossed
its first label line. Found by an auditor session on `examples/one-order`.

Cause, measured: of the 35 distinct strings the checks tested, none was a node
label. A label dimmed by `fade_now` sits at fill opacity 0.16, below the 0.3 floor
of `_visible_texts()`. After `fade_to` lights it, the label is no longer a `Text`
in the scene tree, because `fade_to` animates each glyph on its own. So a node
label escapes the off-frame, overlap and ink checks in both states.

Guard until the checker is fixed: on any clip that uses `fade_now` or `fade_to`,
check the node labels on rendered frames, not with `check.sh`.
