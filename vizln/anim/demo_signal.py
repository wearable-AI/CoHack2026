from vanim import *
import json
import os

data_path = os.path.join(os.path.dirname(__file__), "data", "checkout_latency.json")
with open(data_path, "r") as f:
    trace_data = json.load(f)

# Analyze the trace data dynamically to find the anomaly
anomaly_detect = None
anomaly_peak = None
max_lat = 0

for point in trace_data:
    t = point["t"]
    lat = point["latency_ms"]
    if lat > max_lat:
        max_lat = lat
        anomaly_peak = t
    if lat > 50 and anomaly_detect is None:
        anomaly_detect = t

# We use 10 seconds before detection as the baseline trend start
anomaly_start = max(0, anomaly_detect - 10) if anomaly_detect else 0

# Lookup trace data by time (rounding to nearest integer second)
def get_trace_latency(t):
    idx = min(len(trace_data)-1, max(0, int(t)))
    return trace_data[idx]["latency_ms"]

def prediction(t):
    # The prediction algorithm actually calculates the trend from the raw data
    if anomaly_detect is None or t <= anomaly_detect:
        return get_trace_latency(t)
        
    # Measure the slope of the anomaly during the detection window
    latency_at_start = get_trace_latency(anomaly_start)
    latency_at_detect = get_trace_latency(anomaly_detect)
    trend_slope = (latency_at_detect - latency_at_start) / float(anomaly_detect - anomaly_start)
    
    # Project the trend forward aggressively (simulating a cascading failure)
    return latency_at_detect + trend_slope * (t - anomaly_detect) * 1.5

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

        # Dynamically place the story beats based on the detected data points
        safe_time = anomaly_start - 20 if anomaly_start > 20 else 20
        self.sweep(clock, safe_time, 2.0, say="Checkout service is healthy. Latency within the 50ms safe bound.", color=GREEN_)
        
        self.sweep(clock, anomaly_detect, 1.0, say="Latency begins to trend upwards...", color=AMBER_)
        
        alert = pl.cut(anomaly_detect, color=RED_, label="ANOMALY DETECTED")
        self.add(pl.at_time(alert, anomaly_detect, clock, ramp=0.5))
        self.beat(say=f"Anomaly Detected: Latency crossed 50ms threshold at t={anomaly_detect}s.", color=RED_, hold=1.5)
        
        self.sweep(clock, anomaly_peak, 2.0, say="AI predicts a critical crash if the trend continues.", color=RED_)
        
        self.sweep(clock, anomaly_peak + 5, 0.5)
        mitigate = pl.cut(anomaly_peak, color=BLUE_, label="Auto-Mitigation")
        self.add(pl.at_time(mitigate, anomaly_peak, clock, ramp=0.5))
        self.beat(say=f"Auto-mitigation deployed at t={anomaly_peak}s. Restarting locked database connections.", color=BLUE_, hold=1.5)
        
        self.sweep(clock, 250, 3.0, say="Latency returns to normal. Disaster avoided.", color=GREEN_)
