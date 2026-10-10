# Rubric Self-Score — AeroYield AI

Scored 1–5 per criterion against
`~/workspace/peaii-hackathon/judging-rubric.md`. Points = (score ÷ 5) × weight.
Then scored 1–5 on Preet's five evaluation dimensions.

## Hackathon rubric (100 pts)

| # | Criterion | Weight | Score | Points | One-line evidence |
|---|-----------|--------|-------|--------|-------------------|
| 1 | Problem Definition & Real-World Impact | 25 | 5/5 | 25 | Named user (airline revenue manager), exact setup, $B-scale yield lever |
| 2 | Meaningful Agentic AI Behavior | 20 | 4/5 | 16 | Orchestrator+tools, Observe→Verify loop, restraint on noise, re-evaluation on twist |
| 3 | Working Prototype | 15 | 5/5 | 15 | Full demo in ~0.07s, offline, stdlib-only, 10/10 byte-identical runs |
| 4 | Innovation & Creativity | 15 | 4/5 | 12 | Three-way baseline comparison as killer differentiator; fare-ladder > price war |
| 5 | Presentation & Communication | 15 | 4/5 | 12 | Speaker notes, story, explainable output; terminal-only, no visuals |
| 6 | Responsible AI & Feasibility | 10 | 5/5 | 10 | Approval queue (never live), honest simulation caveat, data-honesty section |
| | **TOTAL** | **100** | | **90** | |

## Evidence per score

**1. Problem (5/5).** The user is specific — an airline revenue manager —
not "travelers" or "everyone." The pain is concrete (manual repricing across
signals), the setup is exact (SFO→BOS, 180 seats, $320, D-14), and the
framing ("the AI agent that thinks like an airline revenue manager") shows
domain understanding: fare classes, fences, buy-up/buy-down, spill,
contribution vs revenue. Yield management moves real P&L.

**2. Agentic behavior (4/5).** One orchestrator + three intelligence tools +
decision engine, running a visible Observe → Analyze → Decide → Act →
Verify loop with the PLAN printed. Genuinely agentic moments: treating an
event as *signal not proof*, declining to act on sub-threshold noise
(continuous monitoring), verifying competitor comparability before acting,
re-evaluating rather than auto-following the $270 twist, and staged
approval instead of direct action. Docked one point: tools and engine are
deterministic functions — no model doing reasoning, so "why an agent" rests
on architecture, not on visible machine reasoning.

**3. Prototype (5/5).** `python3 demo.py` runs the entire arc — intel sweep,
engine, live scenario, twist, 4 scenario simulations, three-way comparison —
in ~0.07s with zero setup. TEST-LOG.md proves 10/10 byte-identical runs.

**4. Innovation (4/5).** The three-way baseline comparison (fixed vs
rule-based vs agentic, 7 metrics, honest caveat) is a genuine differentiator
for a workshop demo, and the fare-class-ladder answer to the price war is
the kind of non-obvious RM move judges remember. Docked one point: RM
concepts themselves (fences, contribution, spill) are industry-standard —
the novelty is in the agentic packaging, not the economics.

**5. Presentation (4/5).** README has the story, MacBook run steps, a
6-minute speaker script with anticipated Q&A, an architecture diagram, and
the demo narrates itself in plain language a non-technical audience can
follow. Docked one point: terminal text only — no slides or dashboard for
the business-leader audience the rubric weights.

**6. Responsible AI (5/5).** Price changes are *staged to an approval queue
in simulation* — the demo states repeatedly it never touches a live booking
system. The honest caveat is printed in the demo itself ("beats the CHOSEN
baselines UNDER SIMULATED ASSUMPTIONS"), the README has a data-honesty
section (public fares ≠ demand/inventory/revenue), and surge-pricing ethics
are flagged as an explicit policy layer rather than ignored.

## Preet's five evaluation dimensions (1–5)

| Dimension | Score | One-line evidence |
|---|---|---|
| Business relevance | 5/5 | Airline RM is a $B lever; every point of yield is P&L — and the demo speaks profit, not just revenue |
| Data quality | 3/5 | Fully synthetic but honestly labeled, with real-data CSV schemas; no real D(p) or booking data |
| Decision-making | 5/5 | Transparent engine, sensitivity ±20%, explicit invalidation conditions, no auto-follow on the twist |
| Agentic behavior | 4/5 | Full Observe→Verify loop with restraint and re-evaluation; deterministic tools, no LLM reasoning |
| Measurable impact | 4/5 | 7-metric three-way comparison (+23% profit, −48%→25% forecast error); simulated, honestly caveated |

## Honest gap note

The biggest gap is **data quality (3/5)**: every "intelligence" input is
hand-built, so the three-way comparison proves the *decision logic*, not a
data pipeline. Second gap: the agent's D-7 shock recognition in the
simulation is perfect by construction — a real system has partial
observability and would sometimes misread the shock. Third: no LLM anywhere,
so the "agentic" claim is architectural rather than demonstrated reasoning.

## How a student could close it (6-month roadmap)

1. **Real D(p) (closes data quality):** fit the demand curve on 2–3 years of
   historical bookings by fare point (even a public BTS/DB1B-style sample);
   re-run the three-way comparison — now the win is empirical.
2. **LLM on the tools (closes agentic):** let Travel Demand Intelligence
   parse free-text news/event feeds and Competitor Intelligence screen real
   shopped fares; keep the engine as the deterministic guardrail —
   *neuro-symbolic*, and easy to explain to judges.
3. **Partial observability (closes honesty gap):** inject shock-recognition
   delay/noise into the simulation; show the agent's edge *shrinks but
   survives* — a stronger claim than perfect foresight.
4. **Ethics policy layer (extends responsible AI):** hard caps on
   disruption-driven surcharges + dual approval above 25%; print the policy
   in the price sheet.
5. **One-page dashboard (closes presentation):** price path + event timeline
   + approval queue as a simple web page for the non-technical audience.
