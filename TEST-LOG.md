# Test Log — 10x Reliability Gate

Date: 2026-10-10 (re-verified by coordinator — original log's recorded hash was stale; re-ran fresh)
Machine: Linux VM, Python 3.12.3, stdlib only

## Result: 10/10 PASSED, byte-identical output on every run

Method: `python3 demo.py` executed 10 consecutive times; each run's stdout was hashed (SHA-256).

| Run | Exit code | SHA-256 (stdout) |
|-----|-----------|------------------|
| 1 | 0 | e0d8918f63163cb74ffcdd8ad12c7f6250a0977b019fe0872fb0d7551dc55b1f |
| 2 | 0 | e0d8918f63163cb74ffcdd8ad12c7f6250a0977b019fe0872fb0d7551dc55b1f |
| 3 | 0 | e0d8918f63163cb74ffcdd8ad12c7f6250a0977b019fe0872fb0d7551dc55b1f |
| 4 | 0 | e0d8918f63163cb74ffcdd8ad12c7f6250a0977b019fe0872fb0d7551dc55b1f |
| 5 | 0 | e0d8918f63163cb74ffcdd8ad12c7f6250a0977b019fe0872fb0d7551dc55b1f |
| 6 | 0 | e0d8918f63163cb74ffcdd8ad12c7f6250a0977b019fe0872fb0d7551dc55b1f |
| 7 | 0 | e0d8918f63163cb74ffcdd8ad12c7f6250a0977b019fe0872fb0d7551dc55b1f |
| 8 | 0 | e0d8918f63163cb74ffcdd8ad12c7f6250a0977b019fe0872fb0d7551dc55b1f |
| 9 | 0 | e0d8918f63163cb74ffcdd8ad12c7f6250a0977b019fe0872fb0d7551dc55b1f |
| 10 | 0 | e0d8918f63163cb74ffcdd8ad12c7f6250a0977b019fe0872fb0d7551dc55b1f |

---

# Web UI test log — app.py (localhost Chrome demo)

Date: 2026-10-10 | Machine: Linux VM, Python 3.12.3, stdlib only

**Result: 12/12 rounds PASSED**

Method (script `/tmp/webui-test.sh`, re-runnable): each round —
(a) `python3 demo.py` must exit 0;
(b) start `python3 app.py`, wait for `http://127.0.0.1:8004/`,
assert startup banner prints `Open in Chrome: http://localhost:8004`,
`curl /` → 200 containing page markers (`AeroYield`, `Run live demo`,
`Agent trace`, `/api/run`),
`curl /api/run` → 200 with `{"ok": true, ...}` containing stable markers
(`$320 -> $350`, `TWIST`, `KILLER DIFFERENTIATOR`, `$270`,
`[ORCHESTRATOR] PLAN`),
`curl /nope` → 404; then kill the server.

| Round | demo.py exit | / (200+markers) | /api/run (200+markers) | /nope 404 | Verdict |
|-------|--------------|-----------------|------------------------|-----------|---------|
| 1–12 | 0 | yes | yes | yes | PASS ×12 |

Checks beyond the 12 rounds:
- Port-in-use: second `python3 app.py` while one is running → clear
  `ERROR: port 8004 is already in use.` on stderr, exit code 1. PASS.
- `/api/run` result-panel regexes (6/6) verified against live `demo.py`
  output: `$320 -> $350 [CHANGE]`, `agentic profit $30,050 vs fixed $24,380 (+23%)`,
  `110 vs 92 seats`, `forecast error 25% vs 48%`, `S2 profit $10,360 vs $5,300`,
  `Expected gain vs holding $320: +$1,030`. PASS.
- No Python SyntaxWarnings from the served page. PASS.

Failures found & fixed during testing:
1. Result-panel regex used `versus holding $320` but demo.py prints
   `vs holding $320` → "Expected gain" stat never rendered. Fixed regex;
   re-verified 6/6 match.
2. Stray `\$` invalid escape in served JS (SyntaxWarning). Replaced with
   string split/join. Fixed; verified warning-free.
3. One round failed as `server did not come up` though the banner printed —
   root cause was environmental, not code: a sibling agent's process cleanup
   (`pkill`) killed the test server mid-round (sibling demo `hhv-copilot`
   runs on port 8002, so no port conflict with 8004). Re-ran clean: 12/12.
   Note for parallel demo work: coordinate `pkill` patterns so one demo's
   cleanup can't SIGTERM another demo's server.

