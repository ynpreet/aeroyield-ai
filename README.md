# AeroYield AI — An Agentic AI Revenue Management System for Airlines

> *"The AI agent that thinks like an airline revenue manager."*
>
> **All data in this demo is SYNTHETIC SAMPLE DATA.** No real airline,
> booking, fare, or revenue data is used anywhere. See section 9 ("Data
> honesty") and section 10 ("Point this at your real data").

## Open in Chrome — live demo

```bash
cd ~/workspace/agentic-ai-workshop/aeroyield-ai
python3 app.py
```

Then open **http://localhost:8004** in Google Chrome. The server prints
`Open in Chrome: http://localhost:8004` on startup (binds 127.0.0.1:8004,
localhost only). Click **"Run live demo"** — the page executes `demo.py`
and renders the run as a styled agent trace: the **PLAN** highlighted, the
three **[TOOL]** calls, the **Observe → Analyze → Decide → Act → Verify**
loop, and a results panel with the headline numbers ($320 → $350, agentic
profit +23%, …).

- Python 3.8+, stdlib only (`http.server` — no Flask/Streamlit, no `pip
  install`, no API keys, no network)
- `app.py` never changes `demo.py` — it only runs it via subprocess and
  displays the output
- Fully offline; the demo finishes in well under a second

---

## Real-world problem, target users, market need, and differentiation

**The problem.** Airline revenue managers do three things constantly: watch
demand signals (events, festivals, booking pace), watch competitors
(without blindly matching them), and watch costs (without confusing a fuel
spike for demand). Then they price — for **profit**, not just revenue —
inside an approval workflow, never by writing straight to a booking system.
Doing that loop by hand, per flight per day, doesn't scale.

**Target users.** Airline revenue-management analysts and pricing teams who
set fares across thousands of flights and need a disciplined,
explainable pricing loop.

**Market need.** Pricing mistakes are expensive in both directions: price
too high and seats fly empty; price too low and you sell out cheap. And the
counterintuitive lesson this demo teaches on the baseline curve — **$280
beats $400 on expected revenue** ($48,200 vs $44,000) because volume wins
when demand is elastic — is exactly the kind of thing gut feel gets wrong.

**Differentiation.** This is the **airline's** pricing agent — not a
passenger price predictor. Setup: one airline, one route (**SFO → BOS**),
180 seats, current fare **$320**, 120 booked / 60 remaining, **14 days to
departure**. The killer differentiator is the three-way baseline
comparison: fixed $320 vs rule-based vs agentic AI on the same simulated
scenarios — revenue, profit, seats sold, unsold, forecast error, volatility,
and shock-scenario performance, with an honest caveat printed underneath.
Headline numbers: agentic profit **$30,050** vs fixed **$24,380** (+23%);
110 seats sold vs 92; forecast error 25% vs 48%; shock-scenario profit
$10,360 vs $5,300.

---

## Meaningful Agentic AI functionality

**Why an agent, not a chatbot?** A chatbot could *describe* revenue
management. This system *runs the decision loop*, out loud, on live
signals:

- **Observe** — three intelligence tools scan demand (festival announced,
  booking pace +7% ahead of baseline), competitors (comparability-verified
  fares), and market/cost (fuel +12%, confidence steady).
- **Analyze** — the pricing decision engine evaluates candidate fares on
  transparent arithmetic: demand forecast D(p), expected revenue R(p),
  contribution (p − cost) × sold, capacity-capped at 60 seats.
- **Decide** — it recommends **$320 → $350**, explains which signals fired,
  why $350 beats $280/$320/$360/$400, what could invalidate it, and a
  sensitivity check (±20% demand → still $350).
- **Act** — the move is **STAGED to an approval queue** (simulation); a
  human approves; it never writes to a live booking system.
- **Verify** — it sets up what to check next (72h pace vs forecast,
  competitor response, auto-flag if pace < 80% of forecast).

And the twist proves it's not a script: when a competitor drops to **$270**,
the agent verifies the fare is comparable — then **does NOT auto-follow**.
It recommends a fenced **$299 fare class** (20 seats) while holding $350:
best contribution, no price war. That's what a revenue manager does — and
what a chatbot cannot.

---

## Project scope, inputs, outputs, constraints, success criteria, and definition of done

**Scope.** A deterministic, offline pricing-agent demo: one live scenario
(three events hit at once), the competitor-drop twist, four scenario
simulations, and a three-way strategy comparison — all in simulation, all
explained.

**Inputs (all synthetic).**

- Flight setup: SFO → BOS, 180 seats, 120 booked / 60 remaining, D-14,
  current fare $320, cost/pax $55.
- Demand curves D(p): baseline, festival, competitor-$270, soft-market
  (hand-built anchors, linearly interpolated).
- Signals: Boston Harbor Music Festival announced (+24 must-fly pax, conf
  0.78), booking pace +7% ahead, competitor fares $340/$335 (verified
  comparable), jet fuel +12% ($55 → ~$58 cost/pax).
- Decision constants: $750 change threshold, candidate fares
  [280…400].

**Outputs.**

- Fare recommendation ($320 → $350 CHANGE), with per-alternative
  contribution deltas, sensitivity analysis, and invalidation conditions.
- Twist recommendation: fenced $299 bucket (20 seats) + hold $350.
- Scenario-simulation takes (festival / competitor −20% / fuel +10% /
  below-pace).
- Three-way comparison table: fixed vs rule-based vs agentic on revenue,
  profit, sold, unsold, forecast MAPE, volatility, S2 profit.

**Constraints.** Stdlib only, fully offline, zero API keys. Fixed clock
(`TODAY = 2026-10-10`) — no `datetime.now()`, no randomness — so output is
byte-identical on every run. **Simulation / approval workflow only — never
a live booking system.**

**Success criteria.** Live scenario recommends $350 with gain clearing the
$750 threshold; twist recommends the fenced ladder (not a price war); fuel
+10% yields HOLD (cost ≠ demand signal); comparison headline reproduces
(+23% profit vs fixed); `TEST-LOG.md` records 10/10 byte-identical runs.

**Definition of done.** All four demo sections print and exit 0; README
carries all 10 checklist sections; `TEST-LOG.md` shows the 10/10
determinism gate passing.

---

## Documented single-agent or multi-agent workflow

**Single-agent workflow** — one orchestrator + three intelligence tools +
the pricing decision engine. (One decision-maker, one audit trail.)

```
┌──────────────────────────────────────────────────────────────┐
│ ORCHESTRATOR -- prints the PLAN, runs Observe->Analyze->     │
│ Decide->Act->Verify. Price moves are STAGED to an approval   │
│ queue (simulation); a human approves; never a live system.   │
└──┬──────────────────┬───────────────────┬────────────────────┘
   ▼                  ▼                   ▼
 TOOL (a)            TOOL (b)            TOOL (c)        PRICING DECISION
 Travel Demand       Competitor          Market & Cost   ENGINE
 Intelligence        Intelligence        Intelligence    D(p): 280->35 ...
 events/news/        comparable fares    fuel, consumer  R(p)=120*320+
 festivals/pace      table; verified     confidence,     min(D(p),60)*p
 signal != proof     before acting       business travel optimize
 of a price rise                         for PROFIT      contribution
```

- **Travel Demand Intelligence** — monitors events/festivals/pace/weather;
  an event is a demand *signal*, not proof prices should rise. Sub-threshold
  noise (a +2% food-blog mention) is logged to the watchlist, not acted on —
  the agent doesn't raise fares on every Boston news mention.
- **Competitor Intelligence** — builds the comparable-fares table, then
  *verifies* comparability (dates, baggage, bookability, inventory) before
  the engine may use it. Never blindly matches.
- **Market & Cost Intelligence** — fuel, consumer confidence, business
  travel. Separates cost signals from demand signals.
- **Decision engine** — transparent arithmetic: demand forecast D(p),
  expected revenue R(p), contribution (p − cost) × sold, capacity-capped at
  60 seats, with a $750 change threshold so prices don't churn on noise.

---

## Working prototype evidence, source code, and setup instructions

### Setup (MacBook)

**In Chrome (recommended for live demos):**

```bash
cd ~/workspace/agentic-ai-workshop/aeroyield-ai
python3 app.py
# then open http://localhost:8004 in Chrome → click "Run live demo"
```

The page runs the demo and renders the agent trace — PLAN, tool calls,
Observe → Verify loop — plus a results panel with the headline numbers.

**In the terminal:**

```bash
cd ~/workspace/agentic-ai-workshop/aeroyield-ai
python3 demo.py
```

- Python 3.8+ (stdlib only — no `pip install`, no API keys, no network)
- Fully offline; finishes in well under a second
- **Deterministic:** the "today" date is a fixed constant in `demo.py`
  (`TODAY = 2026-10-10`) — output is byte-identical on every run

### What you'll see

1. **Live scenario — three events hit at once:** a Boston festival is
   announced, competitor fares rise, booking pace runs ahead of baseline.
   The agent recommends **$320 → $350** with a full explanation — which
   signals fired, why $350 beats $280/$320/$360/$400, what could invalidate
   it, and a sensitivity check (±20% demand → still $350).
2. **The counterintuitive lesson:** on the baseline curve, **$280 beats
   $400 on expected revenue** ($48,200 vs $44,000) — then the engine
   optimizes for **contribution (profit)**, not just revenue, with realism
   caveats (cancellations, buy-up/buy-down, competitor response).
3. **The twist:** a competitor drops to **$270**. The agent verifies the
   fare is comparable (dates, baggage, bookability, inventory) — then
   **does NOT auto-follow**. It recommends a fenced **$299 fare class**
   (20 seats) while holding $350: best contribution, no price war.
4. **Scenario simulations:** festival / competitor −20% / fuel +10% /
   bookings-below-pace — quick takes through the same engine. Note the
   fuel one: *fuel +12% does NOT mean fares +12%* — cost signal ≠ demand
   signal.
5. **Three-way baseline comparison** (the killer differentiator): fixed
   $320 vs rule-based vs agentic AI on the same simulated scenarios —
   revenue, profit, seats sold, unsold, forecast error, volatility, and
   shock-scenario performance, with an honest caveat printed underneath.

### Files

- `demo.py` — the whole demo (entry point: `python3 demo.py`)
- `app.py` — localhost web UI: `python3 app.py`, then open
  http://localhost:8004 in Chrome and click "Run live demo" (stdlib only;
  runs `demo.py` via subprocess, never modifies it)
