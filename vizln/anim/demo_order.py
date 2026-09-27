import json
import os
from vanim import *

class DemoOrder(Clip):
    TITLE = "Tracing a Distributed Order"
    SUB = "Checkout -> Kafka -> Accounting & Fraud"

    def story(self):
        # 1. Load the stitched telemetry data
        trace_path = os.path.join(os.path.dirname(__file__), "..", "trace_data.json")
        try:
            with open(trace_path, "r") as f:
                events = json.load(f)
        except FileNotFoundError:
            # Fallback if the file isn't found locally during rendering checks
            events = []

        # 2. Build the Schematic Architecture
        # The checkout service
        chk = node(capsule, [-4, 1, 0], ["checkout"], BLUE_)
        p_chk = ports(chk.shape, right=(RIGHT, 0))

        # Kafka Queue
        kaf = node(box, [0, 1, 0], ["kafka", "orders topic"], GREEN_)
        p_kaf = ports(kaf.shape, left=(LEFT, 0), top_right=(RIGHT, 0.4), bot_right=(RIGHT, -0.4))

        # The Consumer Services
        acc = node(box, [4, 2.5, 0], ["accounting"], TEAL_)
        p_acc = ports(acc.shape, left=(LEFT, 0))

        frd = node(box, [4, -0.5, 0], ["fraud-detection"], PLUM_)
        p_frd = ports(frd.shape, left=(LEFT, 0))

        # Wire them together with Manhattan routing
        b = Bay(2.0, span=[-1, 3])
        w_chk_kaf = net(p_chk['right'], p_kaf['left'], color=DIM_)
        w_kaf_acc = net(p_kaf['top_right'], p_acc['left'], bay=b, lane=0, color=DIM_)
        w_kaf_frd = net(p_kaf['bot_right'], p_frd['left'], bay=b, lane=1, color=DIM_)

        # Group and display the layout
        g = VGroup(w_chk_kaf, w_kaf_acc, w_kaf_frd, chk, kaf, acc, frd)
        self.beat(FadeIn(g), say="A new order begins its journey")

        # 3. Animate the timeline based dynamically on the JSON data
        for e in events:
            svc = e["service"]
            t = e["type"]
            msg = e.get("message", e.get("name", ""))

            # Map the event to the correct visual action
            if svc == "checkout" and t == "span":
                if msg == "publish orders":
                    self.beat(*w_chk_kaf.light(BLUE_), say="Checkout publishes to Kafka")
                else:
                    self.beat(pulse(chk, BLUE_), say=f"Checkout begins: {msg}")
            
            elif svc == "checkout" and t == "log":
                self.beat(pulse(chk, WHITE), say=f"OpenSearch Log: {msg}")

            elif svc == "accounting" and t == "span":
                self.beat(*w_kaf_acc.light(TEAL_), say="Accounting consumes from Kafka")

            elif svc == "accounting" and t == "log":
                self.beat(pulse(acc, WHITE), say=f"OpenSearch Log: {msg}")

            elif svc == "fraud-detection" and t == "span":
                self.beat(*w_kaf_frd.light(PLUM_), say="Fraud consumes from Kafka")

            elif svc == "fraud-detection" and t == "log":
                self.beat(pulse(frd, WHITE), say=f"OpenSearch Log: {msg}")

        # Final rest state
        self.beat(say="The order is fully processed across 3 disjointed traces!")
