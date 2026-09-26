"""vanim - a thin manim layer for short explainer clips.

Subclass Clip, implement story(). Prefer a clock to a slideshow: a ValueTracker
plus live builders makes the reader watch a quantity change, which is the whole
point of using video instead of a diagram.

Read HARNESS-NOTES.md before changing anything in here. Every guard in this file
was put there by a fault that reached a rendered frame.

    VANIM_AUDIT=1  makes Clip check its own layout while it runs. check.sh uses it.
"""

import os

import numpy as np

from manim import *  # noqa: F401,F403

BLUE_ = "#6FA8FF"
TEAL_ = "#58C7B0"
PLUM_ = "#C89BFF"
AMBER_ = "#FFC24D"
RED_ = "#FF6B6B"
GLASS_ = "#FF4D66"   # a lit red for shaded areas. the muted one reads as dirt
GREEN_ = "#7BD88F"
DIM_ = "#8A8A8A"
BG_ = "#000000"

MONO = "Menlo"
FONT = "Helvetica"   # measured against 5 faces: the only one manim kerns evenly.
#                      Helvetica Neue and Avenir Next both drop the kern after a capital.

SERIES = [BLUE_, TEAL_, GREEN_, AMBER_, PLUM_, RED_]

_BASE_SIZE = 48


def T(text, size=17, font=FONT, color=WHITE, **kw):
    """Build every string at 48 and scale it down.

    manim lays glyphs out at the requested size, and below about 24 it rounds word
    gaps away: "effect at the" renders as "effectat the". Building large and scaling
    keeps the metrics. Never call Text() directly in a clip.
    """
    t = Text(str(text), font=font, font_size=_BASE_SIZE, color=color, **kw)
    t.scale(size / _BASE_SIZE)
    t.vanim_size = size      # the audit reads this: a bbox height lies for a word
    return t                 # with no ascenders, such as "rows"

ICONS = os.environ.get("VANIM_ICONS") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), os.pardir, "assets", "gcp-icons")
IDLE_ = 0.16         # a net that is wired and carries nothing yet
SLEEP_ = 0.16        # a store nothing has written to yet

FRAME_W, FRAME_H = 14.22, 8.0
SAFE = 0.30          # keep text this far off the frame edge
AUDIT = os.environ.get("VANIM_AUDIT") == "1"
AUDIT_HITS = []


def fit(mob, w, h):
    """Scale mob so it fits inside a w x h box. Never grows it past the box."""
    mob.scale(min(w / mob.width, h / mob.height))
    return mob


