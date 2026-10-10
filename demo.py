#!/usr/bin/env python3
"""
AeroYield AI -- An Agentic AI Revenue Management System for Airlines
"the AI agent that thinks like an airline revenue manager"

WHAT THIS IS: the AIRLINE's pricing agent (not a passenger price predictor).
Setup: one airline, one route -- SFO -> BOS, 180 seats, current fare $320,
120 booked / 60 remaining, 14 days to departure.

HOW IT'S BUILT: one orchestrator + tools (not separate agents):
  (a) Travel Demand Intelligence  -- events/news/festivals/conferences/weather
  (b) Competitor Intelligence      -- comparable fares, verified before acting
  (c) Market & Cost Intelligence   -- fuel, confidence, business travel trends
  + Pricing Decision Engine        -- ML-style demand forecast D(p), expected
                                     revenue R(p), contribution (profit)

DECISION LOOP: Observe -> Analyze -> Decide -> Act -> Verify.
Price changes stay in a SIMULATION / approval workflow -- NEVER a live
booking system.

DATA: 100% SYNTHETIC SAMPLE DATA, hardcoded below. Public fares are not
demand, inventory, or revenue -- the README's data-honesty section and the
"point at real data" CSV schemas explain what would be real.

RULES: stdlib only, fully offline, zero API keys. The clock is FIXED
(TODAY = 2026-10-10) -- no datetime.now(), no random -- so output is
byte-identical on every run.
"""

from datetime import date

# --------------------------------------------------------------------------
# Fixed clock + core setup (exact spec numbers)
# --------------------------------------------------------------------------
TODAY = date(2026, 10, 10)
ROUTE = "SFO -> BOS"
SEATS_TOTAL, SEATS_BOOKED = 180, 120
SEATS_LEFT = SEATS_TOTAL - SEATS_BOOKED          # 60
DAYS_TO_DEPARTURE = 14
CURRENT_FARE = 320
BASE_REVENUE = SEATS_BOOKED * CURRENT_FARE       # $38,400 already banked
COST_PER_PAX = 55                                # variable cost / passenger ($)
CHANGE_THRESHOLD = 750                           # min $ gain to move the price
CANDIDATES = [280, 300, 320, 350, 360, 380, 400]

# --------------------------------------------------------------------------
# SYNTHETIC demand curves: D(p) = expected incremental bookings at fare p.
# Anchors are synthetic; values between anchors are linearly interpolated.
# --------------------------------------------------------------------------
BASE_ANCHORS = {280: 35, 320: 28, 360: 21, 400: 14}          # baseline
FEST_ANCHORS = {280: 58, 300: 56, 320: 54, 350: 52,          # festival:
                360: 46, 380: 40, 400: 34}                  # inelastic event segment
COMP_ANCHORS = {280: 30, 300: 25, 320: 20, 350: 16,          # competitor at $270
                360: 14, 380: 12, 400: 10}
SOFT_ANCHORS = {p: d * 0.65 for p, d in                           # soft market
                {280: 35, 300: 31.5, 320: 28, 350: 22.75,
                 360: 21, 380: 17.5, 400: 14}.items()}


def rhu(x):
    """Round-half-up (deterministic; avoids banker's rounding surprises)."""
    return int(x + 0.5)


def make_curve(anchors):
    xs = sorted(anchors)

    def d(p):
        if p <= xs[0]:
            return float(anchors[xs[0]])
        if p >= xs[-1]:
            return float(anchors[xs[-1]])
        for a, b in zip(xs, xs[1:]):
            if a <= p <= b:
                t = (p - a) / (b - a)
                return anchors[a] + t * (anchors[b] - anchors[a])
        return float(anchors[xs[-1]])

    return d


D_BASE = make_curve(BASE_ANCHORS)
D_FEST = make_curve(FEST_ANCHORS)
D_COMP = make_curve(COMP_ANCHORS)
D_SOFT = make_curve(SOFT_ANCHORS)


# --------------------------------------------------------------------------
# Formatting helpers (fixed decimals => deterministic output)
# --------------------------------------------------------------------------
def usd(x):
    return "$%s" % format(int(round(x)), ",d")


def bar():
    print("=" * 74)


def thin():
    print("-" * 74)


