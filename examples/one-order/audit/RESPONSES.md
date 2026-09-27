# Responses to audit 01

One row per finding in `2026-09-26-audit-01.md`. The builder changed the files named here. The
auditor confirms each fix, and only then does the finding close.

| Finding | Response | Changed |
|---|---|---|
| A1 "has the order at 0.0 ms" was a literal, and the first seconds animated browsing | Fixed. The order is now the one top-level request whose subtree holds `demo.order.id` (1 of 7, 55 spans). Times start at that request. Checkout's time is the first tagged span: 3.9 ms. A new check requires exactly one request to hold the id | `vizln/flow/derive.py`, `flow.json`, `DERIVATION.md` section 0 |
| A2 "trace a4013e83 ends at the Kafka send" | Fixed. The caption is now "the consumers are not in trace a4013e83" | `clip.py` |
| A3 "in a new trace" | Fixed. The captions say "in a different trace". DERIVATION section 3 says the consumer traces were already open | `clip.py`, `derive.py` |
| A4 the closing line credits a join that the clip never shows | Fixed. Board 2 has a third fact: in 2 consumer traces, a log line names the order and carries that trace id. Two new checks assert it. The closing line is now "The span link and the order id make them one" | `derive.py`, `clip.py` |
| A5 accounting's store in checkout's colour | Fixed. Each store copy takes the colour of the trace that its calls belong to | `clip.py` |
| B1 three traces is a lower bound | Stated in DERIVATION "Limits". Follow-up: search the in-trace services too, and keep every answer | `derive.py` |
| B2 Cloud Logging measured in `textPayload` only | Stated in "Limits". Board 2 now says "3 lines name the order, none from checkout or frontend" | `derive.py`, `clip.py` |
| B3 cross-node clocks | Stated in "Limits" | `derive.py` |
| B4 the offset joins the consumers only | Fixed wording: "the two consumers read the same Kafka message, offset 1132" | `clip.py` |
| B5 hops that never flash | Stated in "Limits". The new scope also removed the sweep through the browsing requests | `derive.py` |
| B6 the earliest span is not a root | Fixed. Section 0 says the top-level requests name a parent that is not in the trace. The column is now "Earliest span" | `derive.py` |
| B7 two timing rules | Fixed. One rule for both consumers: the end of the receive span. fraud-detection now reads 77.8 ms, 2.9 ms after the publish | `derive.py` |
| C7 cylinder lip crosses the store labels | Fixed by a thinner lip (0.09) and the label moved down 0.05. Please measure again on the new render | `clip.py` |
| C7 six log entries at a 1970 timestamp | Fixed. OpenSearch stores 1970-01-01 when an SDK sends no event time. derive falls back to `observedTimestamp` and records `time_field` | `derive.py` |
| C7 captions outlive their event | Not changed | |
| C8 the checker never tests node labels | Recorded in the trap log. Not fixed in vanim yet. Until then, check node labels on rendered frames | `vizln/anim/HARNESS-NOTES.md` |