- `requirements.txt` — stdlib-only note
- `TEST-LOG.md` — 10 consecutive runs: exit codes + output hashes; plus the
  12-round web-UI reliability gate for `app.py`
- `RUBRIC.md` — honest self-score vs the hackathon judging rubric +
  Preet's five evaluation dimensions
- `CHECKLIST.md` — README checklist mapping the 10 required sections

### Speaker notes (6-minute walkthrough)

1. **Hook (30s):** "This is not a price predictor for passengers. This is
   the *airline's* agent — it thinks like a revenue manager."
2. **Observe (1m):** Walk the three tools. Land the two mantras: *"an event
   is a signal, not proof"* and *"fuel +12% does not mean fares +12%."*
3. **Analyze (1m):** Show the baseline table — "$280 beats $400 on revenue.
   Counterintuitive, right? Volume." Then: "but we optimize profit."
4. **Decide (1m):** The $350 recommendation — read the four 'why $350 beats'
   lines. Ask the room what could invalidate it before revealing the list.
5. **Twist (1m):** Competitor drops to $270. "What would *you* do?" Let them
   answer, then reveal: not follow — fenced $299 bucket. "That's what a
   revenue manager does."
6. **Comparison + caveat (1m):** The three-way table, then read the honest
   caveat aloud — "it beats the *chosen baselines under simulated
   assumptions*." Honesty is the differentiator.