class Clip(MovingCameraScene):
    """A 16:9 dark-background explainer clip.

    The frame is 14.22 wide by 8.0 high. The title takes the top 1.2 and the
    readout takes the bottom 0.8, so a panel gets about 5.0 of height.
    """

    TITLE = ""
    SUB = ""
    HOLD = 0.8
    RUN = 0.45
    PANEL_H = 4.9
    PANEL_W = 6.2

    # ---------- structure ----------

    def construct(self):
        self.camera.background_color = BG_
        self._audit_last = -1.0
        self._audit_t = 0.0          # last t seen, to notice a play() restart
        self._audit_elapsed = 0.0    # clip time before the current animation
        self._cap_at = np.array([0.0, -FRAME_H / 2 + 0.48, 0.0])
        self._boards = [np.zeros(3)]
        self._head()
        self._readout = T("", 17).move_to(self._cap_at)
        self.add(self._readout)
        self.story()
        self.wait(0.4)

    def _head(self):
        if self.TITLE:
            t = T(self.TITLE, 24).to_edge(UP, buff=0.40)
            self.add(t)
            if self.SUB:
                s = T(self.SUB, 15, font=MONO, color=DIM_)
                s.next_to(t, DOWN, buff=0.14)
                self.add(s)

    def story(self):
        raise NotImplementedError("a Clip subclass must implement story()")

    # ---------- captions ----------

    def say_anim(self, text, color=WHITE, run_time=0.42):
        """Fade the old line out, then the new one in.

        Never morph one string into another. A Transform or a FadeTransform between
        two different strings shows both at once for most of its run, which reads as
        a rendering fault.
        """
        new = T(text, 17, color=color).move_to(self._cap_at)
        old = self._readout
        self._readout = new
        return Succession(
            FadeOut(old, run_time=run_time * 0.45),
            FadeIn(new, run_time=run_time * 0.55),
        )

    # ---------- beats ----------

    def beat(self, *anims, say=None, color=WHITE, hold=None, run=None):
        group = list(anims)
        if say is not None:
            group.append(self.say_anim(say, color))
        if group:
            self.play(AnimationGroup(*group, lag_ratio=0.0), run_time=run or self.RUN)
        self.wait(self.HOLD if hold is None else hold)

    def dim(self, mobs, opacity=0.12):
        """Fade mobjects back, saving what they were so `lit` can put it back.

        `set_opacity` raises fill as well as stroke, so a shape whose fill was
        never set becomes visible in manim's default fill colour, which is red:
        `Ellipse` subclasses `Circle` and `Circle` defaults to `#FC6255`. A
        cylinder built as an unfilled ellipse therefore grew a red bottom the
        moment it was dimmed. Anything invisible is repainted to the background
        first, so raising its opacity shows nothing.

        The saved state is written once and never overwritten while it stands.
        Saving on every call ratcheted a mobject down over repeated dim and lit
        cycles: the second save recorded the already-dimmed appearance, so the
        restore returned to 0.5 rather than 1.0. A time strip lost its tick
        labels that way, fill-drawn text fading out a pass before stroked lines.
        """
        out = []
        for m in mobs:
            for f in m.get_family():
                try:
                    if float(f.get_fill_opacity()) == 0.0:
                        f.set_fill(BG_, opacity=0.0)
                except Exception:
                    pass
            if getattr(m, "saved_state", None) is None:
                m.save_state()
            out.append(m.animate.set_opacity(opacity))
        return out

    def lit(self, mobs, opacity=None):
        """Undo `dim`, restoring each mobject's own opacity rather than 1.0.

        `lit` used to set 1.0, which flattens anything translucent: a shaded
        window drawn at 0.17 came back opaque and hid the marks behind it. So
        anything `dim` saved is restored, and `opacity` is only used for a
        mobject `dim` never touched.

        The saved state is deliberately not cleared here. `Restore` reads
        `saved_state` when it plays, not when it is built, so clearing it would
        break the animation this call returns. The cost is that a change made to
        a mobject between a dim and a lit is reverted by the lit. Keep deliberate
        restyling outside a dim window.
        """
        out = []
        for m in mobs:
            if getattr(m, "saved_state", None) is not None:
                out.append(Restore(m))
            else:
                out.append(m.animate.set_opacity(1.0 if opacity is None else opacity))
        return out

    def source(self, text, right=False, y=3.52):
        """Where the figures come from, in the lightest ink, in a top corner.

        Every clip that shows a measured number needs one of these, and it says
        which run or which code the number came from. Keep the counts in the
        data file and the provenance on the frame.
        """
        s = T(text, 12, color=DIM_).move_to([6.75 if right else -6.75, y, 0],
                                            aligned_edge=RIGHT if right else LEFT)
        s.set_opacity(0.8)
        self.add(s)
        return s

    def show(self, *mobs):
        return [FadeIn(m) for m in mobs]

    def flash(self, point, color=WHITE, radius=0.42, run_time=0.55):
        """A burst at a point. Independent of updaters, unlike Indicate.

        Its 14 rays are real Lines on the scene for half a second, so the ink
        audit reports every one that crosses a nearby label. A burst laid over
        a word on purpose is not a layout fault, so the rays are tagged and the
        audit skips them. A raw `Flash` in a clip is not tagged and will report;
        that is the reason to call this instead.
        """
        f = Flash(point, color=color, flash_radius=radius, line_length=0.16,
                  num_lines=14, line_stroke_width=2.2, run_time=run_time)
        for ray in f.lines:
            ray.vanim_transient = True
        return f

    # ---------- time ----------

    def tracker(self, start=0.0):
        return ValueTracker(float(start))

    EASE = {None: linear, "in": rush_into, "out": rush_from, "both": smooth}

    def sweep(self, tracker, to, secs, hold=0.0, say=None, color=WHITE, ease=None):
        """Advance the clock. This is what makes a clip run.

        ease="out" decelerates into a moment, ease="in" accelerates away from one.
        Every live number reads the clock, so easing the clock eases the counters
        with it: they slow as the indicator slows, which is what ties them together.
        """
        move = tracker.animate(run_time=secs, rate_func=self.EASE[ease]).set_value(float(to))
        if say is None:
            self.play(move)
        else:
            self.play(move, self.say_anim(say, color, run_time=min(0.5, secs)))
        if hold:
            self.wait(hold)

    def landmark(self, tracker, at, secs, *extra, say=None, color=WHITE, hold=0.9):
        """Sweep to a moment that matters, then stop on it and mark it.

        Use this instead of a bare hold. A pause with nothing happening in it reads
        as lag; a pause with a flash in it reads as emphasis.
        """
        self.sweep(tracker, at, secs, say=say, color=color)
        if extra:
            self.play(AnimationGroup(*extra, lag_ratio=0.0), run_time=0.55)
        self.wait(hold)

    def live_text(self, fn, at, anchor=LEFT, font=MONO, font_size=14, color=WHITE):
        """Text that follows a clock. Built mobjects are cached per string value.

        always_redraw, not a plain updater: a plain updater gets baked into the
        renderer's static image and you get two values drawn on top of each other.

        The cache hands out copies. always_redraw calls become() on the mobject it
        first built, so returning a cached original makes the holder become itself,
        and the value freezes at whatever it last showed.
        """
        cache = {}

        def make():
            val = str(fn())
            if val not in cache:
                t = T(val, font_size, font=font, color=color)
                t.move_to(at, aligned_edge=anchor)
                cache[val] = t
            return cache[val].copy()

        holder = always_redraw(make)
        self.add(holder)
        return holder

    def counter(self, label, fn, at, gap=0.24, size=20, color=WHITE, label_size=14):
        """A label right-aligned to `at`, and a live value starting just past it.

        Place counters on a shared column x, never by eye. Hand-tuned offsets drift
        as soon as a label changes length, and the numbers stop lining up.
        """
        self.add(T(label, label_size, color=DIM_).move_to(at, aligned_edge=RIGHT))
        pos = np.array([float(at[0]) + gap, float(at[1]), 0.0])
        holder = self.live_text(fn, pos, anchor=LEFT, font_size=size, color=color)
        holder.value_at = pos                                   # left edge of the digits
        # arrow anchors: route below the row, never across it. Starting above a value
        # sends the arc through whatever sits on the line above.
        holder.out_low = pos + np.array([0.55, -0.24, 0.0])     # leave a counter here
        holder.in_low = pos + np.array([-0.18, -0.26, 0.0])     # arrive at one here
        return holder

    def transfer(self, frm, to, color=GREEN_, angle=-0.55, width=1.5, opacity=0.55):
        """A faint curved arrow saying this quantity moved into that one.

        Draw it in the same beat as the event that caused the move, and fade it out
        again. A permanent arrow becomes furniture and stops being read. Aim it at a
        counter's `in_low` point, never at the digits: an arrowhead touching a number
        makes the number harder to read at the exact moment it matters.
        """
        a = CurvedArrow(np.array(frm), np.array(to), angle=angle,
                        stroke_width=width, tip_length=0.13)
        # stroke only. set_fill on a CurvedArrow fills the whole arc and the slick
        # line becomes a solid blob; only the tip wants fill.
        a.set_fill(opacity=0)
        a.set_stroke(color, width=width, opacity=opacity)
        if a.tip is not None:
            a.tip.set_fill(color, opacity=opacity).set_stroke(width=0)
        return a

    # ---------- boards: several views laid out in world space ----------

    def board(self, center, title=None, sub=None, h=None):
        """A second view, off to the side. The camera travels to it and back.

        Use a board when a different granularity deserves its own space: a
        cumulative chart beside a timeline, a scenario table beneath both. Panning
        says "same subject, different view" in a way a cut cannot.
        """
        b = Board(self, center, title, sub, h or FRAME_H)
        self._boards.append(b.center)
        return b

    def pan_to(self, board, run_time=1.2):
        return self.camera.frame.animate(run_time=run_time).set_width(
            FRAME_W).move_to(board.center)

    def travel(self, board, say=None, color=WHITE, run_time=1.2, hold=0.7, keep=()):
        """Fade the caption out, glide to the board, bring a new caption up there.

        The board being left is removed once the pan lands. manim does per-mobject
        work on every output frame whether the mobject is on camera or not, so a
        finished board left in the scene keeps costing frames for the whole clip.
        Measured on a five-board clip: 473 family members after board A and 2,357
        at the end, while the last board ever shows a few hundred.

        Pass `keep=(mob, ...)` for anything that must survive the pan, such as a
        legend the next board reuses.
        """
        here = _nearest(self._boards, self.camera.frame.get_center())
        self.play(FadeOut(self._readout), run_time=0.22)
        leaving = [m for m in self.mobjects
                   if m not in keep and m is not self.camera.frame
                   and not isinstance(m, ValueTracker)
                   and _belongs_to(m, self._boards, here)]
        self._cap_at = board.cap_at
        self._readout = T("", 17).move_to(self._cap_at)
        self.add(self._readout)
        self.play(self.pan_to(board, run_time))
        if leaving:
            self.remove(*leaving)
        if say is not None:
            self.beat(say=say, color=color, hold=hold)

    # ---------- camera ----------

    def zoom_to(self, target, width=6.0, run_time=0.9):
        """Animation that pushes the camera in on a region. Compose it in a beat.

        The title and the readout are placed against the frame edges, so they leave
        the view while zoomed. Say what matters before you push in.
        """
        return self.camera.frame.animate(run_time=run_time).set_width(width).move_to(target)

    def zoom_out(self, run_time=0.9):
        return self.camera.frame.animate(run_time=run_time).set_width(FRAME_W).move_to(ORIGIN)

    # ---------- panels ----------

    def code(self, src, language="go", where=LEFT, w=None, h=None, line_numbers=True,
             at=None, add=True):
        """A syntax-coloured panel. Returns the pair (panel, lines).

        It is a tuple, not an object with `.mob`. `lines[i]` is one source line.

        `at` places the panel at an explicit centre, which is what a board away
        from the origin needs: `where` is a direction scaled by 3.5 and it can
        only reach the middle of the frame. `add=False` keeps the panel off the
        scene until the clip shows it, because the default adds it where the
        call stands, so a panel built for a later board is on screen from the
        moment it is built.
        """
        panel = Code(
            code_string=src.rstrip("\n"),
            language=language,
            add_line_numbers=line_numbers,
            background="rectangle",
            formatter_style="monokai",
            background_config={"stroke_color": DIM_, "fill_color": BG_},
            paragraph_config={"font": MONO},
        )
        fit(panel, w or self.PANEL_W, h or self.PANEL_H)
        if at is not None:
            panel.move_to([float(at[0]), float(at[1]), 0.0])
        else:
            panel.move_to(where * 3.5 + DOWN * 0.3)
        if add:
            self.add(panel)
        return panel, list(panel[2])

    def grid(self, items, colour_of=None, rows=15, cols=3, where=LEFT,
             font_size=12, w=None, h=None, caption=None):
        cells, group = {}, VGroup()
        for it in items:
            col = colour_of(it) if colour_of else WHITE
            t = T(it, font_size, font=MONO, color=col)
            cells[it] = t
            group.add(t)
        group.arrange_in_grid(rows=rows, cols=cols, buff=(0.35, 0.13), cell_alignment=LEFT)
        fit(group, w or self.PANEL_W, h or self.PANEL_H)
        group.move_to(where * 3.7 + DOWN * 0.45)
        self.add(group)
        if caption:
            c = T(caption, 15, color=DIM_)
            c.next_to(group, UP, buff=0.22).align_to(group, LEFT)
            self.add(c)
        return group, cells

    def film(self, paths, centre, width):
        """Real footage as a filmstrip. One mobject, one array swap per frame.

        manim has no video mobject, so footage arrives as a frame sequence. The
        obvious spelling is a Group of N ImageMobjects played with
        ShowSubmobjectsOneByOne, and it is quadratic: that animation re-zeroes
        the opacity of *every earlier frame on every frame*, and because all N
        belong to the animation none of them can enter the static-image cache,
        so the renderer walks all N every frame.

        Measured on 159 frames of a 1100x294 screen recording, same 6-second
        animation, same output duration:

            Group + ShowSubmobjectsOneByOne   200.0 s
            this                                3.2 s

        Never build a filmstrip as a Group.

        Returns a Filmstrip: `.mob` is the image to place and fade, `.roll()`
        gives the animation. `self.play` adds the mobject for you.
        """
        return Filmstrip(paths, centre, width)

    def chain(self, labels, where=ORIGIN, colours=None, w=13.0, h=1.4, caption=None):
        colours = colours or [WHITE] * len(labels)
        boxes, group, arrows = [], VGroup(), []
        for lab, col in zip(labels, colours):
            t = T(lab, 15, color=col)
            r = RoundedRectangle(
                corner_radius=0.1, width=t.width + 0.5, height=0.8,
                stroke_color=col, stroke_width=1.6, fill_color=BG_, fill_opacity=1,
            )
            boxes.append(VGroup(r, t))
            group.add(boxes[-1])
        group.arrange(RIGHT, buff=0.75)
        for a, b in zip(boxes, boxes[1:]):
            arrows.append(Arrow(a.get_right(), b.get_left(), buff=0.06, stroke_width=2,
                                color=DIM_, max_tip_length_to_length_ratio=0.18))
        whole = VGroup(group, VGroup(*arrows))
        fit(whole, w, h)
        whole.move_to(where)
        self.add(whole)
        if caption:
            c = T(caption, 15, color=DIM_)
            c.next_to(whole, UP, buff=0.25)
            self.add(c)
        return whole, boxes

    def timeline(self, lanes, t_max, w=11.4, h=3.0, where=ORIGIN, step=None,
                 unit="s", plot_h=0.0, y_max=None, y_label=None):
        return Timeline(self, lanes, t_max, w, h, where, step, unit, plot_h, y_max, y_label)

    # ---------- marks ----------

    def mark(self, mob, color=AMBER_, buff=0.06):
        target = SurroundingRectangle(mob, color=color, buff=buff,
                                      stroke_width=2, corner_radius=0.05)
        if not hasattr(self, "_marker"):
            self._marker = target
            return FadeIn(self._marker)
        return Transform(self._marker, target)

    def unmark(self):
        if hasattr(self, "_marker"):
            return FadeOut(self._marker)
        return Wait(0.01)

    # ---------- audit ----------

    def update_to_time(self, t):
        """Sample the layout on a clip-wide clock, not on the animation's own.

        manim restarts `t` at 0 for every `play()` and `wait()`. Comparing it to
        a stored absolute value therefore suppresses every animation shorter
        than the longest one seen so far, and `_audit_last` ratchets up until
        almost nothing is sampled again. *Symptom:* `Lifecycle: clean` on an
        eight-board clip whose later boards were never looked at once, and a
        4-second probe that sampled twice, both times before the camera moved.
        *Guard:* notice the restart and accumulate.
        """
        super().update_to_time(t)
        if not AUDIT:
            return
        if t < self._audit_t:
            self._audit_elapsed += self._audit_t
            self._audit_last = -1.0
        self._audit_t = t
        now = self._audit_elapsed + t
        if now - self._audit_last > 0.12:
            self._audit_last = now
            self._audit()

    def _visible_texts(self):
        """Every Text currently drawn, with real ink.

        family_members_with_points() returns the individual glyphs, which carry no
        .text, so an audit written against it collects nothing and reports clean.
        Walk get_family() and pick the Text containers instead.
        """
        out = []
        for m in self.mobjects:
            for f in m.get_family():
                if not isinstance(f, Text):
                    continue
                if not f.text.strip():
                    continue
                glyphs = f.family_members_with_points()
                if not glyphs:
                    continue
                if max(g.get_fill_opacity() for g in glyphs) < 0.3:
                    continue
                out.append(f)
        return out

    def _audit(self):
        cam = self.camera.frame
        cx, cy = cam.get_center()[0], cam.get_center()[1]
        here = (round(cx, 3), round(cy, 3), round(cam.width, 3))
        moving = getattr(self, "_audit_cam", None) not in (None, here)
        self._audit_cam = here
        if moving:
            return   # mid-pan every board is half off-screen; that is not a fault
        if abs(cam.width - FRAME_W) > 0.05:
            return   # a zoom deliberately excludes things
        hw, hh = cam.width / 2, cam.height / 2
        here_board = _nearest(self._boards, cam.get_center())
        texts = [t for t in self._visible_texts()
                 if abs(t.get_center()[0] - cx) < hw * 3 and abs(t.get_center()[1] - cy) < hh * 3]
        onscreen = []
        for f in texts:
            x0, y0, _ = f.get_corner(DL)
            x1, y1, _ = f.get_corner(UR)
            if _nearest(self._boards, f.get_center()) is not here_board:
                continue      # belongs to another board, not a fault
            # a safe margin, not the literal edge: text flush against the frame
            # reads as clipped even when it technically fits
            hw_s, hh_s = hw - SAFE, hh - SAFE
            out = max(cx - hw_s - x1, x0 - (cx + hw_s), cy - hh_s - y1, y0 - (cy + hh_s))
            if out > 0:
                _hit("off-frame",
                     f"{f.text!r} sits just outside the frame "
                     f"(camera at x={cx:.1f} y={cy:.1f})")
                continue
            onscreen.append(f)
            if x0 < cx - hw_s or x1 > cx + hw_s or y0 < cy - hh_s or y1 > cy + hh_s:
                _hit("off-frame", f"{f.text!r} crosses the frame edge "
                                  f"(camera at x={cx:.1f} y={cy:.1f})")
            if getattr(f, "vanim_size", 99) < 12:
                _hit("too-small",
                     f"{f.text!r} is set at {f.vanim_size}, below the 12 floor")
        for i, a in enumerate(onscreen):
            for b in onscreen[i + 1:]:
                if a.text == b.text:
                    continue
                ov = _overlap(a, b)
                if ov > 0.10:
                    _hit("overlap", f"{a.text!r} and {b.text!r} overlap by {ov:.0%}")
        self._audit_ink(onscreen, here_board)
        self._audit_dots(here_board)

    def _leaves(self, kinds, here_board, exclude=()):
        """Visible leaf mobjects of the given classes, on the board in view.

        The text passes above only compare Text against Text, so anything a clip
        draws with raw manim is unchecked. That is backwards: it means reaching
        into the library costs you the safety net. These two passes close it.
        """
        out = []
        for m in self.mobjects:
            for f in m.get_family():
                if not isinstance(f, kinds) or (exclude and isinstance(f, exclude)):
                    continue
                if not f.has_points():
                    continue
                if _nearest(self._boards, f.get_center()) is not here_board:
                    continue
                out.append(f)
        return out

    def _audit_ink(self, onscreen, here_board):
        """A stroke drawn through a word.

        Every label collision on one lifecycle clip's cycle board was this: a
        count placed with next_to() on an arrow, or a return edge routed behind
        a row of labels. A bounding-box test on the path is useless, because a
        long diagonal arrow's box is mostly empty, so sample the path itself.
        """
        # Prefilter on boxes and only then sample the path. Sampling every path
        # against every word took a distribution board's check past two minutes,
        # and a check nobody waits for is a check nobody runs.
        paths = []
        for p in self._leaves((Line, Arc), here_board, exclude=(Dot,)):
            if p.get_stroke_opacity() < 0.3 or getattr(p, "vanim_transient", False):
                continue
            paths.append((p, p.get_corner(DL), p.get_corner(UR), []))
        for t in onscreen:
            x0, y0, _ = t.get_corner(DL)
            x1, y1, _ = t.get_corner(UR)
            for p, dl, ur, cache in paths:
                if dl[0] > x1 or ur[0] < x0 or dl[1] > y1 or ur[1] < y0:
                    continue                      # boxes miss, so the ink cannot hit
                if not cache:
                    try:
                        cache.extend(p.point_from_proportion(i / 24.0)
                                     for i in range(25))
                    except Exception:
                        cache.extend(p.get_all_points())
                if any(x0 < q[0] < x1 and y0 < q[1] < y1 for q in cache):
                    # Name the offending stroke and where it runs. "has a stroke
                    # through it" sends you hunting; the class and its span tell
                    # you which line to move.
                    _hit("ink-over-text",
                         f"{t.text!r} is crossed by a {type(p).__name__} spanning "
                         f"x {dl[0]:.2f}..{ur[0]:.2f}, y {dl[1]:.2f}..{ur[1]:.2f}")
                    break

    def _audit_dots(self, here_board):
        """Two dots covering each other.

        A jittered strip plot collides silently: the dots are not Text, so the
        passes above never see them. 19 points in 1.28 units of height merged
        two pairs on the cancel board and the checker still said clean.

        Two marks read as one when the clear space between their edges is
        smaller than the marks themselves, so the test is separation, not
        strict overlap. Those two pairs sat 3 pixels apart at 720p: not
        overlapping by arithmetic, merged to the eye.
        """
        dots = [d for d in self._leaves(Dot, here_board)
                if d.get_fill_opacity() > 0.3]
        for i, a in enumerate(dots):
            ca, ra = a.get_center(), a.width / 2
            for b in dots[i + 1:]:
                rb = b.width / 2
                clear = float(np.linalg.norm(ca - b.get_center())) - ra - rb
                if clear < min(ra, rb):
                    _hit("dot-collision",
                         f"two dots at ({ca[0]:.2f}, {ca[1]:.2f}) are "
                         f"{max(clear, 0):.3f} apart and read as one")


