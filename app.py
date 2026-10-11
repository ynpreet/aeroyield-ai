#!/usr/bin/env python3
"""AeroYield AI -- localhost web UI (stdlib only).

Run:  python3 app.py   then open http://localhost:8004
Serves a guided, personalized tour of demo.py (the tested artifact --
demo.py is never modified here; it is only imported as a module and its
canned subprocess run is unchanged).
"""

import contextlib
import http.server
import io
import json
import mimetypes
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

HOST = "127.0.0.1"
PORT = 8004
HERE = Path(__file__).resolve().parent
DEMO_PY = HERE / "demo.py"

sys.path.insert(0, str(HERE))
import demo as DEMO  # the tested artifact: imported, never modified

# ---- personalized triage (app.py only; demo.py untouched) ----
# Red-flag patterns are checked FIRST -- any match escalates to URGENT and
# bypasses routine scoring entirely. This demo is not medical advice.

_CRITICAL_PATTERNS = [
    (r"\bcancer\b", "cancer"),
    (r"\btumou?rs?\b", "tumor"),
    (r"(4th|fourth)\s*stage|stage\s*(4|iv)\b", "advanced stage (stage 4/IV)"),
    (r"\bmetastatic\b", "metastatic disease"),
    (r"heart attack", "heart attack"),
    (r"\bstroke\b", "stroke"),
    (r"chest pain", "chest pain"),
    (r"difficulty breathing|can'?t breathe|shortness of breath|trouble breathing|can not breathe", "breathing difficulty"),
    (r"\bbleeding\b", "bleeding"),
    (r"\bseizure\b", "seizure"),
    (r"suicid|self-?harm|kill myself|end my life|end it all", "self-harm risk"),
    (r"\boverdose\b", "overdose"),
    (r"anaphyla", "anaphylaxis"),
]

_WELLNESS_PATTERNS = [
    r"\bi feel fine\b",
    r"\bfeeling (fine|great|good|healthy)\b",
    r"\bhealthy\b",
    r"\bno conditions\b",
    r"\bnone\b",
    r"\bnothing wrong\b",
    r"\ball good\b",
]

# (aliases, canonical display name, risk weight) -- checked in order.
_CONDITION_MAP = [
    (("type 1 diabetes", "t1d", "diabetes type 1"), "Type 1 Diabetes", 25),
    (("type 2 diabetes", "t2d", "diabetes type 2"), "Type 2 Diabetes", 20),
    (("diabetes",), "Type 2 Diabetes", 20),
    (("hypertension", "high blood pressure", "hbp", "htn", "high bp"), "Hypertension", 15),
    (("heart disease", "coronary", "heart failure", "chf"), "Heart Disease", 20),
    (("kidney disease", "ckd", "chronic kidney", "renal failure"), "Chronic Kidney Disease", 15),
    (("copd", "emphysema", "chronic bronchitis"), "COPD", 15),
    (("asthma",), "Asthma", 10),
    (("depression", "depressive"), "Depression", 10),
    (("anxiety",), "Anxiety", 8),
    (("hyperlipidemia", "high cholesterol", "cholesterol"), "High Cholesterol", 10),
    (("arthritis", "osteoarthritis", "rheumatoid"), "Arthritis", 5),
    (("migraine",), "Migraine", 5),
    (("obesity", "obese", "overweight"), "Obesity", 10),
    (("dementia", "alzheimer"), "Dementia", 10),
    (("seasonal allergies", "hay fever", "allergies", "allergy"), "Seasonal Allergies", 3),
    (("knee surgery", "hip surgery", "surgery", "post-surgery", "post surgery",
      "recovering from", "recovery from"), "Post-Surgery Recovery", 8),
    (("smoking", "smoker", "tobacco", "quit smoking", "vaping", "nicotine"), "Smoking Cessation", 10),
]

_HIGH_TIER_AT = 50
_MEDIUM_TIER_AT = 25

# Safe, general self-management information for recognized conditions that have
# no playbook entry in demo.py. General information only -- never prescriptive.
_EXTRA_SECTIONS = {
    "Type 1 Diabetes": [
        "Check blood sugar as your doctor advised and log the readings.",
        "Take insulin exactly as prescribed; never skip or adjust doses on your own.",
        "Know the signs of low blood sugar and keep fast-acting glucose nearby.",
    ],
    "Heart Disease": [
        "Take heart medications exactly as prescribed.",
        "Note any chest discomfort, unusual shortness of breath, or swelling -- report promptly.",
        "Ask your doctor what activity level is safe for you.",
    ],
    "COPD": [
        "Avoid smoke and strong fumes; make sure your inhaler technique is right.",
        "Notice changes in breathlessness or mucus -- report flare-ups early.",
        "Ask about pulmonary rehab and vaccinations (flu, pneumonia).",
    ],
    "Asthma": [
        "Keep your reliever inhaler where you can reach it.",
        "Learn your personal triggers and note them.",
        "Follow the asthma action plan you made with your doctor.",
    ],
    "Depression": [
        "Stay connected -- tell someone you trust how you are feeling.",
        "Keep a regular sleep schedule; daylight and gentle movement help.",
        "If thoughts of self-harm arise, call or text 988 (US) right away.",
    ],
    "Anxiety": [
        "Practice slow breathing when anxiety spikes; note what triggers it.",
        "Keep caffeine and alcohol in check -- both can worsen anxiety.",
        "If anxiety interferes with daily life, ask your doctor about options.",
    ],
    "High Cholesterol": [
        "Take cholesterol medication as prescribed, if any.",
        "Favor vegetables, whole grains, and lean proteins; limit fried foods.",
        "Recheck lipids on the schedule your doctor sets.",
    ],
    "Arthritis": [
        "Keep joints moving with gentle, doctor-approved activity.",
        "Use heat or cold for stiffness as advised.",
        "Report new swelling or hot-feeling joints to your care team.",
    ],
    "Migraine": [
        "Track attacks: when they start, how long they last, possible triggers.",
        "Rest in a dark, quiet room during an attack if you can.",
        "If attacks are frequent or suddenly different, tell your doctor.",
    ],
    "Obesity": [
        "Aim for small, steady changes in eating and activity -- not crash diets.",
        "Track weight weekly, same time of day.",
        "Ask your doctor about programs covered by your plan.",
    ],
    "Dementia": [
        "Keep a consistent daily routine; labels on rooms and drawers help.",
        "Caregivers: take breaks and ask about respite support -- burnout is real.",
        "Report sudden confusion changes promptly; they can signal something treatable.",
    ],
    "Seasonal Allergies": [
        "Check local pollen counts and limit outdoor time on high days.",
        "Shower and change clothes after being outside.",
        "If breathing is ever affected, treat it as urgent -- not just allergies.",
    ],
    "Post-Surgery Recovery": [
        "Follow your surgeon's wound-care and activity instructions exactly.",
        "Watch for redness, swelling, fever, or unusual pain -- report promptly.",
        "Do your prescribed rehab exercises even when they are uncomfortable.",
    ],
    "Smoking Cessation": [
        "Set a quit date and tell someone about it.",
        "Ask your doctor about quit aids covered by your plan.",
        "Cravings pass in minutes -- have a walk or a glass of water ready.",
    ],
}