7. **Close (30s):** "Observe, analyze, decide, act, verify — and every
   number reproduces. Run it ten times." (See TEST-LOG.md.)

Anticipated questions:

- *"Why not just always pick the max?"* — the $750 change threshold and
  the approval queue: churn costs trust and money.
- *"Is the memory/learning real?"* — the loop is Observe→…→Verify with
  forecast-error tracking; a production version would re-fit D(p) on
  realized bookings.
- *"Would this surge-price a festival?"* — it prices an event premium with
  fences and human approval; pricing ethics (caps during disruptions) would
  be an explicit policy layer — see RUBRIC.md.

---

## Functional and end-to-end testing, realistic scenarios, failure cases, reliability, and human oversight

**Realistic scenarios (end to end).** The live scenario (three events at
once), the competitor-$270 twist, four injected scenario simulations, and
the three-way comparison across three demand worlds (festival surge,
competitor price war, soft market) — all printed, all explained, all
exiting 0.

**Failure cases the demo handles** (all from `demo.py` behavior):

- **Sub-threshold noise.** A +2% food-blog demand mention is logged to the
  watchlist, **not acted on** — the agent doesn't raise fares on every
  Boston news mention.
- **Cost signal mistaken for demand.** Fuel +10% raises cost/pax $55 → $58,
  but the best fare stays $280 with gain below the $750 threshold →
  **HOLD**. Cost signal, not demand signal — printed explicitly.