# ==========================================================================
# PRICING DECISION ENGINE
# ==========================================================================
def evaluate(prices, demand_fn, seats, cost):
    """Return [(price, demand, sold, incr_rev, incr_contrib), ...]."""
    rows = []
    for p in prices:
        dem = demand_fn(p)
        sold = min(rhu(dem), seats)
        rows.append((p, dem, sold, sold * p, (p - cost) * sold))
    return rows


def recommend(current, rows, threshold):
    """Pick max-contribution price; act only if gain clears the threshold."""
    best = max(rows, key=lambda r: r[4])
    cur = [r for r in rows if r[0] == current][0]
    gain = best[4] - cur[4]
    action = "CHANGE" if (gain > threshold and best[0] != current) else "HOLD"
    return best, cur, gain, action


def print_engine_table(rows, title):
    print("  " + title)
    print("  %6s %10s %6s %12s %12s %12s"
          % ("fare", "D(p) dem.", "sold", "incr. rev.", "total rev.", "contrib."))
    for p, dem, sold, rev, contrib in rows:
        print("  %6s %10.1f %6d %12s %12s %12s"
              % (usd(p), dem, sold, usd(rev), usd(BASE_REVENUE + rev), usd(contrib)))


# ==========================================================================
# TOOL (a) -- Travel Demand Intelligence
# ==========================================================================
def tool_demand_intelligence():
    print("  [TOOL] Travel Demand Intelligence -- scanning signals ...")
    print("    + SIGNAL: Boston Harbor Music Festival announced (Oct 23-25).")
    print("      -> SFO->BOS demand: +24 must-fly pax (inelastic event segment).")
    print("      -> Confidence 0.78. NOTE: an event is a demand SIGNAL, not proof")
    print("         prices should rise -- the engine still has to earn the move.")
    print("    + SIGNAL: booking pace ahead of baseline: 120 booked vs 112 expected")
    print("      at D-14 (+7%). Corroborates the festival read.")
    print("    + noise : 'Boston food-blog fest' (+2% demand) -- below the action")
    print("      threshold. Logged to watchlist. The agent does NOT raise fares")
    print("      on every Boston news mention.")
    print("    = DEMAND MODEL: festival-adjusted curve loaded "
            "(event segment elasticity -0.3 vs leisure -1.4).")


# ==========================================================================
# TOOL (b) -- Competitor Intelligence
# ==========================================================================
def tool_competitor_intelligence():
    print("  [TOOL] Competitor Intelligence -- fares are verified, not matched.")
    print("    carrier        fare   dates  baggage  bookable  inventory  verdict")
    print("    AeroYield (us) $320   --     --       --        60 seats   --")
    print("    Competitor A   $340   ok     ok       ok        9+ seats   COMPARABLE")
    print("    Competitor B   $335   ok     ok*      ok        9+ seats   COMPARABLE")
    print("      * B charges $35 for checked bags -- noted, still comparable.")
    print("    = Both rivals are comparable AND priced above us: the market has")
    print("      headroom. We do not blindly match -- comparability first.")


# ==========================================================================
# TOOL (c) -- Market & Cost Intelligence
# ==========================================================================
def tool_market_cost_intelligence():
    print("  [TOOL] Market & Cost Intelligence -- separating cost from demand.")
    print("    + jet fuel +12% week-over-week -> variable cost/pax $55 -> ~$58.")
    print("    + consumer confidence steady (index 102); business travel +4%.")
    print("    = Fuel +12% is a COST signal, not a demand signal. It trims margin;")
    print("      it does NOT mean fares +12%. No fare action on fuel alone.")


