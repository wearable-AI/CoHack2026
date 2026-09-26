"""The schematic layer, in one scene. Copy this instead of rewriting the shapes.

Two case studies wrote these builders out before they lived in vanim, and the
two copies drifted. Everything below is in vanim now, so a clip that draws a
service map starts here:

    anim/render.sh anim/examples/schematic.py --draft
    anim/check.sh  anim/examples/schematic.py

Three channels, one fact each. Shape says what kind of thing it is, outline
colour says its role, a badge says which hosted product. A store stays dim
until something writes to it, so the frame is a record of what has happened
rather than a diagram of what exists.
"""
from vanim import *


class Schematic(Clip):
    TITLE = "one job, one queue, one bucket"
    SUB = "the schematic layer: node, ports, net, and the verbs"

    def story(self):
        self.source("example: no measured figures on this frame")

        # --- shapes. the maker is the first argument, so a role can change its
        # outline colour without changing what kind of thing it is.
        api = node(capsule, [-4.8, 1.6], ["POST /v1/exports"], AMBER_, w=2.9)
        job = node(box, [-0.6, 1.6], ["exporter", "one page per task"], TEAL_,
                   w=3.0, h=0.86, icon="cloud_run")
        q = node(box, [-0.6, -0.4], ["export-queue"], BLUE_, w=3.0, icon="cloud_tasks")
        gcs = node(pail, [4.6, 1.6], ["chunks/"], GREEN_, w=2.4, h=0.90)
        db = node(cylinder, [4.6, -0.4], ["job state"], PLUM_, w=2.4, h=0.90)
        zone = dashedbox([-0.6, 0.6], 4.2, 3.6, DIM_)

        # --- ports. the direction belongs to the port, so no wire leaves sideways.
        pa = ports(api.shape, out=(RIGHT, 0.0))
        pj = ports(job.shape, inp=(LEFT, 0.0), down=(DOWN, 0.0),
                   store=(RIGHT, 0.14), state=(RIGHT, -0.14))
        pq = ports(q.shape, up=(UP, 0.0), out=(RIGHT, 0.0))
        pg = ports(gcs.shape, inp=(LEFT, 0.0))
        pd = ports(db.shape, inp=(LEFT, 0.0), up=(UP, 0.0))

        # --- nets. a bay puts every vertical on a known lane; corners route a
        # run that one lane cannot reach. both refuse a diagonal segment.
        bay = Bay(2.2, pitch=0.22, span=(1.5, 3.0))
        w_call = net(pa["out"], pj["inp"], color=DIM_)
        w_task = net(pj["down"], pq["up"], color=BLUE_)
        w_run = net(pq["out"], pd["up"], bay=bay, lane=0, color=BLUE_)
        w_put = net(pj["store"], pg["inp"], color=GREEN_)
        w_state = net(pj["state"], pd["inp"], corners=[[2.6, 1.46], [2.6, -0.4]],
                      color=PLUM_)
        nets = VGroup(w_call, w_task, w_run, w_put, w_state)

        # --- a store sleeps until something writes to it
        for s in (gcs, db):
            fade_now(s, SLEEP_)

        self.beat(*[FadeIn(m) for m in (api, job, q, gcs, db, zone)], FadeIn(nets),
                  say="wired, and nothing has run", color=DIM_, hold=0.9)
        self.beat(*w_call.light(AMBER_), pulse(job, AMBER_),
                  say="a caller asks for an export", color=AMBER_, hold=0.7)
        self.beat(*w_task.light(BLUE_), *w_run.watch(BLUE_),
                  say="one task per page, and the queue stays open", color=BLUE_, hold=0.7)
        self.beat(*w_put.light(GREEN_), *fade_to(gcs, 1.0),
                  say="the first chunk lands", color=GREEN_, hold=0.7)
        self.beat(*w_state.light(PLUM_), *fade_to(db, 1.0), *w_put.rest(),
                  say="the job records its progress", color=PLUM_, hold=0.7)
        self.beat(*w_state.back(PLUM_), say="and the caller reads it back",
                  color=PLUM_, hold=1.4)