def _nearest(centres, point):
    return min(centres, key=lambda c: float(np.linalg.norm(np.array(point) - c)))


def _belongs_to(mob, centres, board_centre):
    """True when `mob` sits on the board at `board_centre`.

    A mobject with no points has no centre to place, so it is never claimed by a
    board. Keeping it is cheap and removing it by accident is not.
    """
    try:
        centre = mob.get_center()
    except Exception:
        return False
    if not np.all(np.isfinite(centre)):
        return False
    return _nearest(centres, centre) is board_centre


def _hit(kind, detail):
    key = (kind, detail)
    if key not in AUDIT_HITS:
        AUDIT_HITS.append(key)


def _overlap(a, b):
    ax0, ay0, _ = a.get_corner(DL)
    ax1, ay1, _ = a.get_corner(UR)
    bx0, by0, _ = b.get_corner(DL)
    bx1, by1, _ = b.get_corner(UR)
    w = min(ax1, bx1) - max(ax0, bx0)
    h = min(ay1, by1) - max(ay0, by0)
    if w <= 0 or h <= 0:
        return 0.0
    smaller = min((ax1 - ax0) * (ay1 - ay0), (bx1 - bx0) * (by1 - by0))
    return (w * h) / smaller if smaller else 0.0


class Timeline:
    """Lanes on a shared time axis, with an optional value plot above them.

    Nothing here is scaled after it is built, so a tick added late lands on the
    same axis as one added first.
    """

    LABEL_FRAC = 0.22

    def __init__(self, scene, lanes, t_max, w, h, where, step, unit,
                 plot_h=0.0, y_max=None, y_label=None):
        self.s, self.t_max = scene, float(t_max)
        self.plot_h, self.y_max = float(plot_h), float(y_max or 1)
        cx, cy = where[0], where[1]
        self.x0 = cx - w / 2 + w * self.LABEL_FRAC
        self.x1 = cx + w / 2
        self.top = cy + h / 2
        self.axis_y = cy - h / 2
        self.plot_base = self.top - self.plot_h

        n = max(1, len(lanes))
        usable = self.plot_base - self.axis_y - 0.45
        self.lane_y = [self.plot_base - 0.25 - (i + 0.5) * usable / n for i in range(n)]

        g = VGroup()
        g.add(Line([self.x0, self.axis_y, 0], [self.x1, self.axis_y, 0],
                   stroke_width=1.4, color=DIM_))
        step = step or self._auto_step()
        # The lowest ink the axis itself draws. window() measures its label
        # clearance from this instead of trusting a typed buff.
        self.numbers_bottom = self.axis_y
        t = 0.0
        while t <= self.t_max + 1e-6:
            x = self.x(t)
            g.add(Line([x, self.axis_y, 0], [x, self.axis_y - 0.08, 0],
                       stroke_width=1.2, color=DIM_))
            lab = T(f"{int(t)}{unit}", 13, font=MONO, color=DIM_)
            lab.next_to([x, self.axis_y - 0.1, 0], DOWN, buff=0.06)
            self.numbers_bottom = min(self.numbers_bottom, float(lab.get_bottom()[1]))
            g.add(lab)
            t += step
        self.lane_labels = []
        for i, name in enumerate(lanes):
            lab = T(name, 13, color=DIM_)
            self.lane_labels.append(lab)
            lab.move_to([self.x0 - 0.24, self.lane_y[i], 0], aligned_edge=RIGHT)
            g.add(lab)
            g.add(DashedLine([self.x0, self.lane_y[i], 0], [self.x1, self.lane_y[i], 0],
                             stroke_width=0.8, color="#333333", dash_length=0.05))
        if self.plot_h > 0:
            g.add(Line([self.x0, self.plot_base, 0], [self.x1, self.plot_base, 0],
                       stroke_width=1.0, color="#3A3A3A"))
            if y_label:
                yl = T(y_label, 14, color=DIM_)
                yl.move_to([self.x0 - 0.24, self.top - 0.1, 0], aligned_edge=RIGHT)
                g.add(yl)
        self.axis = g
        scene.add(g)

    def _auto_step(self):
        for cand in (1, 2, 5, 10, 15, 20, 30, 60, 120, 300):
            if self.t_max / cand <= 7:
                return cand
        return self.t_max / 6

    def x(self, t):
        return self.x0 + (self.x1 - self.x0) * (float(t) / self.t_max)

    def y(self, lane):
        return self.lane_y[lane]

    def py(self, value):
        return self.plot_base + self.plot_h * min(1.0, float(value) / self.y_max)

    # ----- static parts -----

    def tick(self, lane, t, color=BLUE_, height=0.22):
        y = self.y(lane)
        return Line([self.x(t), y - height / 2, 0], [self.x(t), y + height / 2, 0],
                    stroke_width=2.4, color=color)

    def span(self, lane, t0, t1, color=TEAL_, height=0.2, opacity=0.85):
        x0, x1 = self.x(t0), self.x(t1)
        r = Rectangle(width=max(x1 - x0, 0.02), height=height,
                      stroke_width=0, fill_color=color, fill_opacity=opacity)
        r.move_to([(x0 + x1) / 2, self.y(lane), 0])
        return r

    def band(self, t0, t1, color=RED_, opacity=0.14, label=None):
        x0, x1 = self.x(t0), self.x(t1)
        r = Rectangle(width=max(x1 - x0, 0.02), height=self.top - self.axis_y,
                      stroke_width=0, fill_color=color, fill_opacity=opacity)
        r.move_to([(x0 + x1) / 2, (self.top + self.axis_y) / 2, 0])
        if label is None:
            return r
        t = T(label, 13, color=color)
        t.next_to(r, UP, buff=0.06)
        return VGroup(r, t)

    def cut(self, t, color=RED_, label=None):
        line = DashedLine([self.x(t), self.axis_y, 0], [self.x(t), self.top, 0],
                          stroke_width=2, color=color, dash_length=0.08)
        if label is None:
            return line
        lab = T(label, 13, color=color)
        lab.next_to(line, UP, buff=0.06)
        return VGroup(line, lab)

    def window(self, t0, t1, color=DIM_, label=None, opacity=0.13, glass=False,
               label_dir=DOWN, label_buff=None, label_inside=False, label_at=None):
        """Shade an interval across the lanes, and name it.

        Naming the space between two events is usually worth more than another
        caption: the reader sees the interval instead of being told about it.

        A label below the axis used to land on the tick numbers, because the
        buff was a typed 0.42 and the numbers sit where the font puts them.
        With `label_buff=None` the clearance is measured from `numbers_bottom`.
        `label_at` places the label at a point you choose, which a narrow
        interval usually needs: put it in the clear band above the lanes, at
        `x(midpoint)`.
        """
        x0, x1 = self.x(t0), self.x(t1)
        r = Rectangle(width=max(x1 - x0, 0.02), height=self.plot_base - self.axis_y,
                      stroke_width=1.2 if glass else 0,
                      stroke_color=color, stroke_opacity=0.8 if glass else 0,
                      fill_color=color, fill_opacity=opacity)
        r.move_to([(x0 + x1) / 2, (self.plot_base + self.axis_y) / 2, 0])
        if label is None:
            return r
        t = T(label, 13, color=color)
        if label_at is not None:
            t.move_to([float(label_at[0]), float(label_at[1]), 0.0])
        elif label_inside:
            t.move_to(r.get_top() + DOWN * 0.24)
        else:
            buff = label_buff
            if buff is None:
                buff = 0.42
                if float(label_dir[1]) < -0.5 and abs(float(label_dir[0])) < 0.5:
                    buff = max(buff, (self.axis_y - self.numbers_bottom) + 0.12)
            t.next_to(r, label_dir, buff=buff)
        return VGroup(r, t)

    def blink(self, clock, t, color=GREEN_, width=7.0, hold=0.09, times=2):
        """A rapid flash of the playhead in the checkpoint colour, at one moment."""
        bar = Line([self.x(t), self.axis_y, 0], [self.x(t), self.plot_base, 0],
                   stroke_width=width, color=color)
        seq = []
        for _ in range(times):
            seq += [FadeIn(bar, run_time=hold), FadeOut(bar, run_time=hold)]
        return Succession(*seq)

    def note(self, lane, t, text, color=WHITE, direction=UP, buff=0.12, clears=None):
        """A label beside a lane, at one moment.

        `clears` is the height of a tick drawn at the same point. A tick spans
        half its height either side of the lane, so a tick taller than the
        default reaches into the note. Pass the tick's height and the note
        steps past its end instead of sitting on it.
        """
        if clears is not None:
            buff = max(buff, float(clears) / 2 + 0.08)
        n = T(text, 13, color=color)
        n.next_to([self.x(t), self.y(lane), 0], direction, buff=buff)
        return n

    def point(self, lane, t):
        return [self.x(t), self.y(lane), 0]

    def plot_point(self, t, value):
        return [self.x(t), self.py(value), 0]

    # ----- live: everything below reads a ValueTracker every frame -----

    def playhead(self, clock, color=WHITE, width=1.6, pulse_at=(), win=5.0):
        """A line that walks the axis, and swells as it crosses a moment that matters.

        Tagged `vanim_transient`, for the same reason `Clip.flash` tags its rays:
        the playhead is meant to pass over the notes on the lanes, so every
        crossing is intended, not a layout fault. Without the tag one timeline
        board reports a fresh ink-over-text finding at every sampled frame, and
        a checker that cries wolf on its best boards stops being read at all.
        """
        def make():
            t = min(clock.get_value(), self.t_max)
            near = min([abs(t - f) for f in pulse_at], default=1e9)
            k = 0.0 if near > win else 1.0 - near / win
            line = Line([self.x(t), self.axis_y, 0], [self.x(t), self.top, 0],
                        stroke_width=width + 3.4 * k, color=color,
                        stroke_opacity=0.40 + 0.60 * k)
            line.vanim_transient = True
            return line
        return always_redraw(make)

    def live_span(self, lane, t0, clock, cap=None, color=TEAL_, height=0.24):
        cap = self.t_max if cap is None else cap

        def make():
            t = max(t0, min(clock.get_value(), cap))
            return self.span(lane, t0, t, color=color, height=height)

        return always_redraw(make)

    def live_step(self, lane, times, clock, color=GREEN_, height=0.3):
        g = VGroup(*[self.tick(lane, t, color=color, height=height) for t in times])
        for m, t in zip(g, times):
            m.set_opacity(0)
            # full by the moment itself: a tick that fades in after t is invisible
            # during a pause that stops exactly on t
            m.add_updater(lambda m, t=t: m.set_opacity(
                min(1.0, max(0.0, (clock.get_value() - (t - 0.6)) / 0.6))))
        return g

    def at_time(self, mob, t0, clock, ramp=2.0):
        """Reveal a mobject when the clock passes t0.

        Scales each part's own opacity rather than setting it, so a band drawn at
        0.18 fill fades in to 0.18 and not to solid.
        """
        base = [(m, m.get_fill_opacity(), m.get_stroke_opacity())
                for m in mob.family_members_with_points()]

        def upd(_):
            t = clock.get_value()
            a = 0.0 if t < t0 else min(1.0, (t - t0) / ramp)
            for m, f, st in base:
                m.set_fill(opacity=f * a)
                m.set_stroke(opacity=st * a)

        upd(None)
        mob.add_updater(upd)
        return mob

    def beam(self, lane, t, color=WHITE, height=0.62, width=6.0):
        """A bright thick bar at one tick. Flash this instead of scattering a Flash.

        A Flash throws radial lines and reads as confetti. A beam on the exact tick
        points at the one thing that just happened.
        """
        y = self.y(lane)
        return Line([self.x(t), y - height / 2, 0], [self.x(t), y + height / 2, 0],
                    stroke_width=width, color=color)

    def _lattice(self, t_now, step):
        """A fixed sample grid, clipped to now.

        Resampling `n` points between 0 and t_now moves every vertex each frame, and
        the line shimmers. A fixed grid keeps the drawn vertices still.
        """
        ts, t = [], 0.0
        while t < t_now:
            ts.append(t)
            t += step
        ts.append(t_now)
        return ts

    def live_curve(self, fn, clock, color=TEAL_, width=2.6, step=None):
        """A value plotted against the same time axis, drawn as the clock advances."""
        step = step or self.t_max / 240

        def make():
            t_now = max(0.01, min(clock.get_value(), self.t_max))
            pts = [[self.x(t), self.py(fn(t)), 0] for t in self._lattice(t_now, step)]
            m = VMobject(stroke_color=color, stroke_width=width)
            m.set_points_as_corners(pts)
            return m
        return always_redraw(make)

    def live_gap(self, hi, lo, clock, color=RED_, opacity=0.30, step=None):
        """The area between two plotted values. This is usually the whole point."""
        step = step or self.t_max / 200

        def make():
            t_now = max(0.01, min(clock.get_value(), self.t_max))
            ts = self._lattice(t_now, step)
            pts = [[self.x(t), self.py(hi(t)), 0] for t in ts]
            pts += [[self.x(t), self.py(lo(t)), 0] for t in reversed(ts)]
            pts.append(pts[0])
            m = VMobject(fill_color=color, fill_opacity=opacity, stroke_width=0)
            m.set_points_as_corners(pts)
            return m
        return always_redraw(make)


