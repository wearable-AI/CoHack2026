"""Smoke test and template. Exercises code(), chain(), mark() and beat().

    anim/render.sh anim/examples/smoke.py --draft
"""
from vanim import *

SRC = '''func parse(format string) ([]Token, error) {
    parts := strings.Split(format, "/")
    for i, p := range parts {
        if isPlaceholder(p) {
            continue
        }
        if !labelRe.MatchString(p) {
            return nil, fmt.Errorf("bad label %q", p)
        }
    }
    return toks, nil
}'''


class Smoke(Clip):
    TITLE = "One beat per thing the reader must see"
    SUB = "example: a format parser"

    def story(self):
        panel, lines = self.code(SRC, "go", where=LEFT, w=6.6, h=4.6)
        flow, boxes = self.chain(
            ["format string", "parse", "tokens", "validate"],
            colours=[DIM_, BLUE_, TEAL_, GREEN_],
            where=RIGHT * 3.6 + UP * 1.2, w=6.2, h=1.2,
            caption="where the change sits",
        )

        self.beat(say="the format arrives as one string", color=DIM_)
        self.beat(self.mark(lines[1]), say="split on the separator", color=BLUE_)
        self.beat(self.mark(lines[3]), say="a placeholder needs no check", color=TEAL_)
        self.beat(self.mark(lines[6]), say="a label must match the regex", color=GREEN_)
        self.beat(self.mark(lines[7]), say="and this is the error the pod dies on", color=RED_)
        self.beat(self.unmark(), say="", hold=0.3)
