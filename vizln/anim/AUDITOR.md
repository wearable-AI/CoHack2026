# Brief for an auditor session

Paste this into a second Claude Code session, and name the clip and the study
directory at the end. The first session builds. This one measures.

The method came out of case A, 2026-09-08, where it did more for the result
than any single technique in the clip. See
`../docs/CASE-NOTES.md`.

## Your one rule

**Measure. Do not fix.** Do not edit the clip, the derivation, or any file the
builder owns. Write only in `audit/`, one file per report. Do not commit.

This rule is the reason the method works. An auditor with no stake in the code
measures instead of defending. The builder reads its own intent off the frame
and cannot see what is on it.

## What to measure, in this order

1. **The mobject census.** Count the vocabulary the clip uses, by class.
   The first report on case A was "37 `VGroup`, 9 `FadeIn`, 0 `Dot`,
   `MoveAlongPath`, `TracedPath` or `Create`". That one count settled an
   argument about whether the clip was animated or was a slideshow, which no
   amount of looking had settled. Report counts, never opinions.

2. **Frames, sampled and read.** Render at `--draft`, pull one frame per board
   and several inside each long animation, and say what is on them.

   ```sh
   ffmpeg -y -v error -i Scene.mp4 -vf "select='eq(n\,320)'" -vsync 0 frame.png
   ```

   Read the numbers off the frame. Three sampled case A frames all read
   `142.8 s`, which proved an eight to ten second freeze the builder could not
   see. A clock that does not move is the commonest fault this finds.

3. **Every figure against its source.** No figure may be a typed literal. For
   each number on the frame, find the key in the clip's `facts.json` (or
   `data.json`, or `trace.json`) and the assert in `derive/` that produced it.
   Re-derive it with your own command from the raw file in `evidence/`. Report
   the command, the number you got, and whether it agrees.

4. **Instance or class.** For each frame, say whether it is true of one run, of
   one build, or of the design in general. A frame that shows a count from one
   run must say so in its source line. A frame that shows what the code always
   does carries no count. This distinction must live in the data, not only in
   the prose: case A records one yes-or-no field per write target in its fact
   file for exactly this reason.

5. **Claims the clip draws that nothing measured.** The worst case A fault was
   four write targets animated for twenty minutes of work when that run wrote to
   none of them. Check each edge that carries a flash against the evidence that
   it happened.

6. **The checker's blind spots.** Run `check.sh --self-test` first, then
   `check.sh`. A clean result is a lower bound, and it has been wrong three
   times. Known blind spots:
   - it skips every frame whose camera width is not `FRAME_W`, so nothing
     inside a `zoom_to` is checked;
   - `_audit_ink` tests only `Line` and `Arc` against text, so a filled shape
     over a word is invisible to it;
   - `always_redraw` mobjects are not in `_visible_texts()`;
   - text fading in over static text on another z-layer passed twice.

7. **Render cost.** `render.sh` prints its elapsed time and warns past 3x the
   clip length. The cost is per mobject per output frame, so a slow render means
   many mobjects on screen, not a complex idea. Report the peak count and what
   is rebuilt every frame.

## The report

One file per pass, `audit/<date>-audit-NN-<topic>.md`. Each finding gets the
command you ran, the output, and the claim it supports or refutes. Rank by
whether it changes what the clip says.

## Fill this in

- Clip file and scene:
- Study directory:
- The one sentence the clip must land:
