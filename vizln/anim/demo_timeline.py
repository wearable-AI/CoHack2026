from vanim import *

class DemoTimeline(Clip):
    TITLE = "Debugging Cascading Failures"
    SUB = "Why did checkout fail? Tracing the root cause with timelines"

    def story(self):
        clock = self.tracker(0)
        
        # Build the timeline with three service lanes
        tl = self.timeline(
            ["checkout", "shipping", "quote (PHP)"],
            t_max=10, w=10.0, h=4.0, where=DOWN * 0.5, step=2
        )
        
        # Attach the playhead that scans across time
        self.add(tl.playhead(clock))
        
        # 1. Checkout starts processing an order
        span_chk = tl.live_span(0, 1, clock, cap=8, color=BLUE_)
        self.add(span_chk)
        self.sweep(clock, 2, 1.5, say="Checkout receives an order request")
        
        # 2. Checkout calls Shipping
        span_shp = tl.live_span(1, 2, clock, cap=7, color=TEAL_)
        self.add(span_shp)
        self.sweep(clock, 4, 1.5, say="Checkout calls the Shipping service for a rate")

        # 3. Shipping calls Quote, but it's down!
        span_q = tl.live_span(2, 4, clock, cap=4.5, color=RED_)
        self.add(span_q)
        self.sweep(clock, 4.5, 1.0, say="Shipping asks Quote, but Quote has 0 running pods")
        
        # Mark the failure abruptly
        fail_cut = tl.cut(4.5, color=RED_, label="Connection Refused")
        self.play(tl.blink(clock, 4.5, color=RED_))
        self.add(tl.at_time(fail_cut, 4.5, clock, ramp=0.5))
        self.wait(1.0)
        
        # 4. Error bubbles up
        err_window = tl.window(4.5, 7, color=RED_, label="HTTP 500 Bubbles Up", opacity=0.2)
        self.add(tl.at_time(err_window, 4.5, clock, ramp=1.0))
        self.sweep(clock, 7, 2.0, say="Shipping catches the error and returns 500 to Checkout")

        # 5. Checkout logs the error blaming shipping
        log_tick = tl.live_step(0, [7], clock, color=AMBER_)
        self.add(log_tick)
        self.play(tl.blink(clock, 7, color=AMBER_))
        self.sweep(clock, 8, 1.5, say="Checkout logs: 'Shipping failure'. But Timeline proves Quote is the root cause!")
        
        # Rest state
        self.sweep(clock, 10, 1.5, say="Visual traces prevent developers from chasing the wrong service.")
