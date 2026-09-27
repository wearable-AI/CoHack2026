"""One order, three traces.

Every name, edge, time and count on screen comes from flow.json, which
vizln/flow/derive.py built from the runtime evidence in evidence/. The map layout
comes from the same file: a column is the longest chain of calls that reaches a box,
and within a column the order reached the boxes from top to bottom.

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
XS = [-5.8, -3.48, -1.16, 1.16, 3.48, 5.8]
W, H, H2 = 1.9, 0.44, 0.62
TOP, BOT, GAP = 2.3, -2.75, 0.74
LANG = {n["id"]: n["language"] for n in F["nodes"] if n.get("language")}
NICE = {"php": "PHP", "go": "Go", "dotnet": ".NET", "cpp": "C++", "nodejs": "Node.js", "rust": "Rust",
        "ruby": "Ruby", "java": "Java", "python": "Python", "elixir": "Elixir"}
CALLER = {e["to"]: e["from"] for e in reversed(F["edges"])}   # who first reached each box


def spread(want):
    """Keep boxes in a column apart, in the order asked, inside TOP and BOT."""
    ys = list(want)
    for i in range(1, len(ys)):
        ys[i] = min(ys[i], ys[i - 1] - GAP)
    if ys and ys[-1] < BOT:
        ys[-1] = BOT
        for i in range(len(ys) - 2, -1, -1):
            ys[i] = max(ys[i], ys[i + 1] + GAP)
    return ys


def layout():
    """Services by depth. A store is drawn once per caller, one column to its right,
    so no wire runs backwards across the map. Each copy takes the colour of the trace
    that its calls belong to."""
    boxes = [dict(n) for n in F["nodes"] if n["kind"] != "store"]
    depth = {n["id"]: n["depth"] for n in F["nodes"]}
    for e in F["edges"]:
        if e["kind"] == "store":
            boxes.append({"id": f"{e['to']}@{e['from']}", "store": e["to"], "kind": "store",
                          "depth": depth[e["from"]] + 1, "first_ms": e["first_ms"], "parent": e["from"],
                          "trace": HOP[e["hops"][0]]["trace"]})
    parent = {}
    for e in F["edges"]:
        parent.setdefault(e["to"], e["from"])
    cols = {}
    for b in boxes:
        cols.setdefault(b["depth"], []).append(b)
    pos = {}
    for d in sorted(cols):
        col = sorted(cols[d], key=lambda b: b["first_ms"])
        if d >= 4:   # anchor each box beside the box that first reached it
            col.sort(key=lambda b: (-pos[b.get("parent") or parent[b["id"]]][1], b["first_ms"]))
            ys = spread([pos[b.get("parent") or parent[b["id"]]][1] for b in col])
        elif len(col) == 1:
            ys = [0.0]
        else:
            step = (TOP - BOT) / (len(col) - 1)
            ys = [TOP - i * step for i in range(len(col))]
        for b, y in zip(col, ys):
            pos[b["id"]] = (XS[d], y)
    return boxes, pos


def first_trace(node_id):
    return next(h["trace"] for h in F["hops"] if node_id in (h["from"], h["to"]))


class OneOrder(Clip):
    TITLE = "One order, three traces"
    SUB = (f"{len(F['nodes'])} services and stores, {len(set(LANG.values()))} languages, "
           f"all found in the runtime data")

    def story(self):
        self.source(f"{F['cluster']} · order {F['order_short']} · {F['captured_at'][11:16]} UTC")
        boxes, pos = layout()

        def thin_lip(c, w, h, color):
            return cylinder(c, w, h, color, lip=0.09)

        mobs = {}
        for b in boxes:
            name = b.get("store", b["id"])
            col = BLUE_ if b["kind"] == "queue" else TCOL[b.get("trace") or first_trace(name)]
            if b["kind"] == "store":
                mobs[b["id"]] = node(thin_lip, pos[b["id"]], name.split(" · "), col, w=W, h=H2)
                mobs[b["id"]].body.shift(DOWN * 0.05)   # clear the top rim
            elif b["kind"] == "queue":
                mobs[b["id"]] = node(capsule, pos[b["id"]], name.split(" · "), col, w=W, h=H2)
            elif name in LANG:
                mobs[b["id"]] = node(box, pos[b["id"]], [name, NICE.get(LANG[name], LANG[name])], col, w=W, h=H2)
            else:
                mobs[b["id"]] = node(box, pos[b["id"]], [name], col, w=W, h=H)
            fade_now(mobs[b["id"]], SLEEP_)

        def box_of(frm, to):
            return f"{to}@{frm}" if f"{to}@{frm}" in mobs else to

        # spread each box's wires along its edge, in the order of the far ends
        ends = [(e["from"], box_of(e["from"], e["to"])) for e in F["edges"]]
        out_at, in_at = {}, {}
        for side, idx, other in (("out", 0, 1), ("in", 1, 0)):
            groups = {}
            for pair in ends:
                groups.setdefault(pair[idx], []).append(pair)
            for b, pairs in groups.items():
                pairs.sort(key=lambda p: -pos[p[other]][1])
                half = (H2 if mobs[b].shape.height > 0.5 else H) / 2 - 0.08
                for i, p in enumerate(pairs):
                    off = 0.0 if len(pairs) == 1 else half - 2 * half * i / (len(pairs) - 1)
                    (out_at if side == "out" else in_at)[p] = off
        wires = {}
        for e, pair in zip(F["edges"], ends):
            a, b = mobs[pair[0]].shape, mobs[pair[1]].shape
            wires[(e["from"], e["to"])] = Line(a.get_right() + UP * out_at[pair], b.get_left() + UP * in_at[pair],
                                               stroke_width=1.4, color=DIM_).set_stroke(opacity=0.35)
        self.beat(*[FadeIn(m) for m in mobs.values()], *[FadeIn(w) for w in wires.values()],
                  say="every box was found in traces, none in code", color=DIM_, hold=1.0)
        self.beat(say=f"the order is 1 of {F['scope']['top_level_requests']} requests that share its trace",
                  color=DIM_, hold=1.2)

        def spans_txt(t):
            return f"{t['order_spans']} of {t['spans']}" if t["order_spans"] != t["spans"] else f"{t['spans']}"

        # ---------- the order moves, one stop per burst of calls ----------
        clock = self.tracker(0)
        self.live_text(lambda: f"t = {clock.get_value():6.1f} ms", [-6.6, -1.55, 0], font_size=15, color=DIM_)
        chips = {t["short"]: T(f"{t['short']} {t['role']} {spans_txt(t)} spans", 12, font=MONO,
                               color=TCOL[t["short"]]).move_to([-6.6, -2.0 - i * 0.36, 0], aligned_edge=LEFT)
                 for i, t in enumerate(F["traces"])}
        shown = set()

        def light(e):
            h = HOP[e["hops"][0]]
            col, w, far = TCOL[h["trace"]], wires[(e["from"], e["to"])], mobs[box_of(e["from"], e["to"])]
            anims = [ShowPassingFlash(w.copy().set_stroke(col, 5, opacity=1), time_width=0.6),
                     w.animate.set_stroke(col, 2.2, opacity=0.8),
                     *fade_to(mobs[e["from"]], 1.0), *fade_to(far, 1.0)]
            new = h["trace"] not in shown
            if new:
                shown.add(h["trace"])
                anims.append(FadeIn(chips[h["trace"]]))
            return anims, new, h, far

        say_at = {"checkout": f"{CALLER['checkout']} calls checkout",
                  "quote": f"{CALLER['quote']} asks the {NICE.get(LANG['quote'], LANG['quote'])} quote service",
                  FX["queue"]: "checkout drops the order in Kafka"}
        sync = [e for e in F["edges"] if e["first_ms"] <= FX["publish_ms"]]
        after = [e for e in F["edges"] if e["first_ms"] > FX["publish_ms"]]
        bursts = []
        for e in sync:
            if bursts and e["first_ms"] - bursts[-1][-1]["first_ms"] <= 3.0 and e["kind"] != "publish":
                bursts[-1].append(e)
            else:
                bursts.append([e])
        prev = 0.0
        for burst in bursts:
            t = burst[0]["first_ms"]
            self.sweep(clock, t, min(1.1, max(0.3, (t - prev) / 40)))
            prev = t
            anims, say = [], None
            for e in burst:
                a, _, _, _ = light(e)
                anims += a
                say = say_at.get(e["to"], say)
            self.beat(*anims, say=say, color=TEAL_ if say else WHITE, hold=0.9 if say else 0.25, run=0.5)

        # ---------- after the queue: the order enters other traces ----------
        self.beat(say=f"the consumers are not in trace {F['traces'][0]['short']}", color=TEAL_, hold=1.2)
        for e in after:
            self.sweep(clock, e["first_ms"], 0.6)
            anims, new, h, far = light(e)
            say = f"{e['to']}: {round(h['t_ms'] - FX['publish_ms'], 1)} ms later, in a different trace" if new else None
            self.beat(*anims, pulse(far, TCOL[h["trace"]]), say=say, color=TCOL[h["trace"]],
                      hold=1.2 if new else 0.4, run=0.5)

        # ---------- board 2: what joins the three ----------
        b2 = self.board(DOWN * 10, "Jaeger sees three stories", "three facts in the data make them one")
        y0 = -10 + 1.7
        rows = VGroup(*[
            T(f"{t['short']}   {t['role']:<16} {spans_txt(t):>9} spans   has the order at {t['order_ms']} ms",
              15, font=MONO, color=TCOL[t["short"]]).move_to([-6.2, y0 - i * 0.5, 0], aligned_edge=LEFT)
            for i, t in enumerate(F["traces"])])
        offs = sorted(set(FX["kafka_offsets"].values()))
        reached = [j for j in F["joins"] if j["what"].startswith("the order id also reaches") and j["ok"]]
        link = VGroup(
            T(f"1. both consumers point back at checkout's Kafka span {FX['publish_span']}", 15,
              color=WHITE).move_to([-6.2, y0 - 1.9, 0], aligned_edge=LEFT),
            T(f"2. the two consumers read the same Kafka message, offset {', '.join(map(str, offs))}", 15,
              color=WHITE).move_to([-6.2, y0 - 2.4, 0], aligned_edge=LEFT),
            T(f"3. in {len(reached)} consumer traces, a log line names order {F['order_short']} "
              f"and carries that trace id", 15, color=WHITE).move_to([-6.2, y0 - 2.9, 0], aligned_edge=LEFT))
        st = F["stores"]
        miss = sorted(set(st["opensearch"]["services"]) - set(st["cloud-logging"]["services"]))
        logs = VGroup(
            T(f"OpenSearch: {st['opensearch']['lines_naming_order']} lines name the order, from "
              f"{len(st['opensearch']['services'])} services", 15, color=GREEN_).move_to(
                [-6.2, y0 - 3.8, 0], aligned_edge=LEFT),
            T(f"Cloud Logging: {st['cloud-logging']['lines_naming_order']} lines name the order, none from "
              f"{' or '.join(miss)}", 15, color=AMBER_).move_to([-6.2, y0 - 4.3, 0], aligned_edge=LEFT))
        self.travel(b2, hold=0.0)
        self.beat(*self.show(rows), say="three trace ids for one order", hold=1.2)
        self.beat(*self.show(link), say="a span link, a Kafka offset and the order id join them", hold=2.0)
        self.beat(*self.show(logs), say="and the logs are split across two stores", color=AMBER_, hold=1.8)

        # ---------- board 3: how this clip was made ----------
        b3 = self.board(DOWN * 20, "How this clip was made", "runtime data only, no source code")
        steps = [f"{FX['questions']} questions", f"{FX['evidence_files']} raw files",
                 f"{FX['joins_passed']} checks pass", f"flow.json, {FX['hops']} hops", "this clip"]
        self.travel(b3, hold=0.0)
        flow_, _ = self.chain(steps, colours=[BLUE_, BLUE_, GREEN_, TEAL_, WHITE],
                              where=DOWN * 20 + UP * 0.4, w=12.6, h=1.0)
        self.beat(*self.show(flow_), say="asked, saved, joined, checked, drawn", hold=1.4)
        self.beat(say="Jaeger sees three stories. The span link and the order id make them one.",
                  color=WHITE, hold=2.6)