_GENERIC_STEPS = [
    "Keep a simple symptom diary: what you feel, when, and what seems to help.",
    "Keep an up-to-date list of medications and bring it to every appointment.",
    "If symptoms worsen or worry you, contact your care team promptly.",
]

_WELLNESS_STEPS = [
    "Keep your annual checkup -- prevention beats treatment.",
    "Stay current on age-appropriate screenings (your doctor can list them).",
    "If anything changes, come back and tell us -- we will triage you then.",
]

_URGENT_HANDOFF_STEPS = [
    "Contact your doctor, specialist, or care team right away -- today, not next week.",
    "If symptoms are severe, new, or getting worse, call emergency services (911 in the US) or go to urgent care now.",
    "Do not wait for an email or app message for anything urgent -- call.",
    "Bring your medication list and recent test results to every appointment.",
]


def _parse_phrases(raw):
    """Split free text into condition phrases. Never iterate characters."""
    phrases = []
    for part in re.split(r"[;,]", raw.lower()):
        for q in re.split(r"\s+and\s+|\s*&\s*|\s+plus\s+", part):
            q = q.strip(" .")
            if q:
                phrases.append(q)
    seen, deduped = set(), []
    for q in phrases:
        if q not in seen:
            seen.add(q)
            deduped.append(q)
    return deduped


def _map_phrase(phrase):
    for aliases, display, weight in _CONDITION_MAP:
        for a in aliases:
            if a in phrase:
                return display, weight
    return None, 0


def _build_plan(display_names, tier, unknown):
    plan = []
    for dn in display_names:
        steps = DEMO.CONDITION_PLAYBOOKS.get(dn) or _EXTRA_SECTIONS.get(dn)
        if steps:
            plan.append({"condition": dn, "steps": list(steps)})
    if tier == "HIGH":
        plan.append({"condition": "High-risk follow-up",
                     "steps": ["Care manager will check in within 7 days.",
                               "If any symptoms worsen, call the clinic same-day."]})
    elif tier == "MEDIUM":
        plan.append({"condition": "Routine follow-up",
                     "steps": ["Care manager will check in within 30 days."]})
    if not plan or unknown or tier == "NEEDS REVIEW":
        plan.append({"condition": "General guidance (confirm with your care team)",
                     "steps": list(_GENERIC_STEPS)})
    return plan


def _print_pipeline(name, email, chan, display_names, tier, score, reasons, plan):
    patient = {
        "id": "WEB-001",
        "name": name,
        "age": 50,
        "email": email,
        "conditions": display_names,
        "last_visit": "not provided",
        "preferred_channel": chan,
        "risk_factors": {"from_user_input": True},
    }
    triage = {"tier": tier, "score": score, "reasons": reasons}
    print(f"[AuthAgent]    Login verified: {email}")
    print(f"[TriageAgent]  Scoring risk for {name} (conditions: {', '.join(display_names)})...")
    print(f"[TriageAgent]  Score {score} -> tier {tier}")
    for r in reasons:
        print(f"               - {r}")
    channel = DEMO.channel_agent(patient, triage)
    print(f"[ChannelAgent] Selected channel: {channel.upper()} (patient preference: {chan})")
    print(f"[CarePlanAgent] Assembled {len(plan)} care-plan section(s)")
    message = DEMO.message_agent(patient, triage, plan, channel)
    print(f"[MessageAgent] Rendered {channel.upper()} message:")
    print()
    print("-" * 72)
    print(message)
    print("-" * 72)

def _capture_canned():
    """Run the canned demo exactly as before (subprocess), capture stdout."""
    proc = subprocess.run(
        [sys.executable, str(DEMO_PY)],
        cwd=str(HERE),
        capture_output=True,
        text=True,
        timeout=600,
    )
    return proc.stdout or proc.stderr

def _capture_fn(fn, params):
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            return fn(params)
    except Exception as exc:  # never crash the page on a bad input
        return "[web-ui] The personalized run hit an error and stopped safely.\n%s: %s" % (type(exc).__name__, exc)

# _capture_custom: personalized handlers may return a dict carrying a follow-up decision.
def _capture_custom(fn, params):
    try:
        res = fn(params)
    except Exception as exc:  # never crash the page on a bad input
        return {"output": "[web-ui] The personalized run hit an error and stopped safely.", "decision": None}
    if isinstance(res, dict):
        res.setdefault("decision", None)
        return res
    return {"output": res, "decision": None}

# ---- personalized run: input handling lives in app.py; demo.py untouched ----
import hashlib

_AERO_AIRPORTS = [
    ("SFO", "San Francisco"),
    ("LAX", "Los Angeles"),
    ("JFK", "New York (JFK)"),
    ("BOS", "Boston"),
    ("ORD", "Chicago O'Hare"),
    ("DFW", "Dallas/Fort Worth"),
    ("MIA", "Miami"),
    ("SEA", "Seattle"),
    ("DEN", "Denver"),
    ("ATL", "Atlanta"),
    ("IAD", "Washington DC (Dulles)"),
    ("LAS", "Las Vegas"),
]
_AERO_AIRPORT_SET = {c for c, _ in _AERO_AIRPORTS}
_AERO_AIRPORT_NAME = dict(_AERO_AIRPORTS)

_AERO_SCEN_META = {
    "baseline": "Baseline (no event)",
    "festival": "Festival announced",
    "competitor": "Competitor drops fare",
    "fuel": "Fuel price spike",
    "soft": "Bookings below pace",
}
_AERO_CONF_BASE = {"baseline": 0.66, "festival": 0.74, "competitor": 0.70,
                   "fuel": 0.62, "soft": 0.68}
_AERO_SEATS_TOTAL = 180
_AERO_CHANGE_THRESHOLD_REF = 750  # at the $320 reference fare


def _aero_seed(dep, arr):
    return int(hashlib.sha256(("%s>%s" % (dep, arr)).encode("utf-8")).hexdigest(), 16)


