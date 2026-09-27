# Audit Report: DemoSignal

- Clip file and scene: `vizln/anim/demo_signal.py`, Scene `DemoSignal`
- Study directory: `vizln/anim/audit/`
- The one sentence the clip must land: "Time-series interpretation can predict system crashes and highlight anomalies."

## 1. The mobject census
- 2 `counter`
- 1 `timeline` with `playhead`
- 2 `live_span`
- 1 `live_gap`
- 2 `live_curve`
- 2 `cut`
- 8 `sweep`/`beat` actions

## 2. Frames, sampled and read
- **t=80**: The plot shows normal sinusoidal latency bouncing around 20ms. The threshold counter reads "50". 
- **t=110**: The primary latency curve exits the green `live_gap` safe zone. A red cut appears with "ANOMALY DETECTED".
- **t=150**: The primary latency curve peaks around ~370ms. A second red prediction curve diverges. The text states "Auto-mitigation deployed."

## 3. Every figure against its source
**CRITICAL FAULT:** No figure is derived from source evidence.
- The latency calculation is a pure mathematical mock (`math.sin(t * 1.3) * 3 + math.cos(t * 2.7) * 2`).
- The exponential spike is a typed literal equation: `base + (t - 100)**1.5`.
- The threshold is hardcoded: `lambda: "50"`.
- There is no `facts.json`, `data.json`, or `trace.json` backing any of these numbers. They are entirely fictional.

## 4. Instance or class
The frames depict a completely generalized, theoretical class of incident. It does not reflect a specific run.

## 5. Claims the clip draws that nothing measured
- **Claim:** "Auto-mitigation deployed. Restarting locked database connections." at `t=150`.
- **Measurement:** Nothing measured this event. The timeline cut and mitigation drop are perfectly timed to a mathematical constant, with no trace event proving that a database lock occurred or was restarted.

## 6. Render cost
The render is extremely fast (10 animation steps) and generates no warnings about object caching, indicating a very low screen complexity.

## Auditor Conclusion
The visual design is structurally sound and effectively uses `live_curve`, but it fails the core authenticity requirement of the visualizer framework. To be precise and professional, the mathematical mocks must be stripped out and replaced by a real, parsable trace file (e.g., `trace.json` or `metrics.csv`) containing actual latency timestamps and anomaly events.
