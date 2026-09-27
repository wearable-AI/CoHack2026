# How flow.json was made

Order `7c8c01c4-ba22-11f1-903b-b295684fc89c`, captured 2026-09-27T03:21:56+00:00 from the `gke` cluster.
No source code was read. Every service, edge, time and count below comes from the runtime
data in `evidence/`, which the capture step saved unedited.

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

- PASS: the checkout trace carries the order id. demo.order.id=7c8c01c4-ba22-11f1-903b-b295684fc89c on trace a4013e83 (`evidence/02-jaeger-trace-a4013e836e1b.json`)
- PASS: checkout published the order to a queue. 1 producer span(s) (`evidence/02-jaeger-trace-a4013e836e1b.json`)
- PASS: the accounting trace links back to checkout's queue span. FOLLOWS_FROM 68e95041 = publish span 68e95041 (`evidence/14-jaeger-trace-d02a3f06dec1.json`)
- PASS: accounting has the order only after checkout published it. accounting at 178.1 ms, publish at 175.5 ms (`evidence/14-jaeger-trace-d02a3f06dec1.json`)
- PASS: the fraud-detection trace links back to checkout's queue span. FOLLOWS_FROM 68e95041 = publish span 68e95041 (`evidence/15-jaeger-trace-0138fcfe9e56.json`)
- PASS: fraud-detection has the order only after checkout published it. fraud-detection at 178.7 ms, publish at 175.5 ms (`evidence/15-jaeger-trace-0138fcfe9e56.json`)
- PASS: the consumers read the same Kafka message. accounting offset 1132, fraud-detection offset 1132 (`consumer spans`)
- PASS: each hop comes from a different span. 58 hops, 58 distinct spans (`all traces`)
- PASS: every opensearch line found by order id really names it. 5 of 5 (`evidence/16-opensearch-by-order.json`)
- PASS: every cloud-logging line found by order id really names it. 3 of 3 (`evidence/18-cloudlogging-by-order.json`)
- PASS: every OpenSearch line with a trace id belongs to one of the order's traces. 45 lines, trace ids in ['0138fcfe', 'a4013e83', 'd02a3f06'] (`opensearch files`)

## 3. The three traces

Times are milliseconds after the checkout trace's first span. A consumer's time is the moment
it had the order, by the rule in section 6. Its root span can open much earlier: it waits.

| Trace | Role | Spans | Has the order at | Root span, opened at | Services |
|---|---|---|---|---|---|
| `a4013e83` | checkout | 118 | 0.0 ms | `GET`, 0.0 ms | cart, checkout, currency, email, flagd, frontend, frontend-proxy, payment, product-catalog, quote, shipping |
| `d02a3f06` | accounting | 3 | 178.1 ms | `order-consumed`, -17426.3 ms | accounting |
| `0138fcfe` | fraud-detection | 2 | 178.7 ms | `receive orders`, 128.4 ms | fraud-detection |

## 4. What was kept, and what was collapsed

123 spans became 58 hops between 16 nodes. A hop is a call that crosses from one service to another, a write to a store, the queue publish, or a queue read. 65 spans stayed inside one service and are not drawn.

## 5. Where the order's log lines are

| Store | Lines that name the order | Services |
|---|---|---|
| opensearch | 5 | accounting, checkout, email, fraud-detection, frontend |
| cloud-logging | 3 | accounting, email, fraud-detection |