def _aero_params(dep, arr):
    # Deterministic route parameters derived from the airport pair.
    # Same pair -> same numbers on every run, on every machine.
    h = _aero_seed(dep, arr)
    base_fare = 180 + (h % 27) * 10            # 180..440, step $10
    booked = 90 + ((h >> 9) % 51)              # 90..140
    return {
        "base_fare": base_fare,
        "booked": booked,
        "seats_left": _AERO_SEATS_TOTAL - booked,   # 40..90
        "demand_scale": 0.80 + ((h >> 17) % 41) / 100.0,  # 0.80..1.20
        "seed": h,
    }


def _aero_curve(base_fare, demand_scale, scenario):
    # Base curve mirrors demo.py BASE_ANCHORS shape {280:35, 320:28, 360:21,
    # 400:14} -- volume beats price when demand is elastic -- shifted so the
    # middle anchor sits at the route's current fare.
    anchors = {
        base_fare - 40: 35 * demand_scale,
        base_fare: 28 * demand_scale,
        base_fare + 40: 21 * demand_scale,
        base_fare + 80: 14 * demand_scale,
    }
    if scenario == "festival":
        # inelastic event segment: +24 must-fly pax at every fare
        anchors = {f: d + 24 for f, d in anchors.items()}
    elif scenario == "competitor":
        # rival undercuts: shoppers buy down, curve shifts down
        anchors = {f: d * 0.72 for f, d in anchors.items()}
    elif scenario == "soft":
        # soft market: demand scaled down across the curve
        anchors = {f: d * 0.65 for f, d in anchors.items()}
    # fuel: cost signal only -- demand curve untouched
    return DEMO.make_curve(anchors)


def _aero_signals(dep, arr, scenario, p, cost, threshold):
    route = "%s\u2192%s" % (dep, arr)
    load = round(100.0 * p["booked"] / _AERO_SEATS_TOTAL, 1)
    cf = p["base_fare"]
    if scenario == "baseline":
        return [
            "Base case on %s: %d of 180 seats sold (%s%% load factor), %d seats left to price."
            % (route, p["booked"], load, p["seats_left"]),
            "Demand here is price-sensitive: the engine tests every fare from %s to %s."
            % (DEMO.usd(cf - 40), DEMO.usd(cf + 80)),
            "No new signals \u2014 the agent prices the base demand curve and holds unless a move clears %s."
            % DEMO.usd(threshold),
        ]
    if scenario == "festival":
        return [
            "Event segment on %s: +24 must-fly passengers added to demand at every fare." % route,
            "Event travelers are price-insensitive (elasticity \u2248 -0.3 vs leisure -1.4) \u2014 volume barely drops as fares rise.",
            "The engine still has to earn the move: it only changes the fare if expected profit clears %s."
            % DEMO.usd(threshold),
        ]
    if scenario == "competitor":
        rival = cf - 50
        return [
            "Rival filed %s on %s \u2014 verified comparable (dates, baggage, bookable, inventory)."
            % (DEMO.usd(rival), route),
            "Shoppers buy down to the rival: our demand at %s falls. Matching blindly would torch margin."
            % DEMO.usd(cf),
            "The agent re-evaluates every fare on the shifted curve instead of auto-following.",
            "Freshness caveat: re-shop the rival fare before approving any move \u2014 a stale %s "
            "(sold out, repriced, unbookable) is a mirage fare, not a signal."
            % DEMO.usd(rival),
        ]
    if scenario == "fuel":
        return [
            "Jet fuel spike: cost per passenger %s \u2192 %s on %s."
            % (DEMO.usd(55), DEMO.usd(cost), route),
            "A cost signal, not a demand signal \u2014 it trims margin; it does not mean fares rise.",
            "Contribution-margin effect: margin per seat at %s falls %s \u2192 %s (\u2212%s/seat) "
            "on unchanged demand \u2014 the whole hit is cost, not volume."
            % (DEMO.usd(cf), DEMO.usd(cf - 55), DEMO.usd(cf - cost), DEMO.usd(cost - 55)),
            "Watch whether the fare moves at all: the engine only acts if profit clears %s."
            % DEMO.usd(threshold),
        ]
    return [
        "Bookings running below pace on %s \u2014 soft demand across the curve (x0.65)." % route,
        "The engine checks whether any fare clears the %s human-approval bar." % DEMO.usd(threshold),
        "Sub-threshold signals are logged, not acted on \u2014 no churn for churn's sake.",
    ]


def _aero_score(dep, arr, scenario, fuel_pct=10.0, seats_left=None):
    p = _aero_params(dep, arr)
    p = dict(p)  # per-run copy: the seats_left override below must not leak
    try:
        seats_left = int(seats_left)
    except (TypeError, ValueError):
        seats_left = None
    if seats_left is None:
        seats_left = p["seats_left"]
    p["seats_left"] = max(0, min(_AERO_SEATS_TOTAL, seats_left))
    cf = p["base_fare"]
    try:
        fuel_pct = float(fuel_pct)
    except (TypeError, ValueError):
        fuel_pct = 10.0
    fuel_pct = max(0.0, fuel_pct)
    # Cost mapping kept consistent with demo.py: fuel +10% -> cost/pax +$3
    # (fuel is ~1/4 of the variable cost stack), so +1pp fuel -> +$0.25/pax.
    cost = 55.0 + (0.25 * fuel_pct if scenario == "fuel" else 0.0)
    curve = _aero_curve(cf, p["demand_scale"], scenario)
    candidates = [cf - 40, cf - 20, cf, cf + 30, cf + 40, cf + 60, cf + 80]
    threshold = max(250, int(round(_AERO_CHANGE_THRESHOLD_REF * cf / 320.0)))
    rows = DEMO.evaluate(candidates, curve, p["seats_left"], cost)
    best, cur, gain, action = DEMO.recommend(cf, rows, threshold)
    confidence = round(min(0.97, max(0.30,
        _AERO_CONF_BASE[scenario] + (((p["seed"] >> 25) % 9) - 4) / 100.0)), 2)
    return {
        "dep": dep, "arr": arr,
        "dep_name": _AERO_AIRPORT_NAME[dep], "arr_name": _AERO_AIRPORT_NAME[arr],
        "route": "%s \u2192 %s" % (dep, arr),
        "scenario": scenario, "scenario_label": _AERO_SCEN_META[scenario],
        "current_fare": cf, "booked": p["booked"], "seats_left": p["seats_left"],
        "load_pct": round(100.0 * p["booked"] / _AERO_SEATS_TOTAL, 1),
        "cost_per_pax": cost, "threshold": threshold,
        "candidates": candidates,
        "recommended_fare": best[0], "action": action,
        "gain": int(round(gain)), "confidence": confidence,
        "signals": _aero_signals(dep, arr, scenario, p, cost, threshold),
        "rows": [(r[0], round(r[1], 1), r[2], int(round(r[3])), int(round(r[4])))
                 for r in rows],
    }