# ==========================================================================
# LIVE DEMO SCENARIO -- three events hit at once
# ==========================================================================
def live_scenario():
    bar()
    print("LIVE SCENARIO -- three events hit at once (pricing date %s)"
          % TODAY.isoformat())
    bar()

    print("\n[ORCHESTRATOR] PLAN -- decision loop: "
          "Observe -> Analyze -> Decide -> Act -> Verify\n")

    print("OBSERVE -- calling intelligence tools ...")
    tool_demand_intelligence()
    print()
    tool_competitor_intelligence()
    print()
    tool_market_cost_intelligence()

    print("\nANALYZE -- decision engine on the BASELINE curve first "
          "(the counterintuitive lesson):")
    base_rows = evaluate(CANDIDATES, D_BASE, SEATS_LEFT, COST_PER_PAX)
    print_engine_table(base_rows, "R(p) = 120*$320 + min(D(p),60)*p   (synthetic D(p))")
    r280 = BASE_REVENUE + [r for r in base_rows if r[0] == 280][0][3]
    r400 = BASE_REVENUE + [r for r in base_rows if r[0] == 400][0][3]
    print("  LESSON: $280 -> %s expected revenue BEATS $400 -> %s (+%s)."
          % (usd(r280), usd(r400), usd(r280 - r400)))
    print("  Higher price is not higher revenue: volume wins when demand is elastic.")
    print("  Realism caveats: ignores cancellations/no-shows, buy-up/buy-down")
    print("  between fare classes, and competitor response -- a real RM system")
    print("  models all three. We then optimize CONTRIBUTION (profit), not revenue.")

    print("\nANALYZE -- engine on the FESTIVAL-adjusted demand curve:")
    fest_rows = evaluate(CANDIDATES, D_FEST, SEATS_LEFT, COST_PER_PAX)
    print_engine_table(fest_rows, "festival-adjusted D(p), cost $55/pax")
    best, cur, gain, action = recommend(CURRENT_FARE, fest_rows, CHANGE_THRESHOLD)

    print("\nDECIDE --")
    print("  SIGNALS USED: (1) festival event segment +24 pax (conf 0.78);")
    print("                 (2) booking pace +7% ahead of baseline;")
    print("                 (3) both competitors comparable and priced above us.")
    print("  RECOMMENDATION: $320 -> $350  [%s]" % action)
    print("  WHY $350 BEATS THE ALTERNATIVES (expected contribution):")
    for p in (280, 320, 360, 400):
        alt = [r for r in fest_rows if r[0] == p][0]
        print("    vs %s: +%s contribution -- %s"
              % (usd(p), usd(best[4] - alt[4]),
                 {280: "avoids selling out too cheap (spill risk at 58 demand)",
                  320: "prices the event premium; volume barely drops 54->52",
                  360: "protects volume without giving away yield",
                  400: "avoids volume collapse (34 vs 52)"}[p]))
    print("  Expected gain vs holding $320: +%s (clears the $%d change threshold)."
          % (usd(gain), CHANGE_THRESHOLD))
    print("  Confidence 0.74. Limits: festival model untested on this event;")
    print("  assumes no competitor response within 48h.")
    print("  SENSITIVITY: demand -20% -> still $350; demand +20% -> still $350")
    print("  (capacity binds -- $350 also avoids denied boardings).")
    print("  WHAT COULD INVALIDATE IT: festival cancelled/postponed; competitor")
    print("  undercuts below $300 (see twist playbook); event segment < ~12 pax.")

    print("\nACT --")
    print("  STAGED to the pricing approval queue (SIMULATION). A revenue manager")
    print("  approves; the offer auto-expires in 24h if unapproved.")
    print("  This demo NEVER writes to a live booking system.")

    print("\nVERIFY -- (what we would check next)")
    print("  72h booking pace vs forecast (52 pax); competitor response; festival")
    print("  news. Auto-flag for review if pace < 80% of forecast.")
    return fest_rows


# ==========================================================================
# THE TWIST -- competitor drops to $270
# ==========================================================================
def twist_scenario():
    bar()
    print("TWIST -- competitor drops to $270. The agent re-evaluates.")
    print("It does NOT auto-follow.")
    bar()
    print("\n[ORCHESTRATOR] re-running Observe -> Analyze -> Decide ...\n")
    print("OBSERVE --")
    print("  [TOOL] Competitor Intelligence: rival filed $270 on SFO->BOS, same")
    print("  weekend. Comparability check: dates ok / baggage ok / bookable ok /")
    print("  inventory 9+ seats ok -> VERDICT: COMPARABLE. This is a real threat,")
    print("  not a mirage fare.")
    print("  [TOOL] Demand Intelligence: our $350 demand falls 52 -> 34 pax")
    print("  (buy-down to the rival). Event segment still must fly.")
    print("\nANALYZE -- options at competitor $270 (festival world, cost $55/pax):")
    hold = (350, 34.0, 34, 34 * 350, (350 - COST_PER_PAX) * 34)
    cut320 = (320, 41.0, 41, 41 * 320, (320 - COST_PER_PAX) * 41)
    ladder_rev = 20 * 299 + 26 * 350
    ladder_c = 20 * (299 - COST_PER_PAX) + 26 * (350 - COST_PER_PAX)
    promo_c = (350 - COST_PER_PAX - 25) * 40
    print("  option                              sold   incr.rev.  contrib.")
    print("  hold $350                           %4d   %8s   %8s"
          % (hold[2], usd(hold[3]), usd(hold[4])))
    print("  cut to $320                         %4d   %8s   %8s"
          % (cut320[2], usd(cut320[3]), usd(cut320[4])))
    print("  ADD $299 fare class (20 seats,       46   %8s   %8s"
          % (usd(ladder_rev), usd(ladder_c)))
    print("    fenced*) + hold $350")
    print("  promote $350 (free checked bag)     %4d   %8s   %8s"
          % (40, usd(40 * 350), usd(promo_c)))
    print("  * fences: 7-day advance purchase, nonrefundable, 20-seat cap.")
    print("\nDECIDE --")
    print("  RECOMMENDATION: ADD the fenced $299 bucket, HOLD $350 base.")
    print("  WHY: best contribution (%s) -- recaptures price-sensitive shoppers"
          % usd(ladder_c))
    print("  without starting a price war; protects yield on must-fly traffic;")
    print("  matching $270 would torch margin for zero strategic gain.")
    print("\nACT -- staged to approval queue (SIMULATION). VERIFY -- watch rival's")
    print("  inventory: if their $270 sells out, revisit the fences.")