class Filmstrip:
    """A frame sequence held as raw arrays, played through one ImageMobject.

    Built by `Clip.film`. Read that docstring for why this is not a Group.
    """

    def __init__(self, paths, centre, width):
        paths = list(paths)
        if not paths:
            raise ValueError("a filmstrip needs at least one frame")
        frames = [ImageMobject(p) for p in paths]
        shapes = {f.pixel_array.shape for f in frames}
        if len(shapes) != 1:
            # one odd frame would silently stretch, or throw deep inside the
            # renderer where the message names no file
            raise ValueError(f"frames differ in size: {sorted(shapes)}")
        self.arrays = [f.pixel_array for f in frames]
        self.paths = paths
        self.mob = frames[0]
        self.mob.set_width(width)
        self.mob.move_to(centre)
        self.width = width
        self.height = width * self.arrays[0].shape[0] / self.arrays[0].shape[1]
        self.centre = np.array(centre, dtype=float)

    def uv(self, u, v):
        """A point inside the frame, in fractions of its width and height.

        Overlays are placed against the footage, not against the board, so a
        ring on a button survives a change to where the film sits.
        """
        return np.array([self.centre[0] + (u - 0.5) * self.width,
                         self.centre[1] + (0.5 - v) * self.height, 0.0])

    def border(self, color="#3A3A3A", stroke_width=1.2):
        return Rectangle(width=self.width, height=self.height,
                         stroke_width=stroke_width,
                         stroke_color=color).move_to(self.centre)

    def roll(self, run_time=4.0, rate_func=linear):
        return _Roll(self, run_time=run_time, rate_func=rate_func)


