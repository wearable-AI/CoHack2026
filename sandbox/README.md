# sandbox: a fake company to demo against

A complete fictional company with real Kubernetes, real traffic, real logs and traces, a
GitHub org of service repos, and incidents that you can start with one switch.

The company is the [OpenTelemetry Demo](https://opentelemetry.io/docs/demo/), "Astronomy
Shop", release `3.1.0` (chart `0.42.1`), Apache 2.0. We did not write it. It has about 20
services in 12 languages, Kafka between `checkout` and its two consumers, PostgreSQL, Valkey,
a Locust load generator, and 17 failure flags.

## Safety rules the scripts enforce

- **Own kubeconfig.** Every script uses `sandbox/.kubeconfig`, so no other cluster is visible
  to it. Every `kubectl` and `helm` call also names its context.
- **Own gcloud configuration.** The GKE scripts use the `cohack` configuration and refuse to
  run unless its account equals `GCP_ACCOUNT` in `sandbox/.env.local`. Use a personal Google
  account, never an employer's account, project or billing.
- **You publish.** `fake-org.sh publish` pushes public repos to GitHub, so you run it.

## Local cluster

Needs `colima`, `kind`, `helm` and `kubectl`. Uses a colima profile named `cohack` with
6 CPUs, 12 GiB and 60 GiB of disk.

```sh
sandbox/local-up.sh              # first run pulls about 20 images
sandbox/forward.sh local         # then open http://localhost:8080
sandbox/local-down.sh --stop     # delete the cluster and stop the VM
```

## GKE cluster

### 1. Find out if you have a personal account with billing

```sh
gcloud config configurations create cohack --no-activate
gcloud auth login --configuration=cohack          # pick your personal account in the browser
gcloud billing accounts list --configuration=cohack
```

An `OPEN: True` row means yes. No rows means no billing yet: start the free trial at
<https://console.cloud.google.com/freetrial>.

### 2. Make a project and link billing

```sh
gcloud projects create cohack-demo-$RANDOM --configuration=cohack
gcloud billing projects link <project-id> --billing-account=<account-id> --configuration=cohack
gcloud config set project <project-id> --configuration=cohack
cp sandbox/.env.local.example sandbox/.env.local   # then fill in the two values
```

Set a budget alert at <https://console.cloud.google.com/billing/budgets>.

### 3. Run it

```sh
sandbox/quota.sh                 # enables the APIs, compares vCPUs with the limits
sandbox/gke-up.sh                # zonal cluster, 3 x e2-standard-2, then the chart
sandbox/forward.sh gke
sandbox/gke-down.sh              # delete the cluster after the demo
```

Three `e2-standard-2` nodes give 6 vCPUs and 24 GB. On the local cluster the whole company
used 2.8 cores and 7.1 GiB with 5 simulated users. A free trial project had a limit of 12
vCPUs across all regions, so 6 leaves room for a node upgrade. The cost is roughly $5 a day.
Check the current GCP price list. On GKE, each container log also goes to Cloud Logging.

## The fake GitHub org

1. Create a free org in the GitHub web UI: <https://github.com/account/organizations/new>.
2. Build and publish:

```sh
sandbox/fake-org.sh build            # 22 repos in sandbox/.org/, local only
sandbox/fake-org.sh publish <org>    # asks you to type the org name first
```

Each service gets its own repo. `protos` holds the gRPC contracts, and `platform` holds Kafka,
the collector, the stores, the dashboards and the Kubernetes manifests. Each repo keeps the
Apache license and a README that names its source path.

## Verified on the local cluster

One run on 2026-09-26, chart `0.42.1`:

- 30 pods ran with zero restarts. After the traffic started, Jaeger listed 21 services.
- One checkout trace had 155 spans across 11 services. It ended at the `publish orders` span
  in `checkout`.
- `accounting` and `fraud-detection` each started their own trace. Their only link back is a
  `FOLLOWS_FROM` reference to that `publish orders` span.
- Both consumers log the `orderId`, and `checkout` tags its spans with `demo.order.id`.

So Jaeger shows one order as three unconnected traces, and the order id joins them.

`sandbox/kc.sh` runs `kubectl` against the sandbox only, for example
`sandbox/kc.sh logs deploy/fraud-detection`.

## Incidents for the demo

Open `http://localhost:8080/feature` and change a flag:

| Flag | What it does | The clip it gives |
|---|---|---|
| `paymentFailure` | fails the chosen percentage of `charge` calls | a failing checkout, traced to the line that throws |
| `kafkaQueueProblems` | overloads Kafka and slows the consumers | two clocks: orders produced against orders consumed |
| `intlShippingSlowdown` | delays non-US shipping requests | one slow hop inside a normal checkout |
| `paymentUnreachable` | gives checkout a wrong payment address | a flow that stops at one edge |
