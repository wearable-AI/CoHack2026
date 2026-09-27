from vanim import *

def ingested(t): return 100.0 * t
def dropped(t):
    if t <= 100: return 0.0
    if t <= 150: return 50.0 * (t - 100)
    return 2500.0
def processed(t):
    if t <= 150: return 50.0 * t
    if t <= 200: return 7500.0 + 200.0 * (t - 150)
    return 17500.0 + 100.0 * (t - 200)
def queued(t): return ingested(t) - processed(t) - dropped(t)

class DemoData(Clip):
    TITLE = "Data Transfer & Backpressure"
    SUB = "Visualizing queue saturation, dropped packets, and auto-scaling"

    def story(self):
        clock = self.tracker(0)
        
        # Counters
        c_ing = self.counter("ingested", lambda: f"{int(ingested(clock.get_value())):,}", [-3.5, 2.0, 0], color=BLUE_)
        c_q = self.counter("queue (5k)", lambda: f"{int(queued(clock.get_value())):,}", [0.0, 2.0, 0], color=AMBER_)
        c_drop = self.counter("dropped", lambda: f"{int(dropped(clock.get_value())):,}", [0.0, 0.8, 0], color=RED_)
        c_proc = self.counter("processed", lambda: f"{int(processed(clock.get_value())):,}", [3.5, 2.0, 0], color=GREEN_)

        # Timeline
        tl = self.timeline(
            ["Ingestion", "Queueing", "Auto-scaler", "Workers"],
            t_max=250, w=11.0, h=3.0, where=DOWN * 1.5, step=50
        )
        self.add(tl.playhead(clock))
        
        # Timeline spans
        self.add(tl.live_span(0, 0, clock, cap=250, color=BLUE_, height=0.2))
        
        # Queueing span
        q_span1 = tl.span(1, 0, 100, color=AMBER_, height=0.1)
        q_span2 = tl.span(1, 100, 150, color=RED_, height=0.25)
        q_span3 = tl.span(1, 150, 200, color=GREEN_, height=0.2)
        for s, t0 in [(q_span1, 0), (q_span2, 100), (q_span3, 150)]:
            self.add(tl.at_time(s, t0, clock))

        # Workers span
        w_span1 = tl.span(3, 0, 150, color=TEAL_, height=0.1)
        w_span2 = tl.span(3, 150, 250, color=TEAL_, height=0.3)
        self.add(tl.at_time(w_span1, 0, clock))
        self.add(tl.at_time(w_span2, 150, clock))

        # Action!
        self.sweep(clock, 50, 2.0, say="Traffic arrives. The single worker pod processes it slowly.", color=BLUE_)
        
        # Transfer from ingested -> queue, and queue -> processed
        a1 = self.transfer(c_ing.out_low, c_q.in_low, color=BLUE_)
        a2 = self.transfer(c_q.out_low, c_proc.in_low, color=GREEN_)
        self.play(Create(a1), Create(a2))
        self.sweep(clock, 95, 2.0, say="The queue starts filling up due to backpressure...", color=AMBER_)
        self.play(FadeOut(a1), FadeOut(a2))
        
        # Queue hits limit
        self.sweep(clock, 100, 1.0)
        self.beat(say="Queue hits its 5,000 capacity limit!", color=RED_, hold=1.0)
        
        a3 = self.transfer(c_ing.out_low, c_drop.in_low, color=RED_)
        self.play(Create(a3))
        self.sweep(clock, 145, 2.0, say="New requests are now being violently dropped!", color=RED_)
        self.play(FadeOut(a3))
        
        # Autoscaler
        self.sweep(clock, 150, 0.5)
        scale_evt = tl.cut(150, color=TEAL_, label="Scale to 4x")
        self.add(tl.at_time(scale_evt, 150, clock, ramp=0.5))
        self.beat(say="Auto-scaler detects the saturation and deploys 3 more pods.", color=TEAL_, hold=1.5)
        
        # Draining
        a4 = self.transfer(c_q.out_low, c_proc.in_low, color=GREEN_)
        self.play(Create(a4))
        self.sweep(clock, 195, 2.0, say="With 4x compute, the workers rapidly drain the queue.", color=GREEN_)
        self.play(FadeOut(a4))
        
        self.sweep(clock, 200, 0.5)
        self.beat(say="Queue is completely drained. System is stable.", color=GREEN_, hold=1.5)
        
        self.sweep(clock, 250, 2.0, say="Data transfer and backpressure, instantly visible.", color=WHITE)
