"""Import flow: what a restarted Temporal activity has to do again.

Board 1 (origin)   the run on a time axis
Board 2 (right)    rows at risk, as a sawtooth, then a zoom on the last climb
Board 3 (below)    three shutdowns

The figure carries the argument. Captions are labels, not narration.
"""
from vanim import *

TOTAL = 8010
RATE = 55
SIGTERM = 145
POD2 = 172
FINISH = 198
T_END = 240

FLUSH = [0, 60, 120]
BEATS_A = list(range(10, SIGTERM, 10))
BEATS_B = [182, 192]
KEPT = RATE * 120           # 6,600
LOST = RATE * SIGTERM - KEPT  # 1,375
POD_A, POD_B = TEAL_, PLUM_


def parsed(t):
    if t <= SIGTERM:
        return RATE * t
    if t < POD2:
        return KEPT
    return min(TOTAL, KEPT + RATE * (t - POD2))


def saved(t):
    if t >= FINISH:
        return TOTAL
    last = max([f for f in FLUSH if f <= min(t, SIGTERM)], default=0)
    return RATE * last


def risk(t):
    return max(0, int(parsed(t) - saved(t)))


class Heartbeat(Clip):
    TITLE = "Import flow"
    SUB = "Temporal activity  ·  GCS CSV  ·  pod replaced"

    def story(self):
        clock = self.tracker(0)
        pen = self.tracker(0)

        # two columns, one shared x each, so the digits never drift
        self.counter("parsed", lambda: f"{int(parsed(clock.get_value())):,}",
                     [-3.3, 2.52, 0], size=21, color=POD_A)
        self.c_saved = self.counter("server has", lambda: f"{int(saved(clock.get_value())):,}",
                                    [2.7, 2.52, 0], size=21, color=GREEN_)
        self.c_risk = self.counter("at risk", lambda: f"{risk(clock.get_value()):,}",
                                   [-3.3, 1.98, 0], size=21, color=GLASS_)

        tl = self.timeline(
            ["rows parsed", "heartbeat", "server wrote", "pod"],
            t_max=T_END, w=11.9, h=4.1, where=DOWN * 0.55, step=60,
        )
        self.add(tl.playhead(clock))
        self.add(tl.live_span(0, 0, clock, cap=SIGTERM, color=POD_A, height=0.26))
        self.add(tl.live_span(3, 0, clock, cap=SIGTERM, color=POD_A, height=0.14))
        for m, t0 in ((tl.span(0, POD2, FINISH, color=POD_B, height=0.26), POD2),
                      (tl.span(3, POD2, 208, color=POD_B, height=0.14), POD2)):
            self.add(tl.at_time(m, t0, clock, ramp=1.0))
        self.add(tl.live_step(1, BEATS_A + BEATS_B, clock, color=BLUE_, height=0.2))
        self.add(tl.live_step(2, FLUSH + [FINISH], clock, color=GREEN_, height=0.34))

        dead = tl.window(SIGTERM, POD2, color=DIM_, label="no worker", opacity=0.10,
                         label_buff=0.62)
        self.add(tl.at_time(dead, SIGTERM, clock, ramp=0.8))
        again = tl.window(POD2, FINISH, color=GLASS_, label="parsed again",
                          opacity=0.16, glass=True, label_inside=True)
        self.add(tl.at_time(again, POD2, clock, ramp=0.8))
        stop = tl.cut(SIGTERM, color=AMBER_, label="SIGTERM")
        self.add(tl.at_time(stop, SIGTERM, clock, ramp=0.5))

        # ---------- board 1 ----------
        self.sweep(clock, 40, 2.0, say="pod A parses the file", color=POD_A, hold=0.5)
        self.sweep(clock, 52, 0.9, say="heartbeat every 10s", color=BLUE_)
        self._write(clock, tl, 60, "the server writes")
        self.sweep(clock, 90, 1.6, say="the gap lives only in this worker", color=GLASS_,
                   ease="in")
        self.sweep(clock, 112, 1.4)
        self._write(clock, tl, 120, "written again")
        self.sweep(clock, SIGTERM - 0.6, 2.2, ease="in")
        self.beat(say="SIGTERM", color=AMBER_, hold=1.2)
        self.sweep(clock, SIGTERM + 3, 0.4, say="the context dies with the rows in it",
                   color=GLASS_, hold=1.6)
        self.sweep(clock, POD2 + 4, 1.6, say="pod B takes the activity", color=POD_B,
                   ease="both", hold=0.6)
        self.sweep(clock, FINISH + 8, 2.4, say=f"{LOST:,} rows, parsed twice",
                   color=GLASS_, ease="both", hold=1.4)

        # ---------- board 2: rows at risk ----------
        plot = self.board(RIGHT * 17, "Rows at risk", "it returns to zero only when the server writes")
        pl = self.timeline([], t_max=T_END, w=11.4, h=4.2, where=RIGHT * 17 + DOWN * 0.5,
                           step=60, plot_h=3.7, y_max=3500, y_label="rows")
        self.add(pl.live_gap(risk, lambda t: 0, pen, color=GLASS_, opacity=0.42))
        self.add(pl.live_curve(risk, pen, color=GLASS_, width=3.0))
        drops = VGroup()
        for t, col, lab in ((60, GREEN_, "written"), (120, GREEN_, "written"),
                            (SIGTERM, AMBER_, "lost"), (FINISH, GREEN_, "written")):
            d = Dot(pl.plot_point(t, risk(t - 0.5)), radius=0.075, color=col)
            drops.add(VGroup(d, T(lab, 13, color=col).next_to(d, UP, buff=0.12)))

        self.travel(plot, hold=0.0)
        self.sweep(pen, T_END, 3.2, say="every climb is work the server cannot see",
                   color=GLASS_, hold=0.5)
        peak = VGroup(
            T(f"{LOST:,}", 15, color=AMBER_).move_to(
                pl.plot_point(SIGTERM - 16, LOST + 260)),
            T("3,300", 15, color=GLASS_).move_to(pl.plot_point(44, 3300 + 260)),
        )
        self.beat(*self.show(drops, peak), hold=1.2)

        # ---------- zoom on the last climb ----------
        self.play(self.zoom_to(pl.plot_point(185, 900), width=5.4))
        self.wait(0.4)
        z = T("the same 1,375 rows, climbed again", 13, color=GLASS_)
        z.move_to(pl.plot_point(185, 2100))
        self.play(FadeIn(z), run_time=0.4)
        self.wait(1.7)
        self.play(FadeOut(z), self.zoom_out())

        # ---------- board 3: three shutdowns ----------
        scen = self.board(DOWN * 10.5, "Three shutdowns", "shaded is what a retry repeats")
        built = []
        for i, (name, kept, again_s, verdict, col) in enumerate([
            ("no stop timeout", 120, 25, "1,375 rows twice", GLASS_),
            ("worker awaits closers, 30s", 145, 0, "nothing repeats", GREEN_),
            ("30s pod grace, unused", 120, 25, "unused by the process", AMBER_),
        ]):
            y = -10.5 + 1.3 - i * 1.35
            g = VGroup(T(name, 15).move_to([-6.3, y, 0], aligned_edge=LEFT))
            wg = 4.6 * kept / 145.0
            g.add(Rectangle(width=wg, height=0.26, stroke_width=0,
                            fill_color=GREEN_, fill_opacity=0.85)
                  .move_to([-1.1 + wg / 2, y, 0]))
            if again_s:
                wr = 4.6 * again_s / 145.0
                g.add(Rectangle(width=wr, height=0.26, stroke_width=1.2,
                                stroke_color=GLASS_, fill_color=GLASS_, fill_opacity=0.34)
                      .move_to([-1.1 + wg + wr / 2, y, 0]))
            g.add(T(verdict, 14, color=col).move_to([3.6, y, 0], aligned_edge=LEFT))
            built.append(g)

        self.travel(scen, hold=0.0)
        for g in built:
            self.beat(*self.show(g), hold=0.7)
        self.beat(say="checkpoint at a heartbeat boundary", color=WHITE, hold=1.6)

        # ---------- board 4: everything above assumed the create was idempotent ----------
        idem = self.board(DOWN * 21, "The replay is only free if the create is",
                          "every board above assumed re-parsing a row is a no-op")
        y0 = -21 + 1.0
        rows4 = [
            ("upsert on a stable key", TOTAL, 0, GREEN_,
             f"{TOTAL:,} items, none repeated"),
            ("fresh UUID per row", TOTAL, LOST, GLASS_,
             f"{TOTAL + LOST:,} items, {LOST:,} duplicated"),
        ]
        made = []
        for i, (name, keep, dup, col, verdict) in enumerate(rows4):
            y = y0 - i * 1.5
            g = VGroup(T(name, 15).move_to([-6.4, y, 0], aligned_edge=LEFT))
            wk = 3.4
            g.add(Rectangle(width=wk, height=0.3, stroke_width=0,
                            fill_color=TEAL_, fill_opacity=0.8)
                  .move_to([-1.5 + wk / 2, y, 0]))
            if dup:
                wd = max(0.35, 3.4 * dup / TOTAL)
                g.add(Rectangle(width=wd, height=0.3, stroke_width=1.2,
                                stroke_color=GLASS_, fill_color=GLASS_, fill_opacity=0.45)
                      .move_to([-1.5 + wk + wd / 2, y, 0]))
            g.add(T(verdict, 14, color=col).move_to([3.3, y, 0], aligned_edge=LEFT))
            made.append(g)

        self.travel(idem, hold=0.0)
        self.beat(*self.show(made[0]), say="if the write is an upsert, nothing is wrong",
                  color=GREEN_, hold=1.5)
        self.beat(*self.show(made[1]),
                  say="minting a UUID per row makes the retry create them again",
                  color=GLASS_, hold=2.0)
        fix = T("a deterministic id from (object, row) makes the retry a no-op",
                15, color=GREEN_).move_to([0, -21 - 1.6, 0])
        self.beat(*self.show(fix),
                  say="a non-idempotent create turns lost work into wrong data",
                  color=GLASS_, hold=2.4)

    def _write(self, clock, tl, t, say):
        """One event, one pause, and the clock stops exactly on it.

        Stopping past the write leaves a non-zero at-risk count on screen during the
        pause, which says the opposite of what the pause is for. Decelerate in, land
        on t where the count is zero, show the transfer, hold, then accelerate away.
        """
        self.sweep(clock, t, 1.3, say=say, color=GREEN_, ease="out")
        arrow = self.transfer(self.c_risk.out_low, self.c_saved.in_low,
                              GREEN_, angle=-0.25)
        self.play(tl.blink(clock, t, color=GREEN_), Create(arrow, run_time=0.5))
        self.play(Indicate(tl.lane_labels[2], color=GREEN_, scale_factor=1.12),
                  Indicate(self.c_saved, color=GREEN_, scale_factor=1.10), run_time=0.55)
        self.wait(1.2)
        self.play(FadeOut(arrow), run_time=0.3)
