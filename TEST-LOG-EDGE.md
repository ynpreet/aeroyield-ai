# Edge-Case Test Log — AeroYield AI (web UI + route engine)

Date: 2026-10-10. Deterministic: same route+scenario -> same verdict (sha256-seeded).

## Fixes applied during hardening
1. `run_custom`: non-dict params (JSON string/null/number/array) coerced to {}
   (was: AttributeError -> dead connection). Now defaults to SFO->BOS baseline.

## 16-case adversarial battery (function level) — ALL PASS (2 fixed, then all pass)
- dep==arr (SFO->SFO, JFK->JFK) -> friendly "pick two different airports" error, no verdict.
- Reverse pair (BOS->SFO), lowercase ("sfo"/"bos"), padded (" sFo ") -> normalized, valid verdict.
- Invalid codes ("XXX"/"YYY"/"SFOOOO"/"B") -> fall back to SFO/BOS defaults, valid verdict.
- Unicode airport codes ("✈️"/"🛬") -> defaults, valid verdict.
- 10,000-char codes -> defaults, no crash.
- None / 123 / list / dict params -> defaults, valid verdict.
- Bad scenario ("nuclear_winter") / empty scenario -> baseline.
- Every valid verdict: recommended fare inside the candidate set, confidence 0.30-0.97,
  byte-identical on repeat runs (determinism asserted per case).

## HTTP battery (live server, port 8004) — ALL PASS
- Malformed JSON / empty body / 10KB junk / wrong types / JSON array / JSON null
  -> HTTP 200, valid JSON, no traceback.
- 24 concurrent requests -> all 200.