class _Roll(Animation):
    """Advance a Filmstrip. interpolate_mobject gets raw alpha, so apply the
    rate function here: Animation.interpolate does not do it for you."""

    def __init__(self, strip, **kw):
        self._arrays = strip.arrays
        super().__init__(strip.mob, **kw)

    def interpolate_mobject(self, alpha):
        n = len(self._arrays)
        i = min(n - 1, max(0, int(self.rate_func(alpha) * n)))
        if getattr(self.mobject, "_vanim_frame", None) != i:
            self.mobject._vanim_frame = i
            self.mobject.pixel_array = self._arrays[i]


# ------------------------------------------------------------------ schematics
# Three conventions borrowed from schematic capture, after reading manim-eng
# (MIT, github.com/overegneered/manim-eng). Reimplemented rather than depended
# on: it pins manim <0.20 against our 0.21, and its component library is
# electrical, so none of its symbols apply to a cloud diagram. The ideas do.


# ----- fading, and why it is not set_opacity -------------------------------

def fade_now(mob, k):
    """Scale each part's own opacity, at once, with no animation.

    Never call set_opacity on a diagram. It writes fill as well as stroke, and
    manim's default fill is red (Circle is #FC6255, Ellipse subclasses it), so
    an unfilled ellipse grows a red bottom the moment anything dims it. That
    fault reached a rendered frame three separate times.

    One mobject, one dimming mechanism. These two and Clip.dim/Clip.lit both
    remember a starting opacity, so a mobject touched by both loses parts: the
    second save records the already-dimmed state.
    """
    for m in mob.family_members_with_points():
        if not hasattr(m, "_op0"):
            m._op0 = (m.get_stroke_opacity(), m.get_fill_opacity())
        m.set_stroke(opacity=m._op0[0] * k)
        m.set_fill(opacity=m._op0[1] * k)
    return mob


