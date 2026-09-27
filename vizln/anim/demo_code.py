from vanim import *

SRC = '''func getRate(req *Cart) (*Rate, error) {
    for i := 1; i <= 3; i++ {
        rate, err := Quote(req)
        if err == nil { return rate, nil }
        
        log.Warnf("Quote failed: %v", err)
        time.Sleep(backoff(i))
    }
    
    return &Rate{Price: 9.99}, nil // Fallback
}'''

class DemoCode(Clip):
    TITLE = "Resilience Patterns: Circuit Breakers & Retries"
    SUB = "Syncing code execution, architecture, and timelines in real-time"

    def story(self):
        # 1. Code Panel (Top Left)
        panel, lines = self.code(SRC, "go", at=[-2.5, 1.2, 0], w=8.5, h=4.6)
        
        # 2. Architecture Chain (Top Right)
        flow, boxes = self.chain(
            ["Checkout", "Shipping", "Quote"],
            colours=[BLUE_, TEAL_, RED_],
            where=RIGHT * 3.5 + UP * 1.5, w=4.0, h=1.0,
            caption="Microservice Architecture",
        )
        
        # 3. Distributed Trace Timeline (Bottom)
        clock = self.tracker(0)
        tl = self.timeline(
            ["Checkout", "Shipping", "Quote"],
            t_max=12, w=10.0, h=2.5, where=DOWN * 1.8, step=2
        )
        self.add(tl.playhead(clock))

        self.beat(say="When a critical service goes down, how does our code react?", hold=1.0)
        
        # Checkout starts
        span_chk = tl.live_span(0, 0, clock, cap=11, color=BLUE_)
        self.add(span_chk)
        self.sweep(clock, 1, 1.0)

        # The Retry Loop
        for attempt, t_start in enumerate([1, 4, 7]):
            # Enter loop
            self.beat(self.mark(lines[1]), say=f"Attempt {attempt+1}/3: Entering the retry loop.")
            
            # Shipping calls Quote
            self.beat(self.mark(lines[2]), Indicate(boxes[1], color=TEAL_), say="Shipping calls the Quote service...")
            span_shp = tl.live_span(1, t_start, clock, cap=t_start+1, color=TEAL_)
            self.add(span_shp)
            self.sweep(clock, t_start+1, 0.8)
            
            # Quote fails
            self.beat(self.mark(lines[3]), Indicate(boxes[2], color=RED_), say="The Quote service is dead! Returning an error.", color=RED_)
            fail_cut = tl.cut(t_start+1, color=RED_, label="503 Down")
            self.add(tl.at_time(fail_cut, t_start+1, clock, ramp=0.2))
            
            # Log and sleep
            self.beat(self.mark(lines[5]), say="We catch the error and log a warning.")
            self.beat(self.mark(lines[6]), say="Applying exponential backoff sleep before retrying.")
            self.sweep(clock, t_start+3, 1.0)

        # Circuit Breaker Tripped!
        self.beat(self.mark(lines[9]), say="Max retries reached! Returning a default $9.99 flat rate to save the checkout!", color=GREEN_, hold=1.0)
        
        self.sweep(clock, 11, 1.0)
        self.beat(self.unmark(), say="We instantly proved the resilience pattern works, without reading a single log.")