# ==========================================================================
# SCENARIO SIMULATIONS -- injectable, quick takes through the engine
# ==========================================================================
def scenario_simulations():
    bar()
    print("SCENARIO SIMULATIONS -- same engine, injected scenarios")
    bar()
    scenarios = [
        ("festival announced",
         "festival curve in -> $350 optimal, gain +$1,030 over $320 -> CHANGE.",
         None),
        ("competitor -20% ($320 -> $256)",
         "comparability check first; if comparable -> fenced $289 bucket + hold.",
         None),
        ("fuel +10%",
         None,  # computed below
         "cost"),
        ("bookings below pace (96 vs 112 expected)",
         None,  # computed below
         "pace"),
    ]
    for name, take, kind in scenarios:
        if kind == "cost":
            rows = evaluate(CANDIDATES, D_BASE, SEATS_LEFT, COST_PER_PAX + 3)
            best, cur, gain, action = recommend(CURRENT_FARE, rows, CHANGE_THRESHOLD)
            take = ("cost/pax $55->$58; best stays $280 but gain vs $320 is %s "
                    "< $%d threshold -> HOLD. Cost signal, not demand signal."
                    % (usd(gain), CHANGE_THRESHOLD))
        elif kind == "pace":
            rows = evaluate(CANDIDATES, D_SOFT, SEATS_LEFT, COST_PER_PAX)
            best, cur, gain, action = recommend(CURRENT_FARE, rows, CHANGE_THRESHOLD)
            take = ("soft curve in; $280 optimal but gain %s < $%d -> HOLD $320, "
                    "set review trigger: pace < 90 by D-10 -> cut to $299."
                    % (usd(gain), CHANGE_THRESHOLD))
        print("  - %-42s %s" % (name + ":", take))
    print("  (Continuous monitoring: sub-threshold signals are logged, not acted on.)")

# ==========================================================================
# KILLER DIFFERENTIATOR -- three-way baseline comparison
# Same simulated demand scenarios for all three strategies.
# Metrics: revenue, profit, seats sold, unsold, forecast error, volatility,
#          performance under the unexpected event (S2).
# Simulation assumptions (synthetic, deterministic): two decision points
# (D-14, D-7); half-1 demand = round(D(p)/2); half-2 = remaining demand pool
# at the new price minus already-sold; the agent recognizes a shock by D-7
# (perfect shock recognition is a simplification -- real systems have
# partial observability).
# ==========================================================================
SCENARIOS = [
    {"name": "S1 festival surge",
     "model_d14": D_BASE, "true_d14": D_BASE,
     "model_d7": D_FEST, "true_d7": D_FEST, "signal_d7": "festival"},
    {"name": "S2 competitor price war",
     "model_d14": D_BASE, "true_d14": D_BASE,
     "model_d7": D_COMP, "true_d7": D_COMP, "signal_d7": "competitor $270"},
    {"name": "S3 soft market",
     "model_d14": D_SOFT, "true_d14": D_SOFT,
     "model_d7": D_SOFT, "true_d7": D_SOFT, "signal_d7": None},
]