def fade_to(mob, k):
    """The same scaling as fade_now, as a list of animations for one beat."""
    out = []
    for m in mob.family_members_with_points():
        if not hasattr(m, "_op0"):
            m._op0 = (m.get_stroke_opacity(), m.get_fill_opacity())
        out.append(m.animate.set_stroke(opacity=m._op0[0] * k).set_fill(opacity=m._op0[1] * k))
    return out


# ----- shapes: the outline says what kind of thing it is --------------------
# Promoted on 2026-09-23 from two case-study clips that had each written them
# out by hand. The
# bodies agreed. The defaults and the docstrings had drifted, and gicon's
# colour policy survived in one copy only. That drift is what this removes.
#
# Three channels, one fact each: shape says what kind of thing it is and how it
# behaves, outline colour says its role, a badge says which hosted product.

def _pt(c):
    """A centre as a 3-vector. Every shape maker takes [x, y] or [x, y, 0].

    manim's move_to broadcasts against a 3-vector and raises on a 2-vector,
    with a shape error that names neither the shape nor the call.
    """
    return np.array([float(c[0]), float(c[1]), float(c[2]) if len(c) > 2 else 0.0])


def gicon(name, h=0.30):
    """A product badge in its own brand colour, from the icon set at ICONS.

    Colour policy, held everywhere: brand colour marks a hosted product, line
    art marks everything else, so the badge carries information rather than
    decoration. Tinting one to the house palette throws that away, and letting
    the badges carry identity flattens the map, because all 216 Google Cloud
    icons are the same blue. Node colour stays with the role.

    The loader leaves manim's default strokes on the paths (#FFFFFF, #58C4DD),
    which are not the icon's, so the stroke goes to zero and fill carries the
    shape. The fills survive because manim resolves the SVG's style classes.
    """
    m = SVGMobject(os.path.join(ICONS, name, f"{name}.svg"))
    m.set_stroke(width=0)
    m.set_height(h)
    return m