def _aero_table_text(v):
    lines = ["  fare  D(p) dem.  sold  incr. rev.  contrib."]
    for fare, dem, sold, rev, contrib in v["rows"]:
        lines.append("  %4s  %9.1f  %4d  %10s  %8s"
                     % (DEMO.usd(fare), dem, sold, DEMO.usd(rev), DEMO.usd(contrib)))
    lines.append("  (revenue already banked: %s; every figure synthetic)"
                 % DEMO.usd(v["booked"] * v["current_fare"]))
    return "\n".join(lines)


def run_custom(params):
    if not isinstance(params, dict):
        params = {}
    dep = params.get("dep") or "SFO"
    dep = dep.strip().upper() if isinstance(dep, str) else "SFO"
    arr = params.get("arr") or "BOS"
    arr = arr.strip().upper() if isinstance(arr, str) else "BOS"
    if dep not in _AERO_AIRPORT_SET:
        dep = "SFO"
    if arr not in _AERO_AIRPORT_SET:
        arr = "BOS"
    scenario = params.get("scenario") or "baseline"
    if not isinstance(scenario, str) or scenario not in _AERO_SCEN_META:
        scenario = "baseline"
    if dep == arr:
        return {"output": "", "decision": None, "verdict": None,
                "error": "Pick two different airports \u2014 even our agent can't sell %s\u2192%s."
                         % (dep, arr)}
    fuel_pct = params.get("fuel_pct", 10)        # % fuel-price rise (T2: pass 40)
    seats_left = params.get("seats_left", None)  # int override (T3: pass 5)
    v = _aero_score(dep, arr, scenario, fuel_pct=fuel_pct, seats_left=seats_left)
    if scenario != "baseline":
        b = _aero_score(dep, arr, "baseline", seats_left=seats_left)
        v["baseline"] = {"recommended_fare": b["recommended_fare"],
                         "action": b["action"], "gain": b["gain"]}
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        print("%s -- %s" % (v["route"], v["scenario_label"]))
        print("Current fare %s, %d seats left, approval threshold %s"
              % (DEMO.usd(v["current_fare"]), v["seats_left"], DEMO.usd(v["threshold"])))
        hold_fare = (v["current_fare"] if v["action"] == "HOLD"
                     else v["recommended_fare"])
        verb = "CHANGE to" if v["action"] == "CHANGE" else "HOLD at"
        print("Verdict: %s %s -- expected gain %s, confidence %s"
              % (verb, DEMO.usd(hold_fare),
                 DEMO.usd(v["gain"]), v["confidence"]))
        for s in v["signals"]:
            print(" - " + s)
        print("NOTE: all figures are synthetic/sample data -- no fare moves without")
        print("human approval, and rival fares must be re-verified fresh first.")
    return {"output": out.getvalue(), "decision": None,
            "verdict": v, "table": _aero_table_text(v)}


