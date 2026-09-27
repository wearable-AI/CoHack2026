# How flow.json was made

Order `7c8c01c4-ba22-11f1-903b-b295684fc89c`, captured 2026-09-27T03:21:56+00:00 from the `gke` cluster.
No source code was read. Every service, edge, time and count below comes from the runtime
data in `evidence/`, which the capture step saved unedited.

## 0. What counts as the order

The checkout trace holds 7 top-level requests: the shopper's whole session shares one trace. The order is the one request whose subtree holds `demo.order.id`: `frontend-proxy POST`, 55 spans, which began 100.6 ms into the trace. The other 63 spans are browsing and cart requests, and are left out.
The top-level requests all name a parent that is not in the trace: the shopper's own span
was never exported, so the session's origin is not in the evidence.
All times below are milliseconds after that request began.

## Limits

- **Three traces is a lower bound.** The consumer search asked only the services that are not
  in the checkout trace, for 300 s after the order, up to 500 traces each, and it kept only the
  counts of those answers. A linked trace in a service inside the checkout trace was not sought.
- **Cloud Logging was searched in `textPayload` only.** A line with the id in `jsonPayload` would
  not match. So "none from checkout" holds for text lines.
- **Cross-node times include clock offset.** Services on different nodes stamp their own spans,
  and nothing here measures the offset between node clocks.
- **The clip lights each edge once, at its first hop.** Every hop is listed in section 7.

## 1. What the agent asked, and what came back

| # | Store | Question | Answer | Kept as |
|---|---|---|---|---|
| 1 | jaeger | checkout traces tagged demo.order.id=7c8c01c4-ba22-11f1-903b-b295684fc89c | 1 | `evidence/01-jaeger-search-checkout.json` |
| 2 | jaeger | the full trace a4013e836e1b52a0dac860b7b701f713 | 118 | `evidence/02-jaeger-trace-a4013e836e1b.json` |
| 3 | jaeger | the services Jaeger has seen | 21 | count only |
| 4 | jaeger | accounting traces in the 300s after the order that link to a4013e836e1b | 1 | count only |
| 5 | jaeger | ad traces in the 300s after the order that link to a4013e836e1b | 0 | count only |
| 6 | jaeger | agent traces in the 300s after the order that link to a4013e836e1b | 0 | count only |
| 7 | jaeger | chatbot traces in the 300s after the order that link to a4013e836e1b | 0 | count only |
| 8 | jaeger | fraud-detection traces in the 300s after the order that link to a4013e836e1b | 1 | count only |
| 9 | jaeger | frontend-web traces in the 300s after the order that link to a4013e836e1b | 0 | count only |
| 10 | jaeger | image-provider traces in the 300s after the order that link to a4013e836e1b | 0 | count only |
| 11 | jaeger | jaeger traces in the 300s after the order that link to a4013e836e1b | 0 | count only |
| 12 | jaeger | mcp traces in the 300s after the order that link to a4013e836e1b | 0 | count only |
| 13 | jaeger | recommendation traces in the 300s after the order that link to a4013e836e1b | 0 | count only |
| 14 | jaeger | the full accounting trace d02a3f06dec1b9b456e5ce05f392fd13 | 3 | `evidence/14-jaeger-trace-d02a3f06dec1.json` |
| 15 | jaeger | the full fraud-detection trace 0138fcfe9e569ac680e9d74c9d008348 | 2 | `evidence/15-jaeger-trace-0138fcfe9e56.json` |
| 16 | opensearch | log lines that contain the order id | 5 | `evidence/16-opensearch-by-order.json` |
| 17 | opensearch | log lines with one of the trace ids | 45 | `evidence/17-opensearch-by-trace.json` |
| 18 | cloud-logging | container stdout lines that contain the order id | 3 | `evidence/18-cloudlogging-by-order.json` |

## 2. How the pieces were joined

- PASS: exactly one top-level request in the trace holds the order id. 1 of 7 top-level requests (`evidence/02-jaeger-trace-a4013e836e1b.json`)
- PASS: the checkout trace carries the order id. demo.order.id=7c8c01c4-ba22-11f1-903b-b295684fc89c on trace a4013e83 (`evidence/02-jaeger-trace-a4013e836e1b.json`)
- PASS: checkout published the order to a queue. 1 producer span(s) (`evidence/02-jaeger-trace-a4013e836e1b.json`)
- PASS: the accounting trace links back to checkout's queue span. FOLLOWS_FROM 68e95041 = publish span 68e95041 (`evidence/14-jaeger-trace-d02a3f06dec1.json`)
- PASS: accounting has the order only after checkout published it. accounting at 77.5 ms, publish at 74.9 ms (`evidence/14-jaeger-trace-d02a3f06dec1.json`)
- PASS: the fraud-detection trace links back to checkout's queue span. FOLLOWS_FROM 68e95041 = publish span 68e95041 (`evidence/15-jaeger-trace-0138fcfe9e56.json`)
- PASS: fraud-detection has the order only after checkout published it. fraud-detection at 77.8 ms, publish at 74.9 ms (`evidence/15-jaeger-trace-0138fcfe9e56.json`)
- PASS: the consumers read the same Kafka message. accounting offset 1132, fraud-detection offset 1132 (`consumer spans`)
- PASS: each hop comes from a different span. 28 hops, 28 distinct spans (`all traces`)
- PASS: every opensearch line found by order id really names it. 5 of 5 (`evidence/16-opensearch-by-order.json`)
- PASS: every cloud-logging line found by order id really names it. 3 of 3 (`evidence/18-cloudlogging-by-order.json`)
- PASS: every OpenSearch line with a trace id belongs to one of the order's traces. 45 lines, trace ids in ['0138fcfe', 'a4013e83', 'd02a3f06'] (`opensearch files`)
- PASS: the order id also reaches the accounting trace: a log line names the order and carries that trace id. 1 line(s), store opensearch (`opensearch files`)
- PASS: the order id also reaches the fraud-detection trace: a log line names the order and carries that trace id. 1 line(s), store opensearch (`opensearch files`)