def box(c, w, h, color, corner=0.10):
    """A service, a process, anything that runs code."""
    return RoundedRectangle(corner_radius=corner, width=w, height=h, stroke_color=color,
                            stroke_width=2, fill_color=BG_, fill_opacity=1).move_to(_pt(c))


def capsule(c, w, h, color):
    """An endpoint or a trigger: something entered rather than run."""
    return box(c, w, h, color, corner=h / 2)


def cylinder(c, w, h, color, lip=0.13):
    """A store. Built from parts so no part carries manim's default fill."""
    y = h / 2 - lip
    bot = Ellipse(width=w, height=lip * 2, stroke_width=2, fill_opacity=0).shift(DOWN * y)
    body = Rectangle(width=w, height=y * 2, stroke_width=0, fill_color=BG_, fill_opacity=1)
    sides = VGroup(Line([-w / 2, y, 0], [-w / 2, -y, 0], stroke_width=2),
                   Line([w / 2, y, 0], [w / 2, -y, 0], stroke_width=2))
    top = Ellipse(width=w, height=lip * 2, stroke_width=2,
                  fill_color=BG_, fill_opacity=1).shift(UP * y)
    return VGroup(bot, body, sides, top).set_stroke(color).move_to(_pt(c))


def pail(c, w, h, color):
    """A bucket: object storage, as distinct from a database."""
    tw, bw, y = w / 2, w / 2 * 0.90, h / 2
    body = Polygon([-tw, y, 0], [tw, y, 0], [bw, -y, 0], [-bw, -y, 0], stroke_color=color,
                   stroke_width=2, fill_color=BG_, fill_opacity=1)
    rim = Line([-tw, y - 0.11, 0], [tw, y - 0.11, 0], stroke_width=1.3, color=color)
    return VGroup(body, rim).move_to(_pt(c))


def dashedbox(c, w, h, color):
    """A boundary that is not a thing: a trust zone, a deployment, a lifetime."""
    return DashedVMobject(box(c, w, h, color).set_fill(opacity=0),
                          num_dashes=30, dashed_ratio=0.55)


def node(maker, c, lines, color, w=2.3, h=0.62, icon=None, size=12):
    """A shape, an optional badge on its left, and one or two lines of mono text.

    The assert is the point: a label that outgrows its box is a fault the
    checker cannot see, because both are inside the frame and neither is text
    over text. Widen the box or shorten the label.

    Returns a VGroup carrying `.shape` and `.body`, so `ports(n.shape, ...)`
    names its attachment points and `pulse(n, ...)` rings its outline.
    """
    c = _pt(c)
    shape = maker(c, w, h, color)
    body = VGroup(*[T(t, size, font=MONO, color=color) for t in lines]).arrange(DOWN, buff=0.08)
    g = VGroup(shape)
    if icon:
        ic = gicon(icon, 0.26)
        span = ic.width + 0.14 + body.width
        left = c[0] - span / 2
        ic.move_to([left + ic.width / 2, c[1], 0])
        body.move_to([left + ic.width + 0.14 + body.width / 2, c[1], 0])
        g.add(ic)
        g.icon = ic
    else:
        body.move_to(c)
    g.add(body)
    g.shape, g.body = shape, body
    assert body.width + (0.40 if icon else 0) < w - 0.16, f"{lines} does not fit in {w}"
    return g


def pulse(n, color, t=0.8):
    """A flash that runs around a node's own outline, and stops.

    Survives updaters, which Indicate does not, because it animates a copy.
    """
    outline = getattr(n, "shape", None)
    if outline is None:
        outline = n[0] if isinstance(n, VGroup) else n
    return ShowPassingFlash(outline.copy().set_stroke(color, 5).set_fill(opacity=0),
                            time_width=0.6, run_time=t)



class Port:
    """A named attachment point that knows which way a wire leaves it.

    A wire cannot depart a node sideways, because the direction belongs to the
    port rather than to the wire. That is the whole reason ports exist here: the
    old style passed hand-typed offsets, and a lane that happened to equal its
    own destination produced a zero-length segment and an arrowhead pointing at
    nothing.
    """

    def __init__(self, at, direction, name=""):
        self.at = np.array([float(at[0]), float(at[1]), 0.0])
        d = np.array([float(direction[0]), float(direction[1]), 0.0])
        n = float(np.linalg.norm(d))
        if n == 0:
            raise ValueError(f"port {name!r} needs a direction, not {direction!r}")
        self.direction = d / n
        self.name = name
        self.nets = 0