- **Soft market.** Below-pace bookings route through the soft demand curve;
  the optimal move's gain still clears nothing → HOLD $320 with a review
  trigger (pace < 90 by D-10 → cut to $299).
- **Competitor undercut.** $270 is verified comparable (dates, baggage,
  bookability, 9+ seats) — a real threat, not a mirage fare — yet the
  agent does **not** auto-follow; the fenced $299 ladder wins on
  contribution without a price war.
- **Capacity binding.** Every candidate fare is capped at 60 remaining
  seats (`min(dem, seats)`); the sensitivity check confirms $350 also
  avoids denied boardings.
- **Curve edges.** Demand interpolation clamps outside the anchor fares —
  no extrapolation fantasies beyond the hand-built anchors.

**Reliability gate.** `TEST-LOG.md` records 10 consecutive runs of
`python3 demo.py` — exit codes + SHA-256 of full output — with the result
**10/10 PASSED, byte-identical output on every run**.

**Human oversight.** Price moves are **staged to a pricing approval queue
(simulation); a revenue manager approves; the offer auto-expires in 24h if
unapproved. This demo NEVER writes to a live booking system.** The VERIFY
step defines what a human checks next — 72h pace vs forecast, competitor
response, auto-flag if pace < 80% of forecast.

---

## Focus, feasibility, and avoidance of unnecessary complexity

One file, stdlib only, hand-built demand curves, fixed clock. Deliberately
*not* included:

- **No real booking-system integration.** The approval queue is simulated;
  the "never a live system" boundary is printed, not assumed.
- **No ML training loop.** D(p) curves are synthetic anchors with linear
  interpolation — transparent enough to audit, honest enough to caveat.
- **No stochastic simulation.** Deterministic round-half-up, fixed TODAY,
  no wall clock — the demo reproduces exactly, which is the whole point
  of the 10/10 gate.
- **No hidden parameters.** Every constant (thresholds, costs, anchors) is
  a named constant at the top of `demo.py`.

Feasibility: a student can trace the $320 → $350 recommendation through
printed arithmetic line by line — then replace the synthetic constants with
the CSV schemas in section 10 without changing the agent's shape.

---

## Interdisciplinary team roles and division of labor

| Role | Owns in this demo | Concrete component |
|---|---|---|
| **Domain researcher** | Revenue-management economics | D(p) demand-curve anchors, contribution-over-revenue optimization, comparability checks (dates/baggage/bookability/inventory), the $750 change threshold, pricing-ethics caveats |
| **Agent engineer** | Observe → Analyze → Decide → Act → Verify loop | Orchestrator, the three intelligence tools, `evaluate`/`recommend` decision engine, the twist re-evaluation, the fenced-fare-ladder option |
| **Data engineer** | Synthetic data and real-data schemas | Demand-curve constants, event/competitor/fuel fixtures, the `flights.csv` / `demand_curve.csv` / `competitor_fares.csv` / `events.csv` / `market.csv` schemas in section 10 |
| **UX / storyteller** | The 6-minute walkthrough and the honesty beat | Speaker notes (hook → observe → analyze → decide → twist → comparison + caveat), the counterintuitive $280-beats-$400 lesson, the "say it out loud" caveat |
| **QA** | Determinism gate and simulation honesty | `TEST-LOG.md` 10/10 byte-identical gate, sensitivity checks (±20% demand → still $350), the printed honest caveat that the comparison beats *chosen baselines under simulated assumptions* |

