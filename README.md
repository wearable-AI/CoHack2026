# CoHack2026

At a company with many small services, a new developer cannot see how one request moves
through the system. Our product shows it to them as a short animation, made from the
company's real data, inside their AI coding assistant.

## An everyday picture

Think of one online order as a parcel that passes through 12 hands. Each hand writes a note in
its own notebook, and the notebooks sit in 3 different offices. Nobody has the whole story of
the parcel. Our product collects the notes, puts them in order, and makes a 30-second film of
the parcel's journey.

## The setup

### A fake company in Google Cloud

The company is the [OpenTelemetry Demo](https://opentelemetry.io/docs/demo/), a free,
open-source online telescope shop. We did not write it. It has about 20 small services in 12
languages. A load generator (robot shoppers) buys things all day. It runs on Google Kubernetes
Engine, on 3 small VMs. `sandbox/README.md` explains how to start it, join it and stop it.

### Its three notebooks

The shop already records what happens, in 3 places:

| Place | What it holds |
|---|---|
| Jaeger | the list of calls that each request made (a trace) |
| OpenSearch | log lines from the services that log through OpenTelemetry, for example `checkout` |
| Google Cloud Logging | log lines from the services that print to the screen, for example `fraud-detection` |

### The problem, measured

One order is split across all three places:

```
checkout ─► cart, currency, shipping, payment, email     Jaeger: one trace
   │
   └─► Kafka "orders" ─┬─► accounting                     Jaeger: a new trace
                       └─► fraud-detection                Jaeger: a new trace

checkout logs "order placed"         ─► OpenSearch
the consumers log "orderId: ..."     ─► Cloud Logging
```

The trace stops at the queue (Kafka), and Jaeger's own service map shows no edge after it. No
single screen shows the whole order.

## What our product does

1. **Collect.** Read the three places for one order.
2. **Join.** Put the pieces in order, with the order number and the trace ids.
3. **Show.** Make a short animation of the journey with `vizln/`. Every number on screen comes
   from the real data.
4. **Where.** A developer asks their AI assistant "how does checkout work?", and the animation
   comes back.

## The demo story, about 3 minutes

1. "This is a real system: 20 services in Google Cloud." Show the shop and the 3 VMs.
2. "A new developer asks: how does an order work? Today's tools show a broken picture." Show
   Jaeger, where the order stops at Kafka.
3. "Our product shows the whole journey." Show the animation.
4. "Now we break something on purpose." Turn on the `paymentFailure` flag. "The product shows
   what broke, and where."

## Status

| Part | Status |
|---|---|
| Fake company in Google Cloud | done, running |
| Animation engine with 3 example clips (`vizln/`) | done |
| Proof of the problem: one order split across 3 places | done, measured |
| Collect and join (the stitcher) | not yet |
| An animation of a real order | not yet |
| The connection to the AI assistant | not yet |

## Where things are

| Folder | What it holds |
|---|---|
| `vizln/` | the animation engine, the method, and three example clips in `vizln/demo/` |
| `sandbox/` | scripts that run the fake company on GKE or on a laptop |
| `backend/` | the web backend, in progress |

## Words

- **Microservices**: many small programs, and each one does one job.
- **Trace**: the list of calls that one request made.
- **Log**: a line of text that a program writes.
- **Kafka**: a queue. One service drops a message, and other services pick it up later.