def ports(mob, **spec):
    """Name ports on a mobject's edges. `spec` maps a name to (side, offset).

    Side is one of LEFT, RIGHT, UP, DOWN. The offset slides the port along that
    edge, so three arrivals on one face can be spread instead of stacked.
    """
    out = {}
    for name, (side, off) in spec.items():
        side = np.array([float(side[0]), float(side[1]), 0.0])
        along = np.array([-side[1], side[0], 0.0])
        out[name] = Port(mob.get_critical_point(side) + along * off, side, name)
    return out


class Bay:
    """A gutter with numbered lanes, so every vertical sits on a known x.

    Lanes are indices, never floats. A float is how `lane=3.85` ended up exactly
    on a node's own border.
    """

    def __init__(self, centre, pitch=0.20, span=None):
        self.centre, self.pitch, self.span = float(centre), float(pitch), span

    def lane(self, i):
        x = self.centre + self.pitch * i
        if self.span and not (self.span[0] < x < self.span[1]):
            raise ValueError(
                f"lane {i} of the bay at {self.centre} sits at x={x:.2f}, outside "
                f"its clear space {self.span}. It would graze a node.")
        return x


class Net(VGroup):
    """A wired connection, and the verbs that animate it.

    The verbs live here because both case studies left `net()` behind and
    hand-typed their corners: geometry alone was not worth the import when the
    lighting had to be written in the clip anyway. A net that is built here
    keeps the Bay guard, which is the whole reason the geometry exists.

    Every verb but `idle` returns a list of animations, for one beat:

        self.beat(*w.light(TEAL_), say="the worker writes a chunk")
    """

    def idle(self, k=IDLE_):
        """Wired and carrying nothing. A state, not an animation. net() calls it."""
        self.path.set_stroke(opacity=k)
        for t in self[1:]:
            t.set_fill(opacity=k)
        return self

    def light(self, color, t=0.8, k=0.9):
        """Full stroke, and a pulse that runs along the net into the target.

        The pulse says a message went down this wire at this moment. Use
        `watch` for an edge that is open and carries nothing, or the clip
        draws traffic that never happened.
        """
        return [self.path.animate.set_stroke(color, opacity=k),
                *[x.animate.set_fill(color, opacity=k) for x in self[1:]],
                ShowPassingFlash(self.path.copy().set_stroke(color, 5).set_fill(opacity=0),
                                 time_width=0.5, run_time=t)]

    def back(self, color, t=0.8):
        """A pulse against the arrow: a read returning along the net that asked."""
        rev = VMobject().set_points_as_corners(list(reversed(self.pts)))
        return [ShowPassingFlash(rev.set_stroke(color, 5).set_fill(opacity=0),
                                 time_width=0.5, run_time=t)]

    def watch(self, color, k=0.40):
        """Open, carrying nothing: a subscription, a lease, a held connection."""
        return [self.path.animate.set_stroke(color, opacity=k),
                *[x.animate.set_fill(color, opacity=k) for x in self[1:]]]

    def rest(self, k=0.30):
        """Back to a resting weight after it carried something. A lit net that
        stays lit becomes furniture, and the next pulse has nothing to say."""
        return [self.path.animate.set_stroke(opacity=k),
                *[x.animate.set_fill(opacity=k) for x in self[1:]]]


def net(a, b, bay=None, lane=0, corners=None, color=DIM_, width=1.8, opacity=1.0,
        head=True):
    """A Manhattan run between two Ports, cornering in `bay` if one is given.

    Corners are declared, not derived, so the arrowhead always has a real last
    segment to point along.

    `corners` routes a run that one bay lane cannot reach: a list of points the
    net passes through, between `a` and `b`. Every segment must be horizontal
    or vertical, and the check says which pair is not.
    """
    for end, name in ((a, "a"), (b, "b")):
        if not isinstance(end, Port):
            raise TypeError(
                f"net() takes Ports, not {type(end).__name__}. Name them with "
                f"ports(mob, {name}=(RIGHT, 0.0)), so the direction belongs to "
                f"the port and a wire cannot leave a node sideways.")
    if corners is not None:
        pts = [a.at, *[np.array([float(p[0]), float(p[1]), 0.0]) for p in corners], b.at]
    elif bay is not None:
        x = bay.lane(lane)
        pts = [a.at, np.array([x, a.at[1], 0.0]), np.array([x, b.at[1], 0.0]), b.at]
    else:
        pts = [a.at, np.array([b.at[0], a.at[1], 0.0]), b.at]
    pts = [p for i, p in enumerate(pts)
           if i == 0 or float(np.linalg.norm(p - pts[i - 1])) > 1e-6]
    if len(pts) < 2:
        raise ValueError(f"net {a.name}->{b.name} has no length")
    for u, v in zip(pts, pts[1:]):
        if abs(u[0] - v[0]) > 1e-6 and abs(u[1] - v[1]) > 1e-6:
            raise ValueError(
                f"net {a.name}->{b.name} has a diagonal segment {u[:2]} to {v[:2]}. "
                f"Add the corner between them.")
    path = VMobject(stroke_color=color, stroke_width=width, fill_opacity=0)
    path.set_points_as_corners(pts)
    g = Net(path)
    if head:
        seg = pts[-1] - pts[-2]
        tip = Triangle(fill_color=color, fill_opacity=1, stroke_width=0).scale(0.10)
        tip.rotate(np.arctan2(seg[1], seg[0]) - PI / 2).move_to(b.at)
        g.add(tip)
    g.set_stroke(opacity=opacity)
    for t in g[1:]:
        t.set_fill(opacity=opacity)
    a.nets += 1
    b.nets += 1
    g.path, g.a, g.b, g.pts = path, a, b, pts
    return g


def blobs(*nets_, radius=0.055, threshold=2):
    """Solder blobs, drawn only where more than `threshold` nets meet a point.

    manim-eng's rule, and the reason to automate it: a T junction means the nets
    connect and a plain crossing means they do not. Deciding that by hand once
    per edge is how a diagram ends up ambiguous.
    """
    seen, out = {}, VGroup()
    for g in nets_:
        for p in (g.a, g.b):
            seen.setdefault(tuple(np.round(p.at, 3)), []).append(p)
    for at, group in seen.items():
        if len(group) > threshold:
            out.add(Dot(np.array(at), radius=radius,
                        color=group[0].__dict__.get("color", WHITE)))
    return out


class Board:
    """One view in world space, with its own heading and its own caption line."""

    def __init__(self, scene, center, title, sub, h):
        self.center = np.array([float(center[0]), float(center[1]), 0.0])
        self.cap_at = self.center + np.array([0.0, -h / 2 + 0.48, 0.0])
        top = self.center + np.array([0.0, h / 2 - 0.52, 0.0])
        if title:
            t = T(title, 22).move_to(top)
            scene.add(t)
            if sub:
                scene.add(T(sub, 14, font=MONO, color=DIM_).next_to(t, DOWN, buff=0.14))
