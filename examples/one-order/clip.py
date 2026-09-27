"""One order, three traces.

Every name, edge, time and count on screen comes from flow.json, which
vizln/flow/derive.py built from the runtime evidence in evidence/. The map layout
comes from the same file: a column is the longest chain of calls that reaches a box,
and within a column the order reached the boxes from top to bottom. Wires are
Manhattan runs through numbered lanes, drawn with vanim's schematic layer.

    vizln/anim/check.sh  examples/one-order/clip.py
    vizln/anim/render.sh examples/one-order/clip.py --draft
"""
import json
from pathlib import Path

from vanim import *

F = json.loads((Path(__file__).parent / "flow.json").read_text())
FX = F["facts"]
HOP = {h["id"]: h for h in F["hops"]}
ROLE = {"checkout": TEAL_, "accounting": PLUM_, "fraud-detection": AMBER_}
TCOL = {t["short"]: ROLE.get(t["role"], BLUE_) for t in F["traces"]}
LANG = {n["id"]: n["language"] for n in F["nodes"] if n.get("language")}
NICE = {"php": "PHP", "go": "Go", "dotnet": ".NET", "cpp": "C++", "nodejs": "Node.js", "rust": "Rust",
        "ruby": "Ruby", "java": "Java", "python": "Python", "elixir": "Elixir"}
NODE = {n["id"]: n for n in F["nodes"]}
CALLER = {e["to"]: e["from"] for e in reversed(F["edges"])}   # who first reached each box
EDGE_TRACE = {(e["from"], e["to"]): HOP[e["hops"][0]]["trace"] for e in F["edges"]}

COLX = [-5.75, -3.1, -0.45, 2.35, 5.3]
COLW = [2.0, 2.0, 1.8, 2.1, 2.1]
H, HS, TOP, BOT, GAP = 0.62, 0.78, 2.3, -2.5, 0.78
BACK_X = 6.62          # the one wire that returns to an earlier box runs out here


def column(n):
    """Services sit at their call depth. A store sits one column right of its first caller."""
    if n["kind"] == "store":
        return min(column(NODE[CALLER[n["id"]]]) + 1, len(COLX) - 1)
    return min(n["depth"], len(COLX) - 1)


def spread(want):
    ys = list(want)
    for i in range(1, len(ys)):
        ys[i] = min(ys[i], ys[i - 1] - GAP)
    if ys and ys[-1] < BOT:
        ys[-1] = BOT
        for i in range(len(ys) - 2, -1, -1):
            ys[i] = max(ys[i], ys[i + 1] + GAP)
    return ys


def layout():
    cols = {}
    for n in F["nodes"]:
        cols.setdefault(column(n), []).append(n)
    pos = {}
    for c in sorted(cols):
        col = sorted(cols[c], key=lambda n: n["first_ms"])
        if c >= 4:   # beside the box that first reached it
            col.sort(key=lambda n: (-pos[CALLER[n["id"]]][1], n["first_ms"]))
            ys = spread([pos[CALLER[n["id"]]][1] for n in col])
        elif len(col) == 1:
            ys = [0.0]
        else:
            ys = [TOP - i * (TOP - BOT) / (len(col) - 1) for i in range(len(col))]
        for n, y in zip(col, ys):
            pos[n["id"]] = (COLX[c], y)
    return pos


def fan(src_port_y, targets, bay):
    """Lane per wire so a fan-out never crosses itself: rising wires turn in top-down
    order, falling wires in bottom-up order, level wires take no lane."""
    lanes, up, down = {}, [], []
    for t, (py, ty) in targets.items():
        (up if ty > py + 0.01 else down if ty < py - 0.01 else []).append((py, t))
    for i, (_, t) in enumerate(sorted(up, reverse=True)):
        lanes[t] = i
    for i, (_, t) in enumerate(sorted(down)):
        lanes[t] = i
    return lanes


