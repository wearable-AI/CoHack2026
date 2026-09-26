"""Five deliberate faults. check.sh --self-test runs this and expects all five.

A layout checker that collects nothing reports clean forever, which is worse than
having no checker. This file is the proof that it still works. Do not fix it.

The last two were added when the checker reported `clean` on a clip whose frames
had a count sitting on an arrow and two strip-plot dots merged into one blob. It
only ever compared Text against Text, so everything a clip drew with raw manim
was unchecked.
"""
from vanim import *


class Faults(Clip):
    TITLE = "deliberate faults"

    def story(self):
        self.add(T("this text is far off the right edge", 17).move_to([10, 0, 0]))
        self.add(T("overlapping one", 17).move_to([0, 1, 0]))
        self.add(T("overlapping two", 17).move_to([0.1, 1.02, 0]))
        self.add(T("tiny", 3).move_to([0, -2, 0]))
        # a stroke straight through a word, which no Text-vs-Text pass can see
        self.add(T("an arrow runs through this", 17).move_to([0, -0.6, 0]))
        self.add(Arrow([-3, -0.9, 0], [3, -0.3, 0], stroke_width=2, color=AMBER_))
        # two dots covering each other, as a jittered strip plot does
        self.add(Dot([-4.0, 2.0, 0], radius=0.07, color=RED_))
        self.add(Dot([-3.95, 2.02, 0], radius=0.07, color=RED_))
        self.beat(say="the checker must report all five kinds", hold=0.4)