## 3. The three traces

Checkout's time is the first span tagged with the order id. A consumer's time is the moment
it had the order, by the rule in section 6. A consumer's root span opened before that: it waits.
So the consumers' traces were already open. The order entered them, it did not start them.

| Trace | Role | Spans (in the order's scope) | Has the order at | Earliest span, opened at | Services |
|---|---|---|---|---|---|
| `a4013e83` | checkout | 118 (55) | 3.9 ms | `GET`, -100.6 ms | cart, checkout, currency, email, flagd, frontend, frontend-proxy, payment, product-catalog, quote, shipping |
| `d02a3f06` | accounting | 3 (3) | 77.5 ms | `order-consumed`, -17526.9 ms | accounting |
| `0138fcfe` | fraud-detection | 2 (2) | 77.8 ms | `receive orders`, 27.8 ms | fraud-detection |

## 4. What was kept, and what was collapsed

60 spans in the order's scope became 28 hops between 16 nodes. A hop is a call that crosses from one service to another, a write to a store, the queue publish, or a queue read. 32 spans stayed inside one service and are not drawn.

## 5. Where the order's log lines are

| Store | Lines that name the order | Services |
|---|---|---|
| opensearch | 5 | accounting, checkout, email, fraud-detection, frontend |
| cloud-logging | 3 | accounting, email, fraud-detection |

| ms | Store | Service | Field that names the order | Text |
|---|---|---|---|---|
| 58.9 | opensearch | checkout | `attributes.demo.order.id` | order placed |
| 73.3 | opensearch | email | `attributes.demo.order.id` | Order confirmation email sent |
| 73.7 | cloud-logging | email | `textPayload` | Order confirmation email sent for order 7c8c01c4-ba22-11f1-903b-b29568 |
| 77.5 | opensearch | accounting | `attributes.@OrderResult` | Order details: {@OrderResult}. |
| 78.4 | opensearch | fraud-detection | `body` | Consumed record with orderId: 7c8c01c4-ba22-11f1-903b-b295684fc89c, an |
| 79.0 | cloud-logging | accounting | `textPayload` | Order details: { "orderId": "7c8c01c4-ba22-11f1-903b-b295684fc89c", "s |
| 79.0 | cloud-logging | fraud-detection | `textPayload` | 2026-09-27 03:21:10 - fraud-detection - Consumed record with orderId:  |
| 86.1 | opensearch | frontend | `attributes.demo.order.id` | Order placed successfully |

## 6. The queue hop

- 74.9 ms: checkout → kafka · orders (`publish orders`, trace `a4013e83`).
- 77.5 ms: kafka · orders → accounting (`receive orders`, trace `d02a3f06`). Span 29.3 to 77.5 ms. Rule: the receive span ends: the message is in hand.
- 77.8 ms: kafka · orders → fraud-detection (`process orders`, trace `0138fcfe`). Span 78.1 to 78.8 ms. Rule: its parent receive span ends: the message is in hand, before `process orders` starts.

## 7. Every hop, in time order

| Hop | ms | From | To | Kind | Trace |
|---|---|---|---|---|---|
| h01 | 1.1 | frontend-proxy | frontend | call | `a4013e83` |
| h02 | 3.9 | frontend | checkout | call | `a4013e83` |
| h03 | 6.0 | checkout | cart | call | `a4013e83` |
| h04 | 6.2 | cart | redis · valkey-cart | store | `a4013e83` |
| h05 | 10.1 | checkout | product-catalog | call | `a4013e83` |
| h06 | 13.6 | product-catalog | postgresql · astronomy-db | store | `a4013e83` |
| h07 | 19.2 | checkout | currency | call | `a4013e83` |
| h08 | 21.2 | checkout | product-catalog | call | `a4013e83` |
| h09 | 23.5 | product-catalog | postgresql · astronomy-db | store | `a4013e83` |
| h10 | 28.5 | checkout | currency | call | `a4013e83` |
| h11 | 34.2 | checkout | shipping | call | `a4013e83` |
| h12 | 39.4 | shipping | quote | call | `a4013e83` |
| h13 | 45.1 | checkout | currency | call | `a4013e83` |
| h14 | 48.1 | checkout | payment | call | `a4013e83` |
| h15 | 53.3 | checkout | shipping | call | `a4013e83` |
| h16 | 54.5 | checkout | cart | call | `a4013e83` |
| h17 | 55.5 | cart | flagd | call | `a4013e83` |
| h18 | 57.1 | cart | redis · valkey-cart | store | `a4013e83` |
| h19 | 57.8 | cart | redis · valkey-cart | store | `a4013e83` |
| h20 | 62.2 | checkout | email | call | `a4013e83` |
| h21 | 74.9 | checkout | kafka · orders | publish | `a4013e83` |
| h22 | 77.5 | kafka · orders | accounting | consume | `d02a3f06` |
| h23 | 77.8 | kafka · orders | fraud-detection | consume | `0138fcfe` |
| h24 | 79.0 | frontend | product-catalog | call | `a4013e83` |
| h25 | 79.0 | accounting | postgresql · astronomy-db | store | `d02a3f06` |
| h26 | 79.4 | frontend | product-catalog | call | `a4013e83` |
| h27 | 82.4 | product-catalog | postgresql · astronomy-db | store | `a4013e83` |
| h28 | 83.0 | product-catalog | postgresql · astronomy-db | store | `a4013e83` |