| ms | Store | Service | Field that names the order | Text |
|---|---|---|---|---|
| 159.5 | opensearch | checkout | `attributes.demo.order.id` | order placed |
| 174.0 | opensearch | email | `attributes.demo.order.id` | Order confirmation email sent |
| 174.3 | cloud-logging | email | `textPayload` | Order confirmation email sent for order 7c8c01c4-ba22-11f1-903b-b29568 |
| 178.2 | opensearch | accounting | `attributes.@OrderResult` | Order details: {@OrderResult}. |
| 179.0 | opensearch | fraud-detection | `body` | Consumed record with orderId: 7c8c01c4-ba22-11f1-903b-b295684fc89c, an |
| 179.6 | cloud-logging | accounting | `textPayload` | Order details: { "orderId": "7c8c01c4-ba22-11f1-903b-b295684fc89c", "s |
| 179.6 | cloud-logging | fraud-detection | `textPayload` | 2026-09-27 03:21:10 - fraud-detection - Consumed record with orderId:  |
| 186.7 | opensearch | frontend | `attributes.demo.order.id` | Order placed successfully |

## 6. The queue hop

- 175.5 ms: checkout → kafka · orders (`publish orders`, trace `a4013e83`).
- 178.1 ms: kafka · orders → accounting (`receive orders`, trace `d02a3f06`). Span 130.0 to 178.1 ms. Rule: receive span: the message is in hand when the span ends.
- 178.7 ms: kafka · orders → fraud-detection (`process orders`, trace `0138fcfe`). Span 178.7 to 179.5 ms. Rule: process span: it starts after the message arrived.

## 7. Every hop, in time order

| Hop | ms | From | To | Kind | Trace |
|---|---|---|---|---|---|
| h01 | 0.7 | frontend-proxy | frontend | call | `a4013e83` |
| h02 | 3.9 | frontend | product-catalog | call | `a4013e83` |
| h03 | 5.8 | product-catalog | postgresql · astronomy-db | store | `a4013e83` |
| h04 | 24.7 | frontend-proxy | frontend | call | `a4013e83` |
| h05 | 28.0 | frontend | cart | call | `a4013e83` |
| h06 | 28.1 | cart | redis · valkey-cart | store | `a4013e83` |
| h07 | 29.1 | cart | redis · valkey-cart | store | `a4013e83` |
| h08 | 29.9 | cart | redis · valkey-cart | store | `a4013e83` |
| h09 | 31.2 | frontend | cart | call | `a4013e83` |
| h10 | 31.3 | cart | redis · valkey-cart | store | `a4013e83` |
| h11 | 39.7 | frontend-proxy | frontend | call | `a4013e83` |
| h12 | 44.8 | frontend | product-catalog | call | `a4013e83` |
| h13 | 48.8 | product-catalog | postgresql · astronomy-db | store | `a4013e83` |
| h14 | 58.7 | frontend-proxy | frontend | call | `a4013e83` |
| h15 | 61.4 | frontend | cart | call | `a4013e83` |
| h16 | 61.5 | cart | redis · valkey-cart | store | `a4013e83` |
| h17 | 62.4 | cart | redis · valkey-cart | store | `a4013e83` |
| h18 | 63.7 | cart | redis · valkey-cart | store | `a4013e83` |
| h19 | 66.0 | frontend | cart | call | `a4013e83` |
| h20 | 66.1 | cart | redis · valkey-cart | store | `a4013e83` |
| h21 | 73.7 | frontend-proxy | frontend | call | `a4013e83` |
| h22 | 76.5 | frontend | product-catalog | call | `a4013e83` |
| h23 | 78.4 | product-catalog | postgresql · astronomy-db | store | `a4013e83` |
| h24 | 87.7 | frontend-proxy | frontend | call | `a4013e83` |
| h25 | 90.8 | frontend | cart | call | `a4013e83` |
| h26 | 91.0 | cart | redis · valkey-cart | store | `a4013e83` |
| h27 | 91.9 | cart | redis · valkey-cart | store | `a4013e83` |
| h28 | 92.3 | cart | redis · valkey-cart | store | `a4013e83` |
| h29 | 93.6 | frontend | cart | call | `a4013e83` |
| h30 | 93.7 | cart | redis · valkey-cart | store | `a4013e83` |
| h31 | 101.7 | frontend-proxy | frontend | call | `a4013e83` |
| h32 | 104.5 | frontend | checkout | call | `a4013e83` |
| h33 | 106.6 | checkout | cart | call | `a4013e83` |
| h34 | 106.8 | cart | redis · valkey-cart | store | `a4013e83` |
| h35 | 110.7 | checkout | product-catalog | call | `a4013e83` |
| h36 | 114.2 | product-catalog | postgresql · astronomy-db | store | `a4013e83` |
| h37 | 119.8 | checkout | currency | call | `a4013e83` |
| h38 | 121.8 | checkout | product-catalog | call | `a4013e83` |
| h39 | 124.2 | product-catalog | postgresql · astronomy-db | store | `a4013e83` |
| h40 | 129.1 | checkout | currency | call | `a4013e83` |
| h41 | 134.8 | checkout | shipping | call | `a4013e83` |
| h42 | 140.0 | shipping | quote | call | `a4013e83` |
| h43 | 145.7 | checkout | currency | call | `a4013e83` |
| h44 | 148.7 | checkout | payment | call | `a4013e83` |
| h45 | 153.9 | checkout | shipping | call | `a4013e83` |
| h46 | 155.1 | checkout | cart | call | `a4013e83` |
| h47 | 156.1 | cart | flagd | call | `a4013e83` |
| h48 | 157.7 | cart | redis · valkey-cart | store | `a4013e83` |
| h49 | 158.4 | cart | redis · valkey-cart | store | `a4013e83` |
| h50 | 162.8 | checkout | email | call | `a4013e83` |
| h51 | 175.5 | checkout | kafka · orders | publish | `a4013e83` |
| h52 | 178.1 | kafka · orders | accounting | consume | `d02a3f06` |
| h53 | 178.7 | kafka · orders | fraud-detection | consume | `0138fcfe` |
| h54 | 179.6 | accounting | postgresql · astronomy-db | store | `d02a3f06` |
| h55 | 179.7 | frontend | product-catalog | call | `a4013e83` |
| h56 | 180.0 | frontend | product-catalog | call | `a4013e83` |
| h57 | 183.1 | product-catalog | postgresql · astronomy-db | store | `a4013e83` |
| h58 | 183.6 | product-catalog | postgresql · astronomy-db | store | `a4013e83` |