---

## Limitations, risks, and responsible AI (ethics, privacy, security, safety)

**Data honesty — what's synthetic vs what would be real.** **Everything in
this demo is synthetic**, including: the demand curves D(p), the event
feed, competitor fares, booking pace, fuel moves, and the simulation
scenarios. They were hand-built to teach, not measured.

What would be real in production (and what each proxies):

| Demo input | Real-world source |
|---|---|
| D(p) demand curve | Historical bookings by fare point (MIDT / internal PNR data), choice models |
| Event signals | Events APIs, conference calendars, news feeds, weather feeds |
| Competitor fares | Filed-fare data (ATPCO), GDS shopping data — *public* fares only |
| Booking pace | Internal reservations system (booked/remaining by flight) |
| Cost per pax | Airline cost accounting (fuel burn share, catering, fees) |

**Critical honesty note:** public fares ≠ actual demand, inventory, or
revenue. A competitor's $270 could be a 9-seat teaser, include no bags, or
be unbookable — which is exactly why the demo's comparability check exists
before any price action.

**Risks and ethics.**

- **Pricing ethics.** The demo prices an event premium with fences and
  human approval; caps during disruptions (e.g., no surge pricing on
  evacuations) would be an explicit policy layer in production.
- **Simulation honesty.** The three-way comparison proves the agent beats
  the *chosen baselines under simulated assumptions* (synthetic curves,
  perfect shock recognition by D-7) — it does NOT prove it beats real
  airline revenue-management systems on real data. The caveat is printed in
  the demo and read aloud on stage.
- **No live-system risk by design.** The approval-queue boundary and the
  24h auto-expiry mean no price can execute without a human — the demo
  cannot cause real-world pricing harm.

---

## Practical value, adoption path, and measurable outcomes

**Practical value.** A revenue manager's daily loop — watch demand, watch
competitors, watch costs, price for profit inside approvals — run
continuously, explainably, and reproducibly instead of by spreadsheet and
gut feel. The demo's headline (+23% profit vs a fixed fare under simulated
assumptions) is the *shape* of the value; the discipline (verify
comparability, separate cost from demand, stage for approval) is the value
itself.

**Adoption path — point this at your real data.** Replace the synthetic
constants at the top of `demo.py` with CSV loads (`import csv` — still
stdlib). Expected schemas:

**`flights.csv`** — the flight being priced
| column | example |
|---|---|
| `route` | `SFO-BOS` |
| `seats_total` / `seats_booked` | `180` / `120` |
| `days_to_departure` | `14` |
| `current_fare` | `320` |

**`demand_curve.csv`** — estimated incremental bookings per fare point
| column | example |
|---|---|
| `fare` | `350` |
| `expected_bookings` | `52` |
| `source` | `choice-model v3` |

**`competitor_fares.csv`** — shopped/screened competitor fares
| column | example |
|---|---|
| `carrier` | `Competitor A` |
| `fare` | `340` |
| `dates_match` / `baggage_ok` / `bookable` / `inventory` | `true` / `true` / `true` / `9+` |

**`events.csv`** — demand-signal feed
| column | example |
|---|---|
| `event_id` | `EVT-101` |
| `type` | `festival` / `conference` / `weather` / `news` |
| `name` | `Boston Harbor Music Festival` |
| `start_date` / `end_date` | `2026-10-23` |
| `demand_delta_pax` | `24` |
| `confidence` | `0.78` |

**`market.csv`** — cost/macro signals
| column | example |
|---|---|
| `signal` | `jet_fuel_wow` |
| `value` | `+12%` |
| `cost_per_pax` | `58` |

To make "today" real instead of fixed, replace `TODAY = date(2026, 10, 10)`
with `TODAY = date.today()` — output will then vary by run date (correct
for a live tool; wrong for a reproducible demo).

**Measurable outcomes.** Today: byte-identical determinism (10/10), the
$320 → $350 recommendation with invalidation conditions, and the three-way
comparison table. In production: forecast MAPE vs realized bookings,
contribution per flight, price-change volatility, and shock-scenario
profit — the same metrics the demo already computes.

---

*Built for the Agentic AI Workshop*