def sim_fixed(scn):
    p = CURRENT_FARE
    s1 = min(rhu(scn["true_d14"](p) / 2), SEATS_LEFT)
    s2 = min(max(0, rhu(scn["true_d7"](p)) - s1), SEATS_LEFT - s1)
    return {"prices": [p, p], "sold": [s1, s2], "ladder": None,
            "forecast": rhu(D_BASE(CURRENT_FARE))}


def sim_rule(scn):
    p1 = CURRENT_FARE
    s1 = min(rhu(scn["true_d14"](p1) / 2), SEATS_LEFT)
    # thresholds on booking pace: hot -> +$20, cold -> -$20
    p2 = p1 + 20 if s1 >= 16 else (p1 - 20 if s1 <= 10 else p1)
    s2 = min(max(0, rhu(scn["true_d7"](p2)) - s1), SEATS_LEFT - s1)
    return {"prices": [p1, p2], "sold": [s1, s2], "ladder": None,
            "forecast": rhu(D_BASE(CURRENT_FARE))}


def sim_agentic(scn):
    # D-14: optimize on the demand-intel model; move only if gain > threshold
    rows14 = evaluate(CANDIDATES, scn["model_d14"], SEATS_LEFT, COST_PER_PAX)
    best14, cur14, gain14, _ = recommend(CURRENT_FARE, rows14, CHANGE_THRESHOLD)
    p1 = best14[0] if gain14 > CHANGE_THRESHOLD else CURRENT_FARE
    s1 = min(rhu(scn["true_d14"](p1) / 2), SEATS_LEFT)
    forecast = rhu(scn["model_d14"](CURRENT_FARE))
    forecast_h1 = rhu(scn["model_d14"](p1) / 2)

    # D-7: continuous monitoring -- re-optimize only on new signal or pace miss
    pace_ok = abs(s1 - forecast_h1) / max(forecast_h1, 1) <= 0.15
    ladder = None
    if scn["signal_d7"] is None and pace_ok:
        p2 = p1  # nothing relevant changed: hold, don't churn
        s2 = min(max(0, rhu(scn["true_d7"](p2)) - s1), SEATS_LEFT - s1)
    elif scn["signal_d7"] == "competitor $270":
        # re-evaluate options incl. the fenced fare-class ladder
        seats_rem = SEATS_LEFT - s1
        dem2 = max(0, rhu(scn["true_d7"](p1)) - s1)
        hold_c = (p1 - COST_PER_PAX) * min(dem2, seats_rem)
        lad_dem = max(0, 40 - s1)  # ladder recaptures share: 40 total demand
        n299 = min(20, lad_dem, seats_rem)
        n350 = min(max(0, lad_dem - n299), seats_rem - n299)
        lad_c = n299 * (299 - COST_PER_PAX) + n350 * (350 - COST_PER_PAX)
        thr = CHANGE_THRESHOLD * 7 / DAYS_TO_DEPARTURE
        if lad_c - hold_c > thr:
            ladder = (n299, n350)
            p2 = p1  # base held; ladder added alongside
            s2 = n299 + n350
        else:
            p2 = p1
            s2 = min(dem2, seats_rem)
    else:  # new demand signal (festival): re-optimize price
        seats_rem = SEATS_LEFT - s1
        thr = CHANGE_THRESHOLD * 7 / DAYS_TO_DEPARTURE
        best_c, best_p2, best_s2 = -1, p1, 0
        for p in CANDIDATES:
            dem2 = max(0, rhu(scn["model_d7"](p)) - s1)
            sold2 = min(dem2, seats_rem)
            c = (p - COST_PER_PAX) * sold2
            if c > best_c:
                best_c, best_p2, best_s2 = c, p, sold2
        cur_c = (p1 - COST_PER_PAX) * min(max(0, rhu(scn["model_d7"](p1)) - s1),
                                          seats_rem)
        if best_c - cur_c > thr:
            p2, s2 = best_p2, best_s2
        else:
            p2 = p1
            s2 = min(max(0, rhu(scn["model_d7"](p1)) - s1), seats_rem)
    return {"prices": [p1, p2], "sold": [s1, s2], "ladder": ladder,
            "forecast": forecast}


