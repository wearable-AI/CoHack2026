# What to model, and what shape to draw it in

**This list is open, not settled.** Eight rows is where it stands today, and the ninth row is
probably already in the work we have not classified yet. When a problem half-fits a row, say so
out loud rather than forcing it, and write the row you wish existed at the bottom under
"Rows we do not have yet". Fetching a paper or a specification to justify a new row is in scope.


Read this before writing a clip. It exists so a session does not re-derive the mapping
from "what is this thing" to "what picture shows it".

Organise by **structure, not by topic**. Two problems that look different on the surface
often need the same picture. That is Gentner's structure-mapping result, and it is why the
rows below are named after the shape of the problem, not the service it came from.

## The eight rows

| # | You are looking at | The formal model | The shape | Builder | Paper, see `../docs/REFERENCES.md` |
|---|---|---|---|---|---|
| 1 | Ordering, lag, "who saw what when" | A partial order of events, two clocks that disagree | lanes on one time axis | `timeline()` | Lamport 1978 |
| 2 | An analyzer that approximates a runtime truth | A Galois connection: abstract and concretise as an adjoint pair | a set panel next to a lattice, one beat per concept | `grid()` + a lattice | Cousot & Cousot 1979, 1977 |
| 3 | "Does my copy still behave like the original?" | Behavioural subtyping, the abstraction function | two verdict columns, one row per case, disagreements lit | `grid()` two panels | Liskov & Wing 1994, Hoare 1972 |
| 4 | A module boundary, what a layer hides | Information hiding: name the decision likely to change | a chain of boxes with one box opened | `chain()` | Parnas 1972 |
| 5 | A protocol or lifecycle | A labelled transition system | states as nodes, a token walking the edges | `DiGraph` + `LabeledArrow` | Møller & Schwartzbach |
| 6 | A race, an interleaving that breaks an invariant | Happens-before, with two lanes that cross | two lanes and a crossing | `timeline()` | Lamport 1978 |
| 7 | What a type alone already guarantees | Parametricity | a code panel, one beat per constraint | `code()` | Reynolds 1983, Wadler 1989 |
| 8 | "This is just hard" | Essential vs accidental complexity | **no clip**. Write the sentence instead | none | Brooks 1987 |

Row 8 is not a joke. Half of the honest answers to "should I animate this" are no.

## Worked examples in this repository

| File | Row | The one sentence it lands |
|---|---|---|
| `examples/heartbeat.py` | 1 | The work you lose on a pod stop is the gap between your last heartbeat and the last one the server persisted. |
| `examples/smoke.py` | 7 | One beat per thing the reader must see. Also the toolchain smoke test. |
| `examples/schematic.py` | 4 | A store stays dim until something writes to it, so the frame records what happened. |

## Row 1 is the workhorse. Its recipe.

Almost every distributed-systems question is row 1. The recipe never changes:

1. **Name the two clocks that disagree.** One lane each. The whole clip is the gap between them.
2. **Put the truth on the top lane** and the observed or persisted view below it.
3. **Cut the axis where the disruption lands** with `cut()`. SIGTERM, a deploy, a crash.
4. **Shade the loss with `band()`.** The band between the last durable point and the cut is the
   answer. It is the only thing the reader must remember.
5. **End with the rule, not the diagnosis.** "Checkpoint at the flush boundary" beats
   "and so it broke".
6. **Plot the quantity above the lanes, on the same axis.** Lanes say *when*. A plotted line
   says *how much*, and the shaded area between the two lines is the loss itself. `plot_h`
   reserves the space; `live_curve()` and `live_gap()` draw it as the clock runs.
7. **Show the recovery, not only the failure.** The second pod restarting from the checkpoint
   is what makes the cost concrete: the curve falls to the green line and climbs the same
   ground twice.

Cases already waiting for this recipe:

- **Kubernetes rollout and grace period.** Lanes: in-flight request, readiness probe, endpoint
  removal, SIGTERM, `terminationGracePeriodSeconds`, SIGKILL. The gap is between endpoint
  removal and the last request the pod already accepted. That gap is the 502s.
- **Log and metric flushing at shutdown.** Lanes: emitted, buffered, exported. The band after
  SIGKILL is the evidence you never get to see, which is why the incident looks silent.
- **A read model lagging a write.** Lanes: write committed, index updated, List returns it.
  The rule it lands: a read model lags, so it cannot confirm a write.
- **Retry with a side effect after the loop.** Lanes: work done, external effect landed,
  checkpoint. The rule it lands: one side effect per retryable step.

## Where the rows come from

`../docs/REFERENCES.md` is the reading list, split into formal abstraction and
cognition. When a problem does not fit a row, read the index before inventing a ninth row.
Most of the time the row exists and the problem is wearing a costume.

## How to teach with the finished clip

Bruner's order, from the pedagogy half of the corpus: enactive, then iconic, then symbolic.
Run the thing, then show the picture, then give the formalism. A clip is the iconic step. It
fails when it is used as the first contact, and it fails when it carries an equation the
reader has not earned yet.

## Rows we do not have yet

Named gaps, so a session can pick one up instead of rediscovering it.

- **Row 5 has no `vanim` builder, but it is no longer unsolved.** Drawn once by hand in
  an earlier lifecycle clip (not in this repository), and manim already ships the parts: `DiGraph(layout="partite",
  partitions=[...])` lays the states out in layers, `edge_type` plus a per-edge `edge_config`
  styles the return arc, and `LabeledArrow` puts the count **on** the edge instead of near it.
  Every label collision in that hand-built board came from placing labels with `next_to()`.
  Promote it to a builder the second time someone needs it.
- **Resource contention.** Queue depth, worker pool saturation, backpressure. Probably a stacked
  area over time rather than lanes. Needs a builder.
- **A distribution rather than a sequence. Answered, and the answer was not a static chart.**
  That lifecycle clip's board 3 puts five phases on one shared log axis, each binned from its raw
  1,000 values. It works because the comparison between rows is the point, and a p50 bar threw
  away a shape spanning four orders of magnitude. Two cautions learned there: draw the axis with
  `NumberLine(scaling=LogBase())` rather than by hand, and **report what the bins dropped**, or
  the figure quietly narrows its own denominator.
- **A proof or a refinement chain.** Each step justified by the last. `code()` plus `mark()` gets
  close, but there is no way to show the justification edge.
- **Interactive rather than filmed.** Ciechanowski's sliders beat any video. An HTML artifact
  with a range input may be the better artifact for row 1. Not attempted yet.

## Prior art worth studying before inventing a shape

Named, not linked, because I did not verify the URLs in this session.

- **Bartosz Ciechanowski's explainers** (`ciechanow.ski`). The best working models of a mechanism
  on the internet. Study how he gives the reader one control at a time. Our beat is his slider.
- **The manim Community example gallery** in the official docs. Read it for mechanics, not for
  taste. Most entries are feature demonstrations, not explanations.
- **3Blue1Brown**. The source of manim. Study the pacing: one idea held on screen far longer
  than feels comfortable.
- **Nicky Case's explorables**. Structure over polish. Every one of them lands a single sentence.
- **Lamport's own TLA+ talks** for row 1. He draws the partial order and nothing else.

The common property: each holds exactly one idea per view and refuses to decorate. Copy that
property. Do not copy the production budget.
