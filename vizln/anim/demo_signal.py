from vanim import *
import json
import os

data_path = os.path.join(os.path.dirname(__file__), "data", "checkout_latency.json")
with open(data_path, "r") as f:
    trace_data = json.load(f)

# Lookup trace data by time (rounding to nearest integer second)
def get_trace_latency(t):
    idx = min(250, max(0, int(t)))
    return trace_data[idx]["latency_ms"]

def prediction(t):
    # Dotted line prediction showing the crash trajectory
    if t < 100:
        return get_trace_latency(t)
    return get_trace_latency(100) + (t - 100)**1.5

def safe_bound(t):
    return 50

class DemoSignal(Clip):
    TITLE = "Interpretable Temporal Signals"
    SUB = "Visualizing checkout service latency and anomaly detection"

    def story(self):
        clock = self.tracker(0)
        
        self.counter("checkout latency (ms)", lambda: f"{int(get_trace_latency(clock.get_value())):,}", [-3.0, 2.5, 0], color=WHITE)
        self.counter("threshold", lambda: "50", [2.0, 2.5, 0], color=GREEN_)

        pl = self.timeline(
            ["Network", "Database", "Compute"],
            t_max=250, w=11.0, h=4.0, where=DOWN * 0.5, step=50,
            plot_h=3.5, y_max=400, y_label="ms"
        )
        self.add(pl.playhead(clock))
        
        self.add(pl.live_span(0, 0, clock, cap=250, color=BLUE_, height=0.1))
        self.add(pl.live_span(1, 0, clock, cap=250, color=TEAL_, height=0.1))

        # The safe zone gap
        self.add(pl.live_gap(safe_bound, lambda t: 0, clock, color=GREEN_, opacity=0.15))
        
        # The predictive curve (red, drawn first so it's under the main curve)
        self.add(pl.live_curve(prediction, clock, color=RED_, width=2.0))
        
        # The actual latency curve from trace data
        self.add(pl.live_curve(get_trace_latency, clock, color=WHITE, width=4.0))

        self.sweep(clock, 80, 2.0, say="Checkout service is healthy. Latency within the 50ms safe bound.", color=GREEN_)
        
        self.sweep(clock, 110, 1.0, say="Latency begins to trend upwards...", color=AMBER_)
        
        alert = pl.cut(110, color=RED_, label="ANOMALY DETECTED")
        self.add(pl.at_time(alert, 110, clock, ramp=0.5))
        self.beat(say="Anomaly Detected: Latency crossed 50ms threshold.", color=RED_, hold=1.5)
        
        self.sweep(clock, 150, 2.0, say="AI predicts a critical crash if the trend continues.", color=RED_)
        
        self.sweep(clock, 155, 0.5)
        mitigate = pl.cut(150, color=BLUE_, label="Auto-Mitigation")
        self.add(pl.at_time(mitigate, 150, clock, ramp=0.5))
        self.beat(say="Auto-mitigation deployed. Restarting locked database connections.", color=BLUE_, hold=1.5)
        
        self.sweep(clock, 250, 3.0, say="Latency returns to normal. Disaster avoided.", color=GREEN_)
