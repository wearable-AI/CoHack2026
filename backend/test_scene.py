from manim import *

class QuickTest(Scene):
    def construct(self):
        box_a = Rectangle(height=1.2, width=2.5, color=BLUE).shift(LEFT * 3)
        label_a = Text("Client", font_size=24).move_to(box_a)
        
        box_b = Rectangle(height=1.2, width=2.5, color=GREEN).shift(RIGHT * 3)
        label_b = Text("API Gateway", font_size=24).move_to(box_b)

        arrow = Arrow(start=box_a.get_right(), end=box_b.get_left(), buff=0.2)
        req_text = Text("GET /users", font_size=18).next_to(arrow, UP)

        self.play(Create(box_a), Write(label_a))
        self.play(GrowArrow(arrow), Write(req_text))
        self.play(Create(box_b), Write(label_b))
        self.wait(1)