class OneOrder(Clip):
    TITLE = "One order, three traces"
    SUB = (f"{len(F['nodes'])} services and stores, {len(set(LANG.values()))} languages, "
           f"all found in the runtime data")

    def story(self):
        self.source(f"{F['cluster']} · order {F['order_short']} · {F['captured_at'][11:16]} UTC")
        pos = layout()

        # ---------- boxes: shape says what kind, colour says which trace ----------
        mobs = {}
        for n in F["nodes"]:
            nid, c = n["id"], column(n)
            first = next(h["trace"] for h in F["hops"] if nid in (h["from"], h["to"]))
            col = BLUE_ if n["kind"] == "queue" else TCOL[first]
            lines = nid.split(" · ") if " · " in nid else [nid] + ([NICE.get(LANG[nid], LANG[nid])] if nid in LANG else [])
            if n["kind"] == "store":
                mobs[nid] = node(lambda c_, w_, h_, k_: cylinder(c_, w_, h_, k_, lip=0.09),
                                 pos[nid], lines, col, w=COLW[c], h=HS)
                mobs[nid].body.shift(DOWN * 0.05)   # clear the top rim
            elif n["kind"] == "queue":
                mobs[nid] = node(pail, pos[nid], lines, col, w=COLW[c], h=H)
            elif c == 0:
                mobs[nid] = node(capsule, pos[nid], lines, col, w=COLW[c], h=H)
            elif nid == "checkout":
                mobs[nid] = node(box, pos[nid], lines, col, w=COLW[c], h=1.9)
            else:
                mobs[nid] = node(box, pos[nid], lines, col, w=COLW[c], h=H)
            fade_now(mobs[nid], SLEEP_)

        # ---------- wires: Manhattan runs through lanes in the gaps ----------
        def right(nid):
            return mobs[nid].shape.get_right()[0]

        def left(nid):
            return mobs[nid].shape.get_left()[0]

        out_edges, in_edges = {}, {}
        for e in F["edges"]:
            out_edges.setdefault(e["from"], []).append(e["to"])
            in_edges.setdefault(e["to"], []).append(e["from"])
        back = {(e["from"], e["to"]) for e in F["edges"]
                if column(NODE[e["to"]]) <= column(NODE[e["from"]])}
        skip = {(e["from"], e["to"]) for e in F["edges"]
                if column(NODE[e["to"]]) - column(NODE[e["from"]]) > 1}

        # one port per wire, spread along the face in the order of the far ends
        out_port, in_port = {}, {}
        for src, tos in out_edges.items():
            fwd = sorted([t for t in tos if (src, t) not in back | skip], key=lambda t: -pos[t][1])
            half = mobs[src].shape.height / 2 - 0.12
            spec = {t: (RIGHT, 0.0 if len(fwd) == 1 else half - 2 * half * i / (len(fwd) - 1))
                    for i, t in enumerate(fwd)}
            got = ports(mobs[src].shape, **{f"p{i}": s for i, s in enumerate(spec.values())})
            for i, t in enumerate(spec):
                out_port[(src, t)] = got[f"p{i}"]
        for dst, frms in in_edges.items():
            fwd = sorted([f for f in frms if (f, dst) not in back | skip], key=lambda f: -pos[f][1])
            extra = [f for f in frms if (f, dst) in back | skip]
            spec = {f: (LEFT, 0.0 if len(fwd) == 1 else -(0.12 - 0.24 * i / max(1, len(fwd) - 1)))
                    for i, f in enumerate(fwd)}
            got = ports(mobs[dst].shape, **{f"p{i}": s for i, s in enumerate(spec.values())})
            for i, f in enumerate(spec):
                in_port[(f, dst)] = got[f"p{i}"]
            for f in extra:
                side = RIGHT if (f, dst) in back else LEFT
                in_port[(f, dst)] = ports(mobs[dst].shape, p=(side, -0.14 if side is RIGHT else -0.14))["p"]

        wires = {}
        for c in range(len(COLX) - 1):
            srcs = [s for s in out_edges if column(NODE[s]) == c]
            if not srcs:
                continue
            gap_l = max(right(s) for s in srcs)
            gap_r = min(left(t) for s in srcs for t in out_edges[s] if column(NODE[t]) == c + 1)
            n_lanes = max(1, max(len(out_edges[s]) for s in srcs))
            pitch = min(0.12, (gap_r - gap_l - 0.2) / max(1, n_lanes))
            bay = Bay(gap_l + 0.12, pitch=pitch, span=(gap_l, gap_r))
            for s in srcs:
                tgt = {t: (out_port[(s, t)].at[1], in_port[(s, t)].at[1])
                       for t in out_edges[s] if (s, t) in out_port}
                lanes = fan(None, tgt, bay)
                for t in tgt:
                    col = TCOL[EDGE_TRACE[(s, t)]]
                    if t in lanes:
                        wires[(s, t)] = net(out_port[(s, t)], in_port[(s, t)], bay=bay, lane=lanes[t], color=col)
                    else:
                        wires[(s, t)] = net(out_port[(s, t)], in_port[(s, t)], color=col)
        for (s, t) in skip:   # over the top, then down a free lane of the next gap
            p = ports(mobs[s].shape, top=(UP, 0.0))["top"]
            lane_x = left(t) - 0.12
            wires[(s, t)] = net(p, in_port[(s, t)], corners=[[p.at[0], 2.72], [lane_x, 2.72],
                                                            [lane_x, in_port[(s, t)].at[1]]],
                                color=TCOL[EDGE_TRACE[(s, t)]])
        for (s, t) in back:   # out to the right edge, and back into the earlier box
            p = ports(mobs[s].shape, back=(RIGHT, 0.0))["back"]
            q = in_port[(s, t)]
            wires[(s, t)] = net(p, q, corners=[[BACK_X, p.at[1]], [BACK_X, q.at[1]]],
                                color=TCOL[EDGE_TRACE[(s, t)]])

        for w in wires.values():
            w.idle()                 # wired and carrying nothing until a message goes down it
        self.add(*wires.values())
        self.beat(*[FadeIn(m) for m in mobs.values()],
                  say="every box was found in traces, none in code", color=DIM_, hold=1.0)
        self.beat(say=f"the order is 1 of {F['scope']['top_level_requests']} requests that share its trace",
                  color=DIM_, hold=1.2)

        def spans_txt(t):
            return f"{t['order_spans']} of {t['spans']}" if t["order_spans"] != t["spans"] else f"{t['spans']}"

        clock = self.tracker(0)
        self.live_text(lambda: f"{clock.get_value():6.1f} ms", [4.9, -3.2, 0], font_size=18, color=WHITE)
        chips = {t["short"]: T(f"{t['short']} {t['role']} {spans_txt(t)} spans", 12, font=MONO,
                               color=TCOL[t["short"]]).move_to([-6.6, -1.7 - i * 0.36, 0], aligned_edge=LEFT)
                 for i, t in enumerate(F["traces"])}
        consumer_wire = {h["to"]: (h["from"], h["to"]) for h in F["hops"] if h["kind"] == "consume"}

        # the consumers were already waiting: each poll span opened before the order came
        waiting = sorted([(t["root_opened_ms"], t) for t in F["traces"] if t["role"] in consumer_wire])
        early = [t for ms_, t in waiting if ms_ <= 0]
        later = [(ms_, t) for ms_, t in waiting if ms_ > 0]
        if early:
            self.beat(*[a for t in early for a in wires[consumer_wire[t["role"]]].watch(TCOL[t["short"]])],
                      *[a for t in early for a in fade_to(mobs[t["role"]], 0.5)],
                      say=f"{' and '.join(t['role'] for t in early)} already waits on Kafka",
                      color=TCOL[early[0]["short"]], hold=1.2)

        shown, lit_last = set(), []

        def light(e):
            key = (e["from"], e["to"])
            h = HOP[e["hops"][0]]
            col, w = TCOL[h["trace"]], wires[key]
            anims = [*w.light(col), *fade_to(mobs[e["from"]], 1.0), *fade_to(mobs[e["to"]], 1.0)]
            new = h["trace"] not in shown
            if new:
                shown.add(h["trace"])
                anims.append(FadeIn(chips[h["trace"]]))
            return anims, new, h, key

        say_at = {"checkout": f"{CALLER['checkout']} calls checkout",
                  "quote": f"{CALLER['quote']} asks the {NICE.get(LANG['quote'], LANG['quote'])} quote service",
                  FX["queue"]: "checkout drops the order in Kafka"}
        events = [("edge", e["first_ms"], e) for e in F["edges"]]
        events += [("wait", ms_, t) for ms_, t in later]
        events.sort(key=lambda x: x[1])
        prev, i = 0.0, 0
        after_pub = False
        while i < len(events):
            kind, t, obj = events[i]
            burst = [events[i]]
            while (i + 1 < len(events) and events[i + 1][0] == "edge" and kind == "edge"
                   and events[i + 1][1] - t <= 3.0 and events[i + 1][2]["kind"] not in ("publish", "consume")
                   and obj["kind"] not in ("publish", "consume")):
                i += 1
                burst.append(events[i])
            i += 1
            if not after_pub and t > FX["publish_ms"]:
                after_pub = True
                self.beat(*[a for k in lit_last for a in wires[k].rest()],
                          say=f"the consumers are not in trace {F['traces'][0]['short']}", color=TEAL_, hold=1.2)
                lit_last = []
            t = burst[-1][1]   # the clock lands on the last call it lights
            self.sweep(clock, t, min(1.1, max(0.3, (t - prev) / 25)))
            prev = t
            anims = [a for k in lit_last for a in wires[k].rest()]
            lit_last, say, col = [], None, WHITE
            for kind_, _, o in burst:
                if kind_ == "wait":
                    anims += [*wires[consumer_wire[o["role"]]].watch(TCOL[o["short"]]),
                              *fade_to(mobs[o["role"]], 0.5)]
                    say, col = f"{o['role']} starts waiting on Kafka", TCOL[o["short"]]
                    continue
                a, new, h, key = light(o)
                anims += a
                lit_last.append(key)
                if o["kind"] == "consume" and new:
                    say, col = f"{o['to']}: {round(h['t_ms'] - FX['publish_ms'], 1)} ms later, in a different trace", TCOL[h["trace"]]
                elif o["to"] in say_at:
                    say, col = say_at[o["to"]], TEAL_
            self.beat(*anims, say=say, color=col, hold=1.1 if say else 0.3, run=0.55)
        self.beat(*[a for k in lit_last for a in wires[k].rest()], hold=0.6)


        # ---------- zoom: where checkout's time goes ----------
        enter = next(h for h in F["hops"] if h["to"] == "checkout")
        calls = sorted([h for h in F["hops"] if h["from"] == "checkout"], key=lambda h: h["t_ms"])
        t0, span = enter["t_ms"], enter["dur_ms"]
        in_calls = round(sum(h["dur_ms"] for h in calls), 1)
        cx, cy = mobs["checkout"].get_center()[:2]
        view_w = 9.4
        pw, ph = 6.5, 4.0
        px, py = mobs["checkout"].shape.get_right()[0] + 0.25 + pw / 2, cy - 0.2
        panel = RoundedRectangle(corner_radius=0.08, width=pw, height=ph, stroke_color=DIM_, stroke_width=1.2,
                                 fill_color=BG_, fill_opacity=1).move_to([px, py, 0])
        head = T(f"checkout: {span} ms, and where it goes", 12, color=WHITE).move_to(
            [px - pw / 2 + 0.25, py + ph / 2 - 0.25, 0], aligned_edge=LEFT)
        note = T(f"order {F['order_short']} · each bar is the called service's own span", 10,
                 color=DIM_).next_to(head, DOWN, buff=0.08, aligned_edge=LEFT)
        ax_l, ax_r = px - pw / 2 + 2.25, px + pw / 2 - 0.3
        top_y, row = note.get_bottom()[1] - 0.22, (ph - 1.45) / len(calls)

        def x_of(t):
            return ax_l + (t - t0) / span * (ax_r - ax_l)

        frame = Rectangle(width=ax_r - ax_l, height=row * len(calls) + 0.08, stroke_color=DIM_,
                          stroke_width=0.8).move_to([(ax_l + ax_r) / 2, top_y - row * len(calls) / 2, 0])
        bars, labels = [], []
        for i, h in enumerate(calls):
            y = top_y - row * (i + 0.5)
            col = BLUE_ if h["kind"] == "publish" else TCOL[h["trace"]]
            w = max(0.03, x_of(h["t_ms"] + h["dur_ms"]) - x_of(h["t_ms"]))
            bars.append(Rectangle(width=w, height=row * 0.62, stroke_width=0, fill_color=col,
                                  fill_opacity=0.85).move_to([x_of(h["t_ms"]) + w / 2, y, 0]))
            name = h["to"].split(" · ")[0]
            labels.append(T(f"{name}  {h['dur_ms']} ms", 10, font=MONO, color=col).move_to(
                [px - pw / 2 + 0.25, y, 0], aligned_edge=LEFT))
        ticks = VGroup(T(f"{t0} ms", 9, font=MONO, color=DIM_).next_to(frame, DOWN, buff=0.06, aligned_edge=LEFT),
                       T(f"{round(t0 + span, 1)} ms", 9, font=MONO, color=DIM_).next_to(frame, DOWN, buff=0.06,
                                                                                    aligned_edge=RIGHT))
        foot = T(f"{in_calls} ms inside the called services, {round(span - in_calls, 1)} ms in checkout "
                 f"itself and on the network", 10, color=DIM_).move_to(
            [px - pw / 2 + 0.25, py - ph / 2 + 0.2, 0], aligned_edge=LEFT)

        self.play(self.zoom_to([(mobs['checkout'].shape.get_left()[0] + px + pw / 2) / 2, py, 0], width=view_w),
                  run_time=1.2)
        self.play(FadeIn(panel), FadeIn(head), FadeIn(note), FadeIn(frame), FadeIn(ticks),
                  pulse(mobs['checkout'], TEAL_), run_time=0.6)
        for grp in (range(0, 6), range(6, len(calls))):
            self.play(*[FadeIn(labels[i]) for i in grp],
                      *[FadeIn(bars[i], shift=RIGHT * 0.08) for i in grp], run_time=0.8)
            self.wait(0.8)
        self.play(FadeIn(foot), run_time=0.4)
        self.wait(2.4)
        self.play(*[FadeOut(m) for m in (panel, head, note, frame, ticks, foot, *bars, *labels)], run_time=0.4)
        self.play(self.zoom_out(), run_time=1.0)
        self.beat(say="one order: three traces, joined by a span link and the order id", color=WHITE, hold=2.4)