def strategy_totals(run_fn):
    tot_rev, tot_c, tot_sold, errs, changes, s2_profit = 0, 0, 0, [], [], None
    for i, scn in enumerate(SCENARIOS):
        r = run_fn(scn)
        s1, s2 = r["sold"]
        p1, p2 = r["prices"]
        if r["ladder"]:
            n299, n350 = r["ladder"]
            rev = BASE_REVENUE + s1 * p1 + n299 * 299 + n350 * 350
            c = ((p1 - COST_PER_PAX) * s1 + n299 * (299 - COST_PER_PAX)
                 + n350 * (350 - COST_PER_PAX))
            changes.append("fare ladder")
        else:
            rev = BASE_REVENUE + s1 * p1 + s2 * p2
            c = (p1 - COST_PER_PAX) * s1 + (p2 - COST_PER_PAX) * s2
            if p2 != p1:
                changes.append("%s%+d" % ("$", p2 - p1))
        tot_rev += rev
        tot_c += c
        tot_sold += s1 + s2
        errs.append(abs(r["forecast"] - (s1 + s2)) / max(s1 + s2, 1))
        if scn["name"].startswith("S2"):
            s2_profit = c
    return {"revenue": tot_rev, "profit": tot_c, "sold": tot_sold,
            "unsold": 3 * SEATS_LEFT - tot_sold,
            "mape": sum(errs) / len(errs),
            "changes": changes, "s2_profit": s2_profit}


def three_way_comparison():
    bar()
    print("KILLER DIFFERENTIATOR -- three-way baseline comparison")
    print("(same simulated demand scenarios; all numbers synthetic)")
    bar()
    strategies = [("fixed $320", sim_fixed),
                  ("rule-based", sim_rule),
                  ("agentic AI", sim_agentic)]
    results = [(name, strategy_totals(fn)) for name, fn in strategies]
    print("\n  strategy     total rev.  profit   sold  unsold  fcastMAPE "
          "volatility        S2 profit")
    for name, t in results:
        vol = "%d change(s)" % len(t["changes"])
        if t["changes"]:
            vol += " (%s)" % ", ".join(t["changes"])
        print("  %-11s %10s %8s %6d %7d %9.1f%%  %-17s %10s"
              % (name, usd(t["revenue"]), usd(t["profit"]), t["sold"],
                 t["unsold"], t["mape"] * 100, vol, usd(t["s2_profit"])))
    ag, fx = results[2][1], results[0][1]
    print("\n  HEADLINE: agentic profit %s vs fixed %s (+%.0f%%); agentic sold"
          % (usd(ag["profit"]), usd(fx["profit"]),
             (ag["profit"] / fx["profit"] - 1) * 100))
    print("  %d seats vs %d; forecast error %.0f%% vs %.0f%%; shock-scenario (S2)"
          % (ag["sold"], fx["sold"], ag["mape"] * 100, fx["mape"] * 100))
    print("  profit %s vs %s (fare ladder instead of a price war)."
          % (usd(ag["s2_profit"]), usd(fx["s2_profit"])))
    print("\n  HONEST CAVEAT: this simulation proves the agent beats the CHOSEN")
    print("  baselines UNDER SIMULATED ASSUMPTIONS (synthetic curves, perfect")
    print("  shock recognition by D-7). It does NOT prove it beats real airline")
    print("  revenue-management systems on real data. See README data-honesty.")


# ==========================================================================
# Main orchestrator
# ==========================================================================
def main():
    bar()
    print("AEROYIELD AI -- An Agentic AI Revenue Management System for Airlines")
    print('"the AI agent that thinks like an airline revenue manager"')
    bar()
    print("SETUP: %s | %d seats | %d booked / %d remaining | D-%d | fare %s"
          % (ROUTE, SEATS_TOTAL, SEATS_BOOKED, SEATS_LEFT,
             DAYS_TO_DEPARTURE, usd(CURRENT_FARE)))
    print("DATA: SYNTHETIC SAMPLE DATA -- public fares are not demand,")
    print("      inventory, or revenue. Details in README data-honesty.")
    print("MODE: SIMULATION / approval workflow -- never a live booking system.")

    live_scenario()
    print()
    twist_scenario()
    print()
    scenario_simulations()
    print()
    three_way_comparison()

    print()
    bar()
    print("SUMMARY -- the agent observed, analyzed, decided, acted (staged),")
    print("and set up verification; re-evaluated instead of auto-following the")
    print("competitor; and beat fixed + rule-based baselines on profit (+%d%%)"
          % 23)
    print("under simulated assumptions. Every number above is reproducible:")
    print("run it again -- byte-identical.")
    bar()


if __name__ == "__main__":
    main()
