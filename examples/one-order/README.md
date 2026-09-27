# One order, three traces

One real order from the fake company, followed through 16 services and stores in 8
languages. Jaeger shows it as three unconnected traces. Two facts in the runtime data join
them: the consumers' span link back to checkout's Kafka span, and the Kafka offset that both
consumers read.

**Runtime only.** No source code was read. Every service, edge, time, language and count
comes from what the running system recorded.

## How the clip was made

```
the running system ──► capture ──► evidence/ ──► derive ──► flow.json ──► clip.py ──► OneOrder.mp4
   Jaeger               asks and     saved         joins and     the only      draws
   OpenSearch           saves        unedited      checks        input to      only what
   Cloud Logging                                                 the clip      flow.json says
```

| File | What it is |
|---|---|
| `capture.json` | every question the agent asked, the exact request, the answer count, and a checksum of each kept answer |
| `evidence/` | the raw answers, unedited, numbered by question |
| `DERIVATION.md` | how the evidence became `flow.json`, step by step, with every join check |
| `flow.json` | nodes, edges, hops, log lines and facts. The clip reads nothing else |
| `clip.py` | the vanim clip |
| `OneOrder.mp4`, `OneOrder.gif` | the result |

## Repeat it

From the repo root:

```sh
sandbox/capture.sh gke examples/one-order <order-id>    # or leave out the id for the latest order
python3 vizln/flow/derive.py examples/one-order          # stops with an error if a join fails
vizln/anim/check.sh  examples/one-order/clip.py
vizln/anim/render.sh examples/one-order/clip.py --q qh --gif
```

## Two things the checks caught

- **A log line hid the order id in a structured field.** OpenSearch found `accounting`'s line
  `Order details: {@OrderResult}.` by the order id, but the id is not in its text. It is in the
  field `@OrderResult`. The first version of the check looked only at the text and failed.
- **A consumer seemed to receive the order before it was sent.** `accounting`'s `receive
  orders` span starts 45.5 ms before checkout's publish, because it includes the wait for the
  next message. The message is in hand when the span ends, 2.6 ms after the publish. The
  derive step now uses the span's end for a `receive` span, and a causality check stops the
  build if any consumer has the order before the publish.
