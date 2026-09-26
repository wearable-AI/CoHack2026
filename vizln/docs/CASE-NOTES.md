# Case notes

Three finished pieces of work, kept as lessons. Each came from a real production system, so the
clips, the raw evidence and the session transcripts are not in this repository. The process
transfers, and that is what this file keeps. Each number below is a measurement from the
original work.

## Case A: an architecture explainer. 75 seconds, two days, eight rebuilds

The subject was a cloud service that starts one batch job per request and records each run in a
database and two storage buckets.

### Two sessions, one rule each

- **The builder** wrote the clip, read the service's source, derived the figures and rendered.
- **The auditor** rendered the same clip, pulled frames, measured pixel values and mobject
  counts, and reported. It never edited a file.

A person relayed each finding from the auditor to the builder. The two transcripts ran to 370
and 628 turns.

**Why it worked.** The auditor had no stake in the code, so it measured instead of defending.
Its first report counted the builder's mobject vocabulary: 37 `VGroup`, 9 `FadeIn`, and zero
`Dot`, `MoveAlongPath`, `TracedPath` or `Create`. That one count settled an argument about
whether the clip was animated or was a slideshow. "Make it more animated" had already been said,
and it had changed nothing. Later the auditor found that three sampled frames all read
`142.8 s`, which proved an eight-to-ten-second freeze. The builder could not see it, because it
read its own intent instead of the frame.

The brief for that second session is `anim/AUDITOR.md`.

### How the brief moved

Nine briefs, each one replaced the last. The clip was rebuilt for six of them.

| # | The ask |
|---|---|
| 1 | a machine-checked invariant list plus a video |
| 2 | a lifecycle view, with the cloud products and a timeline |
| 3 | a day-one primer for someone who does not know what a run is |
| 4 | motion over static boards, the mechanism named next to the observation |
| 5 | one canvas, one zoom. `board()` and `travel()` forbidden |
| 6 | a directed graph, five write targets, one edge that points back |
| 7 | schematic-capture conventions: a lane grid, Manhattan routing, junctions |
| 8 | Google Cloud icons, the database split into three, node colour back to role |
| 9 | no punchlines, no title, stores dim until something writes to them |

Nobody could have written brief 9 at the start. Each brief was a reaction to the previous render.
Budget for the arc, and keep the superseded renders.

### Read the source before you draw

A source pass corrected four things the clip had wrong:

- Two components shared one product badge but were different resource kinds, a long-running
  service and a batch job. They kept the same badge and got different shapes. That became the
  clip's central visual decision.
- The clip had drawn an edge between two stores that are not connected.
- A subscription opened several steps earlier than the clip showed.
- The platform pulls a prebuilt image. It does not build one, as the clip had said.

### The late correction that mattered most

On the last day the auditor reported that four write targets fired together at one stationary
clock. The cause was worse than the symptom: the run under study wrote to none of them. The clip
had animated four writes that did not happen, for about twenty minutes of work.

The map still showed all five targets, because a reader must know that they exist. The fix:

- captions say "a run" for the general case and "this run" where the figure comes from the trace;
- the one edge that only read was drawn at read weight, because a travelling flash would draw a
  write that never happened;
- the fact file records one yes-or-no field per write target, so the distinction lives in the
  data and not only in the prose.

**The rule.** When a clip shows a system, decide out loud which frames are this instance and
which are the class. Put the distinction where a machine can check it.

### Decisions worth keeping

- **Three channels, one fact each.** Shape says what kind of thing it is. Outline colour says its
  role. A badge says which hosted product.
- **Colour cannot come from icons.** All 216 Google Cloud icons are the same blue. When the icons
  carried identity, the map went flat.
- **A node stays dim until something writes to it**, so the frame records what happened, not what
  exists.
- **Captions label, the figure argues.** Each rejected caption did the explaining that the figure
  should have done.
- **Population statistics stayed off the frame.** Medians and counts stayed in the fact file as
  evidence.
- **Delete the timeline when it costs more than it carries.** Removing the time strip was the
  largest single improvement to the composition. Name what a deletion costs.

### Traps

The manim traps are in `anim/HARNESS-NOTES.md`, section "From case A". One more, not a manim
trap: scripted regex edits over-deleted three times. One regex removed a neighbouring function,
and only a parse error caught it. Delete by line span with explicit boundaries, and assert that
the anchor exists before you substitute.

## Case B: a race. Four boards, 68 seconds

The subject was a client autosave that reached the server while a record was changing state. The
state change read the record's items once, and nothing read them again. The client held more
items than the server did, and only the server's copy fed the state change.

**The one sentence.** The state change reads the items once, and nothing reads them again.

**Classification.** Row 6 of `anim/PATTERNS.md`: a race, two lanes that cross. Two actors, two
colours.

| Board | What it lands |
|---|---|
| 1 | The whole window on one axis. The shaded area between two plotted counts is the items that were never processed. |
| 2 | The same events on a 7-second axis. A 1000 ms debounce cannot be drawn to scale on a 185-second axis, so it gets its own board, not a zoom. |
| 3 | The guard, before and after, and the moment each version reads the state. |
| 4 | The assumption that every board above rests on. |

**Where the numbers came from.** A script builds `data.json` from three raw files, and the clip
types no number:

- the record's own status history;
- request timings from the service's request log;
- a count of other records with the same shape, with the id of the query that produced it.

A request log row carries the completion time, so a start time is that timestamp minus the
latency. Two figures on board 2 are derived that way, not stated.

**Traps.** Six faults. Three were harness defects and are fixed. See `anim/HARNESS-NOTES.md`,
section "Three defects case B paid for". The other three are craft notes in the same section.

## Case C: a series of one-sentence clips

The subject was a study of a workflow engine's import and export jobs, run on a local rig with
process kills and injected faults.

**One clip, one sentence.** Each clip reads one `facts.json`. A script builds that file from the
evidence and asserts every join that a figure depends on.

| # | Row | The shape of the sentence |
|---|---|---|
| 1, 2 | 4 + 1 | the design: who owns each step, and what each step writes |
| 3 | 1 | a crash replays everything after the last heartbeat the server saw |
| 4 | 1 | a replay into an overwrite produces a byte-identical file |
| 5 | 8 | **not a clip.** Nobody had measured the real shutdown order, so a clip would draw a claim with no measurement behind it |
| 6 | 1 | a finish that makes two side effects in one retryable step repeats, loses or skips one of them |
| 7 | 8 | a still table: what survives a replay, before and after the fixes |

**Instance and class.** A frame that shows a count from one run says so in its source line. A
frame that shows what the code always does, and that no run measured, draws the wire at read
weight and carries no count.

**Try the form, not only the content.** A second pass tried five more forms against the same
frozen fact file: a two-clock timeline, a module-boundary still, code beside its effect, a
message sequence chart, and small multiples. It also built a local interactive explorer. Three
were promoted. One sketch, drawn only to test a form, corrected a size that an earlier clip
carried. The earlier rig ran so fast that the server only ever saw the first heartbeat, which hid
the heartbeat throttle.

**Render cost.** Two clips rendered slower than 3x their length. Each rebuilt a bottom strip on
every frame: a curve with a shaded tail, and three combs of up to 100 ticks. The cost is per
mobject per frame, as `render.sh` warns.