PAGE = '<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n<title>AeroYield AI &mdash; Live Demo</title>\n<style>\n:root{\n  --bg:#0b1220; --bg2:#0e1626; --panel:#131e33; --panel2:#182742;\n  --ink:#eaf0f9; --muted:#9db0c9; --faint:#6b7f99;\n  --teal:#2dd4bf; --teal-dim:rgba(45,212,191,.12);\n  --accent:#5aa9ff; --warn:#fbbf24; --danger:#f87171; --ok:#34d399;\n  --line:#233451; --radius:14px;\n}\n*{box-sizing:border-box}\nbody{margin:0;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;\n  background:var(--bg);color:var(--ink);line-height:1.6}\nheader{background:linear-gradient(135deg,#0a2540 0%,#0e3a5c 60%,#0b4f4a 100%);\n  padding:42px 32px 34px;border-bottom:1px solid var(--line)}\n.wrap{max-width:1060px;margin:0 auto}\nheader h1{margin:0 0 8px;font-size:30px;letter-spacing:-.01em}\nheader .sub{margin:0;color:#c8d6ea;font-size:16px;max-width:800px}\n.badge{display:inline-block;margin-top:14px;font-size:11.5px;letter-spacing:.1em;\n  text-transform:uppercase;color:#06281f;background:var(--teal);\n  padding:5px 14px;border-radius:999px;font-weight:800}\nmain{padding:8px 32px 48px}\nsection.card{background:var(--panel);border:1px solid var(--line);\n  border-radius:var(--radius);padding:26px 28px;margin:26px 0}\nsection.card h2{margin:0 0 12px;font-size:18px;color:var(--teal)}\nsection.card h2 .n{display:inline-block;width:28px;height:28px;border-radius:50%;\n  background:var(--teal-dim);border:1px solid var(--teal);color:var(--teal);\n  text-align:center;line-height:26px;font-size:14px;margin-right:10px}\nsection.card p{margin:0 0 12px;color:#d5e0f1;font-size:15.5px}\nsection.card p:last-child{margin-bottom:0}\n.watch{list-style:none;margin:6px 0 0;padding:0}\n.watch li{position:relative;padding:8px 0 8px 30px;color:#d5e0f1;font-size:15px;\n  border-bottom:1px dashed var(--line)}\n.watch li:last-child{border-bottom:0}\n.watch li::before{content:"\\25b8";position:absolute;left:8px;color:var(--teal);font-weight:700}\nlabel.f{display:block;margin:14px 0 6px;font-size:13px;font-weight:700;\n  letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}\ninput[type=text],input[type=number],select,textarea{\n  width:100%;background:var(--bg2);border:1px solid var(--line);color:var(--ink);\n  border-radius:10px;padding:11px 14px;font-size:15px;font-family:inherit}\ntextarea{min-height:76px;resize:vertical}\ninput:focus,select:focus,textarea:focus{outline:none;border-color:var(--teal)}\n.row2{display:grid;grid-template-columns:1fr 1fr;gap:14px}\n@media(max-width:700px){.row2{grid-template-columns:1fr}}\n.btnrow{display:flex;gap:14px;align-items:center;margin-top:20px;flex-wrap:wrap}\nbutton.run{background:linear-gradient(135deg,#14b8a6,#0d9488);border:0;\n  color:#04211c;font-weight:800;font-size:17px;padding:15px 34px;\n  border-radius:12px;cursor:pointer;box-shadow:0 6px 22px rgba(45,212,191,.25)}\nbutton.run:hover{filter:brightness(1.08)}\nbutton.run:disabled{opacity:.45;cursor:default;box-shadow:none}\nbutton.ghost{background:transparent;border:1px solid var(--teal);color:var(--teal);\n  font-weight:700;font-size:15px;padding:13px 26px;border-radius:12px;cursor:pointer}\nbutton.ghost:hover{background:var(--teal-dim)}\nbutton.ghost:disabled{opacity:.45;cursor:default}\n.hint{color:var(--muted);font-size:13.5px}\n.spinner{display:none;align-items:center;gap:10px;color:var(--muted);font-size:14px;margin-top:14px}\n.spinner.show{display:flex}\n.dot{width:12px;height:12px;border-radius:50%;background:var(--teal);\n  animation:pulse 1s infinite ease-in-out}\n@keyframes pulse{0%,100%{transform:scale(.6);opacity:.5}50%{transform:scale(1.2);opacity:1}}\n#output{display:none;margin-top:6px}\n#output.show{display:block}\n.out{background:#0a0f1c;border:1px solid var(--line);border-radius:12px;\n  padding:20px 22px;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;\n  font-size:13px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word;\n  max-height:640px;overflow:auto;color:#c9d6ea}\n.sechead{color:var(--accent);font-weight:800;margin:18px 0 2px;font-size:13.5px}\n.sechead:first-child{margin-top:0}\n.seccap{background:var(--teal-dim);border-left:3px solid var(--teal);\n  padding:8px 12px;margin:4px 0 12px;border-radius:0 8px 8px 0;\n  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;\n  font-size:13.5px;color:#bfe9e2}\n.tok-orch{color:var(--accent);font-weight:700}\n.tok-tool{color:var(--ok);font-weight:700}\n.tok-guard{color:var(--warn);font-weight:700}\n.tok-mem{color:#c084fc;font-weight:700}\n#takeaways{display:none}\n#takeaways.show{display:block}\n.take{background:rgba(52,211,153,.07);border:1px solid rgba(52,211,153,.4);\n  border-radius:var(--radius);padding:22px 26px;margin:26px 0}\n.take h2{color:var(--ok);margin:0 0 10px;font-size:18px}\n.take ul{margin:0;padding-left:20px}\n.take li{margin:8px 0;color:#d5e0f1;font-size:15px}\ntable.dec{width:100%;border-collapse:collapse;margin-top:12px;font-size:14px}\ntable.dec th{background:var(--panel2);color:var(--teal);text-align:left;\n  padding:10px 12px;font-size:12px;letter-spacing:.06em;text-transform:uppercase;\n  border-bottom:1px solid var(--line)}\ntable.dec td{padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}\n.pill{display:inline-block;padding:3px 12px;border-radius:999px;font-weight:800;font-size:12px}\n.pill.v{background:var(--ok);color:#04281c}\n.pill.s{background:var(--faint);color:#0b1220}\nfooter{padding:26px 32px 40px;color:var(--faint);font-size:13.5px;text-align:center}\nfooter a{color:var(--teal);text-decoration:none}\nfooter a:hover{text-decoration:underline}\ndetails.raw{margin-top:14px}\ndetails.raw summary{cursor:pointer;color:var(--muted);font-size:13.5px}\n/* --- care revamp: why-section + sidebar layout --- */\n.care-layout{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:26px;align-items:start}\n.care-main{min-width:0}\n.care-sidebar{position:sticky;top:20px;min-width:0}\n@media(max-width:960px){.care-layout{grid-template-columns:1fr}.care-sidebar{position:static}}\n.side-card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:20px;margin-bottom:20px}\n.side-card h3{margin:0 0 10px;font-size:15px;color:var(--teal)}\n.side-vid{margin-bottom:18px}\n.side-vid:last-child{margin-bottom:0}\n.side-vid iframe{width:100%;aspect-ratio:16/9;border:0;border-radius:10px;display:block;background:#000}\n.side-vid p{font-size:13px;color:var(--muted);margin:8px 0 0;line-height:1.5}\n.why-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;margin:16px 0}\n@media(max-width:700px){.why-grid{grid-template-columns:1fr}}\n.why-grid figure{margin:0}\n.why-grid img{width:100%;aspect-ratio:16/10;object-fit:cover;border-radius:10px;border:1px solid var(--line);display:block;background:#0a0f1c}\n.why-grid figcaption{font-size:12.5px;color:var(--muted);margin-top:6px;line-height:1.5}\n.chips{display:flex;flex-wrap:wrap;gap:8px;margin:8px 0 4px}\n.chip{background:var(--panel2);border:1px solid var(--teal);color:var(--teal);font-size:13px;padding:7px 14px;border-radius:999px;cursor:pointer;font-family:inherit;line-height:1.4}\n.chip:hover{background:var(--teal-dim)}\n.chal{list-style:none;margin:10px 0 0;padding:0}\n.chal li{position:relative;padding:7px 0 7px 28px;color:#d5e0f1;font-size:15px}\n.chal li::before{content:"!";position:absolute;left:9px;color:var(--warn);font-weight:800}\n\n\n.blog-list{list-style:none;margin:0;padding:0}\n.blog-list li{margin:0 0 14px;padding-bottom:14px;border-bottom:1px dashed var(--line)}\n.blog-list li:last-child{margin-bottom:0;padding-bottom:0;border-bottom:0}\n.blog-list a{color:var(--teal);font-weight:700;font-size:14.5px;text-decoration:none}\n.blog-list a:hover{text-decoration:underline}\n.blog-list span{display:block;font-size:13px;color:var(--muted);margin-top:3px;line-height:1.5}</style>\n</head>\n<body>\n<header><div class="wrap">\n  <h1>AeroYield AI</h1>\n  <p class="sub">The AI that thinks like an airline revenue manager — SFO to Boston, 180 seats, 14 days out.</p>\n</div></header>\n<main><div class="wrap care-layout">\n<div class="care-main">\n<section class="card" id="why">\n<h2><span class="n">&#9733;</span>Why this matters in real life</h2>\n<p>An empty airline seat at takeoff is money lost forever &mdash; you cannot put it back on the shelf and sell it tomorrow. Economists call this <i>perishable inventory</i>, and it is the defining fact of the airline business.</p>\n<p>Airlines have practiced revenue management for decades: selling the right seat to the right customer at the right price, adjusting continuously as departure approaches. Price too low and you leave money on the table; price too high and you fly empty.</p>\n<p><b>What changed:</b> it used to be analysts with spreadsheets checking a few times a day. Now an agent can watch demand signals, competitor fares, and fuel costs <i>continuously</i> &mdash; and re-price in minutes when a festival is announced or a rival drops its fare. This demo is that agent, with its reasoning on display. Pick any route above and fire an event at it.</p>\n<div class="why-grid">\n<figure><img src="/assets/img/wing-sunset.svg" alt="Airplane wing at sunset" loading="lazy"><figcaption>Above the clouds: every seat is a ticking clock.</figcaption></figure>\n<figure><img src="/assets/img/takeoff.svg" alt="Airplane taking off" loading="lazy"><figcaption>At pushback, unsold inventory becomes worthless.</figcaption></figure>\n<figure><img src="/assets/img/terminal.svg" alt="Travelers in an airport terminal" loading="lazy"><figcaption>Thousands of pricing decisions, every day, per route.</figcaption></figure>\n</div>\n<p><b>Why this kind of agent helps:</b></p>\n<ul class="watch">\n<li>Reacts to events the moment they happen &mdash; not at the next analyst review</li>\n<li>Shows its work: every price move comes with signals, expected gain, and confidence</li>\n<li>Never touches a live booking system &mdash; it stages to an approval queue, like the real job</li>\n</ul>\n</section>\n\n<section class="card" id="story">\n  <h2><span class="n">1</span>The story</h2>\n  <p>You own the pricing for one flight: San Francisco to Boston, <b>180 seats, 120 already sold, 14 days to departure, current fare $320</b>. Every day you must decide: hold, raise, or cut — while festivals get announced, competitors move, and fuel prices jump.</p>\n<p>This demo runs your pricing desk as an agent. Three intelligence tools (demand signals, competitor fares, costs) feed a pricing engine that evaluates every candidate fare for expected <b>profit</b> — then stages the change for a human to approve. It never writes to a booking system. And watch the counterintuitive lesson first: <b>$280 beats $400</b> on expected revenue, because volume wins when demand is elastic.</p>\n</section>\n\n<section class="card" id="watch">\n  <h2><span class="n">2</span>What to watch for</h2>\n  <ul class="watch">\n<li>Watch the engine table: the same demand curve priced from $280 to $400 — and why the cheapest fare can win.</li>\n<li>Three events hit at once (festival, booking pace, competitor moves). Watch which signals the agent acts on — and which it deliberately ignores.</li>\n<li>The twist: a competitor drops to $270. The agent does <b>not</b> blindly follow — watch it re-evaluate.</li>\n<li>The finale: fixed pricing vs. rule-based vs. agentic AI on identical scenarios. The numbers decide.</li>\n  </ul>\n</section>\n\n\n<style>\n.verdict{background:linear-gradient(135deg,#0e2a4a,#0b4f4a);border:1px solid var(--teal);\n  border-radius:14px;padding:22px 24px;margin-top:18px}\n.verdict .v-route{font-size:12.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}\n.verdict .v-scen{display:inline-block;margin-left:10px;background:var(--teal-dim);\n  border:1px solid var(--teal);color:var(--teal);padding:2px 12px;border-radius:999px;\n  font-size:12px;letter-spacing:.04em;text-transform:none}\n.verdict .v-main{font-size:24px;font-weight:800;margin:10px 0 4px}\n.verdict .v-main .chg{color:var(--teal)}\n.verdict .v-main .hld{color:var(--warn)}\n.verdict .v-stats{color:#c8d6ea;font-size:15px;margin-bottom:6px}\n.verdict ul.v-signals{margin:8px 0 0;padding-left:20px;color:#d5e0f1;font-size:14.5px}\n.verdict ul.v-signals li{margin:6px 0}\n.verdict .v-base{background:rgba(0,0,0,.28);border-radius:10px;padding:10px 14px;\n  margin-top:12px;font-size:14px;color:#c8d6ea}\n.verdict details{margin-top:12px}\n.verdict details summary{cursor:pointer;color:var(--muted);font-size:13.5px}\n.verdict-err{background:rgba(248,113,113,.08);border:1px solid var(--danger);\n  border-radius:14px;padding:18px 22px;margin-top:18px;color:#fecaca;font-size:15px}\n</style>\n<section class="card" id="tryown">\n  <h2><span class="n">✎</span>Try your own — price any route</h2>\n  <p>You run the pricing desk for <b>12 airports — 132 routes</b>. Pick a route, price it, then fire an event on it and watch the engine re-price <b>before / after</b> against the baseline.</p>\n  <div class="row2">\n    <div>\n      <label class="f" for="a_dep">From (departure)</label>\n      <select id="a_dep">\n        <option value="SFO" selected>San Francisco (SFO)</option>\n        <option value="LAX">Los Angeles (LAX)</option>\n        <option value="JFK">New York (JFK)</option>\n        <option value="BOS">Boston (BOS)</option>\n        <option value="ORD">Chicago O\'Hare (ORD)</option>\n        <option value="DFW">Dallas/Fort Worth (DFW)</option>\n        <option value="MIA">Miami (MIA)</option>\n        <option value="SEA">Seattle (SEA)</option>\n        <option value="DEN">Denver (DEN)</option>\n        <option value="ATL">Atlanta (ATL)</option>\n        <option value="IAD">Washington DC (IAD)</option>\n        <option value="LAS">Las Vegas (LAS)</option>\n      </select>\n    </div>\n    <div>\n      <label class="f" for="a_arr">To (arrival)</label>\n      <select id="a_arr">\n        <option value="SFO">San Francisco (SFO)</option>\n        <option value="LAX">Los Angeles (LAX)</option>\n        <option value="JFK">New York (JFK)</option>\n        <option value="BOS" selected>Boston (BOS)</option>\n        <option value="ORD">Chicago O\'Hare (ORD)</option>\n        <option value="DFW">Dallas/Fort Worth (DFW)</option>\n        <option value="MIA">Miami (MIA)</option>\n        <option value="SEA">Seattle (SEA)</option>\n        <option value="DEN">Denver (DEN)</option>\n        <option value="ATL">Atlanta (ATL)</option>\n        <option value="IAD">Washington DC (IAD)</option>\n        <option value="LAS">Las Vegas (LAS)</option>\n      </select>\n    </div>\n  </div>\n  <div class="btnrow">\n    <button class="run" id="routeRun">▶ Price my route</button>\n  </div>\n  <label class="f">Fire an event on this route</label>\n  <div class="btnrow">\n    <button class="ghost scen" data-s="festival">Festival announced</button>\n    <button class="ghost scen" data-s="competitor">Competitor drops fare 20%</button>\n    <button class="ghost scen" data-s="fuel">Fuel +10%</button>\n    <button class="ghost scen" data-s="soft">Bookings below pace</button>\n  </div>\n  <p class="hint">Same route + same event → same result, every time. Fully deterministic.</p>\n  <div class="spinner" id="cspin"><div class="dot"></div><span>Pricing…</span></div>\n  <div id="verdict"></div>\n</section>\n\n\n\n<section class="card" id="runbox">\n  <h2><span class="n">3</span>Run the demo</h2>\n  <p>Click below to run the full canned demonstration. It takes a few seconds.</p>\n  <div class="btnrow">\n    <button class="run" id="run">&#9654; Run live demo</button>\n  </div>\n  <div class="spinner" id="spin"><div class="dot"></div><span>The pricing engine is evaluating every fare…</span></div>\n  <div id="output">\n    <div class="out" id="outtext"></div>\n    <details class="raw"><summary>Show raw terminal output</summary>\n      <div class="out" id="rawtext"></div>\n    </details>\n  </div>\n</section>\n\n<section class="card" id="takeaways" style="display:none">\n  <div class="take">\n    <h2>What just happened</h2>\n    <ul>\n<li>$280 beat $400 on expected revenue ($48,200 vs $44,000) — higher price is not higher revenue when demand is elastic.</li>\n<li>The agent recommended $320 → $350 with its reasoning on the table: signals used, alternatives beaten, confidence stated, and what could invalidate it.</li>\n<li>Fuel +12% moved no fares: the agent separated a cost signal from a demand signal.</li>\n<li>Head-to-head, the agentic strategy beat fixed and rule-based pricing on profit, seats sold, and shock resilience.</li>\n<li>Try your own: fire the scenario buttons in “Try your own” — festival, competitor cut, fuel spike, soft demand.</li>\n    </ul>\n  </div>\n</section>\n\n</div>\n<aside class="care-sidebar">\n<div class="side-card">\n<h3>Learn more</h3>\n<p style="font-size:13.5px;color:var(--muted);margin:0 0 14px">Want to go deeper on airline pricing? Start with these.</p>\n<div class="side-vid">\n<iframe src="https://www.youtube-nocookie.com/embed/8IWHcrWanXA" title="Why Airlines Sell the Same Seat Twice" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>\n<p>Perishable inventory explained: why every empty seat at takeoff is money gone forever.</p>\n</div>\n<div class="side-vid">\n<iframe src="https://www.youtube-nocookie.com/embed/sMVcuctEtzg" title="Why You Paid $947 for the Same Seat" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>\n<p>Price-discovery engines: fare buckets, repricing, and what the algorithm reads.</p>\n</div>\n<div class="side-vid">\n<iframe src="https://www.youtube-nocookie.com/embed/n_-x9DomqV0" title="Why Flying Is So Expensive" loading="lazy" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>\n<p>The cost stack behind a ticket: fuel, fees, salaries &mdash; and what drives the price you see.</p>\n</div>\n</div>\n<div class="side-card">\n<h3>Go deeper &mdash; articles</h3>\n<ul class="blog-list">\n<li><a href="https://apex.aero/articles/yield-management-pricing-explained/" target="_blank" rel="noopener">Yield Management Pricing, Explained</a><span>APEX &mdash; From 1978 deregulation to fare buckets: how yield management was born.</span></li>\n<li><a href="https://fastercapital.com/topics/making-total-yield-management-work-for-your-business.html/3" target="_blank" rel="noopener">Making Total Yield Management Work</a><span>FasterCapital &mdash; Dynamic pricing, overbooking, and segmentation &mdash; the yield-management playbook.</span></li>\n</ul>\n</div>\n</aside>\n\n</div></main>\n<footer><div class="wrap">\n  <a href="https://github.com/ynpreet/aeroyield-ai" target="_blank" rel="noopener">View the project on GitHub</a>\n  &nbsp;&middot;&nbsp; All data in this demo is synthetic / fictional.\n</div></footer>\n\n<script>\nconst SECTIONS = [["LIVE SCENARIO", "Three events hit at once. The agent runs its decision loop: Observe \\u2192 Analyze \\u2192 Decide \\u2192 Act \\u2192 Verify."], ["DECIDE --", "The recommendation: which fare maximizes expected profit, why it beats every alternative, and what could invalidate it."], ["ACT --", "Staged to the approval queue (simulation). A human approves \\u2014 this demo never touches a live booking system."], ["TWIST", "A competitor drops to $270. Watch the agent re-evaluate instead of auto-matching."], ["SCENARIO SIMULATIONS", "Same engine, injected shocks: festival announced, competitor cut, fuel spike, soft demand."], ["KILLER DIFFERENTIATOR", "Three strategies on identical scenarios: fixed vs. rule-based vs. agentic. Measured, not claimed."], ["SUMMARY", "End of run."]];\nfunction esc(s){return s.replace(/&/g,\'&amp;\').replace(/</g,\'&lt;\').replace(/>/g,\'&gt;\');}\nfunction decorate(line){\n  let h = esc(line);\n  h = h.replace(/\\[ORCHESTRATOR\\]/g,\'<span class="tok-orch">[ORCHESTRATOR]</span>\');\n  h = h.replace(/\\[TOOL [^\\]]+\\]/g,function(m){return \'<span class="tok-tool">\'+m+\'</span>\';});\n  h = h.replace(/\\[MEMORY\\]/g,\'<span class="tok-mem">[MEMORY]</span>\');\n  h = h.replace(/GUARDRAIL/g,\'<span class="tok-guard">GUARDRAIL</span>\');\n  return h;\n}\nfunction renderOut(text){\n  document.getElementById(\'rawtext\').textContent = text;\n  const lines = text.split(\'\\n\');\n  let html = \'\';\n  for(const line of lines){\n    let matched = null;\n    for(const s of SECTIONS){ if(line.indexOf(s.m) !== -1){ matched = s; break; } }\n    if(matched){\n      html += \'<div class="sechead">\'+decorate(line)+\'</div>\'+\n              \'<div class="seccap">\'+matched.c+\'</div>\';\n      continue;\n    }\n    html += decorate(line) + \'\\n\';\n  }\n  document.getElementById(\'outtext\').innerHTML = html;\n  document.getElementById(\'output\').classList.add(\'show\');\n  document.getElementById(\'output\').scrollIntoView({behavior:\'smooth\',block:\'start\'});\n}\nfunction showTakeaways(){\n  const t = document.getElementById(\'takeaways\');\n  t.style.display=\'block\'; t.classList.add(\'show\');\n  t.scrollIntoView({behavior:\'smooth\',block:\'start\'});\n}\ndocument.getElementById(\'run\').addEventListener(\'click\',function(){\n  const btn=this, spin=document.getElementById(\'spin\');\n  btn.disabled=true; spin.classList.add(\'show\');\n  fetch(\'/api/run\').then(r=>r.json()).then(j=>{\n    spin.classList.remove(\'show\'); btn.disabled=false;\n    renderOut(j.output);\n    if(typeof loadDecisionTable===\'function\') loadDecisionTable();\n    showTakeaways();\n  }).catch(e=>{spin.classList.remove(\'show\');btn.disabled=false;alert(\'Run failed: \'+e);});\n});\nfunction aeroUsd(n){return \'$\'+Number(n).toLocaleString(\'en-US\');}\nfunction aeroVerdictHTML(v, table){\n  var main = v.action === \'CHANGE\'\n    ? \'hold \' + aeroUsd(v.current_fare) + \' &rarr; <span class="chg">move to \' + aeroUsd(v.recommended_fare) + \'</span>\'\n    : \'<span class="hld">hold at \' + aeroUsd(v.current_fare) + \'</span>\';\n  var gainTxt = (v.gain >= 0 ? \'+\' : \'\') + aeroUsd(v.gain);\n  var html = \'<div class="verdict">\'\n    + \'<div class="v-route">\' + esc(v.dep_name) + \' &rarr; \' + esc(v.arr_name)\n    + \'<span class="v-scen">\' + esc(v.scenario_label) + \'</span></div>\'\n    + \'<div class="v-main">\' + main + \'</div>\'\n    + \'<div class="v-stats">Expected gain <b>\' + gainTxt + \'</b> vs holding\'\n    + \' &nbsp;·&nbsp; Confidence <b>\' + v.confidence.toFixed(2) + \'</b>\'\n    + \' &nbsp;·&nbsp; \' + v.seats_left + \' seats left &nbsp;·&nbsp; \' + v.load_pct + \'% load factor</div>\'\n    + \'<ul class="v-signals">\';\n  for (var i = 0; i < v.signals.length; i++){\n    html += \'<li>\' + esc(v.signals[i]) + \'</li>\';\n  }\n  html += \'</ul>\';\n  if (v.baseline){\n    var b = v.baseline;\n    var bTxt = b.action === \'CHANGE\' ? \'move to \' + aeroUsd(b.recommended_fare) : \'hold \' + aeroUsd(v.current_fare);\n    html += \'<div class="v-base"><b>Before (baseline, no event):</b> \' + bTxt\n      + \' &nbsp;·&nbsp; <b>After (\' + esc(v.scenario_label.toLowerCase()) + \'):</b> \'\n      + (v.action === \'CHANGE\' ? \'move to \' + aeroUsd(v.recommended_fare) : \'hold\')\n      + \' (\' + gainTxt + \' vs holding)</div>\';\n  }\n  html += \'<div class="hint" style="margin-top:10px">Staged to the human approval queue (simulation) — never a live booking system. All figures synthetic.</div>\';\n  if (table){\n    html += \'<details><summary>Show engine table</summary><div class="out">\' + esc(table) + \'</div></details>\';\n  }\n  html += \'</div>\';\n  return html;\n}\nfunction aeroSetBusy(busy){\n  document.getElementById(\'routeRun\').disabled = busy;\n  document.querySelectorAll(\'.scen\').forEach(function(x){ x.disabled = busy; });\n  var spin = document.getElementById(\'cspin\');\n  if (busy) spin.classList.add(\'show\'); else spin.classList.remove(\'show\');\n}\nfunction aeroRun(scenario){\n  var dep = document.getElementById(\'a_dep\').value;\n  var arr = document.getElementById(\'a_arr\').value;\n  aeroSetBusy(true);\n  fetch(\'/api/custom\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},\n    body:JSON.stringify({dep:dep, arr:arr, scenario:scenario})})\n  .then(function(r){ return r.json(); })\n  .then(function(j){\n    aeroSetBusy(false);\n    var box = document.getElementById(\'verdict\');\n    if (j.error){\n      box.innerHTML = \'<div class="verdict-err">&#9888; \' + esc(j.error) + \'</div>\';\n    } else if (j.verdict){\n      box.innerHTML = aeroVerdictHTML(j.verdict, j.table);\n    } else {\n      box.innerHTML = \'<div class="verdict-err">&#9888; Something went wrong — please try again.</div>\';\n    }\n    box.scrollIntoView({behavior:\'smooth\', block:\'nearest\'});\n  })\n  .catch(function(e){\n    aeroSetBusy(false);\n    document.getElementById(\'verdict\').innerHTML =\n      \'<div class="verdict-err">&#9888; Request failed: \' + esc(String(e)) + \'</div>\';\n  });\n}\ndocument.getElementById(\'routeRun\').addEventListener(\'click\', function(){ aeroRun(\'baseline\'); });\ndocument.querySelectorAll(\'.scen\').forEach(function(b){\n  b.addEventListener(\'click\', function(){ aeroRun(b.dataset.s); });\n});\nfunction collectCustom(){return {};}\n\n\nfunction wireCustom(){\n  const b=document.getElementById(\'customRun\');\n  if(!b) return;\n  b.addEventListener(\'click\',function(){\n    const spin=document.getElementById(\'cspin\');\n    b.disabled=true; spin.classList.add(\'show\');\n    fetch(\'/api/custom\',{method:\'POST\',headers:{\'Content-Type\':\'application/json\'},\n      body:JSON.stringify(collectCustom())})\n    .then(r=>r.json()).then(j=>{\n      spin.classList.remove(\'show\'); b.disabled=false;\n      if(j.error){alert(j.error);return;}\n      renderOut(j.output); showTakeaways();\n    }).catch(e=>{spin.classList.remove(\'show\');b.disabled=false;alert(\'Run failed: \'+e);});\n  });\n}\nwireCustom();\n</script>\n</body>\n</html>\n'

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "WorkshopUI/1.0"

    def _send(self, body, ctype="text/html; charset=utf-8"):
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, obj):
        self._send(json.dumps(obj), "application/json; charset=utf-8")

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            length = 0
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return {}

    def _serve_asset(self, path):
        safe = (HERE / path.lstrip("/")).resolve()
        try:
            safe.relative_to(HERE / "assets")
        except ValueError:
            return self.send_error(403, "forbidden")
        if not safe.is_file():
            return self.send_error(404, "not found")
        ctype, _ = mimetypes.guess_type(str(safe))
        data = safe.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path in ("/", "/index.html"):
            self._send(PAGE)
        elif path == "/api/run":
            self._json({"output": _capture_canned()})
        elif path.startswith("/assets/"):
            self._serve_asset(path)
        else:
            self.send_error(404, "not found")

    def do_POST(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/api/custom":
            params = self._read_json()
            self._json(_capture_custom(run_custom, params))
        else:
            self.send_error(404, "not found")

    def log_message(self, fmt, *args):
        sys.stderr.write("ui: " + (fmt % args) + "\n")


def main():
    server = http.server.ThreadingHTTPServer((HOST, PORT), Handler)
    print("AeroYield AI demo UI -> http://localhost:8004")
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")


if __name__ == "__main__":
    main()
