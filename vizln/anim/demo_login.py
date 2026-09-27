from vanim import *

class OnboardingFlow(Clip):
    TITLE = "Onboarding Flow: Request Lifecycle"
    SUB = "Client -> API Gateway -> Auth Service -> PostgreSQL"

    def story(self):
        self.source("demo: login request")

        client = node(box, [-5.0, 0.0], ["Client"], AMBER_, w=2.0)
        gw = node(box, [-1.5, 0.0], ["API Gateway"], TEAL_, w=2.4)
        auth = node(box, [2.0, 0.0], ["Auth Service"], PLUM_, w=2.4)
        db = node(cylinder, [5.0, 0.0], ["PostgreSQL", "users"], GREEN_, w=2.0, h=1.0)
        
        # ports
        pc = ports(client.shape, out=(RIGHT, 0.0), inp=(RIGHT, 0.0))
        pgw = ports(gw.shape, inp=(LEFT, 0.0), out=(RIGHT, 0.0))
        pauth = ports(auth.shape, inp=(LEFT, 0.0), out=(RIGHT, 0.0))
        pdb = ports(db.shape, inp=(LEFT, 0.0), out=(LEFT, 0.0))

        # nets
        w_req1 = net(pc["out"], pgw["inp"], color=AMBER_)
        w_req2 = net(pgw["out"], pauth["inp"], color=TEAL_)
        w_db = net(pauth["out"], pdb["inp"], color=GREEN_)

        nets = VGroup(w_req1, w_req2, w_db)

        # Step 0: All wired up
        self.beat(*[FadeIn(m) for m in (client, gw, auth, db)], FadeIn(nets),
                  say="wired, waiting for request", color=DIM_, hold=0.9)

        # Step 1: Client issues POST /login.
        self.beat(*w_req1.light(AMBER_), pulse(gw, AMBER_),
                  say="Step 1: Client issues POST /login.", color=AMBER_, hold=0.7)

        # Step 2: Gateway forwards payload to Auth Service.
        self.beat(*w_req2.light(TEAL_), pulse(auth, TEAL_), *w_req1.rest(),
                  say="Step 2: Gateway forwards payload to Auth Service.", color=TEAL_, hold=0.7)

        # Step 3: Auth queries PostgreSQL for user record and verifies password hash.
        self.beat(*w_db.light(GREEN_), pulse(db, GREEN_), *w_req2.rest(),
                  say="Step 3: Auth queries PostgreSQL and verifies hash.", color=GREEN_, hold=0.7)

        # Step 4: Auth returns signed JWT back to Client.
        self.beat(*w_db.back(GREEN_), *w_req2.back(PLUM_), *w_req1.back(PLUM_), pulse(client, PLUM_),
                  say="Step 4: Auth returns signed JWT back to Client.", color=PLUM_, hold=1.4)
