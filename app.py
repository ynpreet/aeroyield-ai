#!/usr/bin/env python3
"""AeroYield AI -- localhost web UI for the demo.

STDLIB ONLY (http.server -- no Flask/Streamlit/pip, no API keys, offline).

Usage:
    python3 app.py
Then open in Chrome: http://localhost:8004

Endpoints:
    GET /         -- single-page demo UI (inline CSS/JS, no external assets)
    GET /api/run  -- runs `python3 demo.py` via subprocess, returns
                     {"ok": true, "output": "..."} (or {"ok": false, ...})

This file never modifies demo.py's behavior; it only executes it.
"""

import errno
import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8004
HOST = "127.0.0.1"
HERE = Path(__file__).resolve().parent
DEMO = HERE / "demo.py"

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AeroYield AI &mdash; Agentic Airline Revenue Management (Live Demo)</title>
<style>
  :root{
    --bg:#0b1220; --panel:#121c30; --panel2:#0f1728; --line:#22314f;
    --ink:#e8eefc; --dim:#9fb0cc; --accent:#4cc2ff; --green:#3ddc84;
    --amber:#ffc554; --red:#ff7a90; --violet:#b39dff;
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);
       font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
       line-height:1.55}
  .wrap{max-width:1080px;margin:0 auto;padding:28px 20px 64px}
  header.top{border:1px solid var(--line);border-radius:14px;background:linear-gradient(135deg,#101c33,#0b1220);
             padding:26px 28px;margin-bottom:20px}
  header.top h1{margin:0 0 6px;font-size:30px;letter-spacing:.3px}
  header.top h1 .ai{color:var(--accent)}
  .tag{display:inline-block;font-size:12px;color:#0b1220;background:var(--amber);
       border-radius:20px;padding:2px 10px;font-weight:700;margin-bottom:10px}
  .sub{color:var(--dim);font-size:15px;margin:6px 0 0;max-width:900px}
  .story{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin:18px 0}
  @media(max-width:760px){.story{grid-template-columns:1fr}}
  .story .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
  .story .card h3{margin:0 0 6px;font-size:14px;color:var(--accent);text-transform:uppercase;letter-spacing:.6px}
  .story .card p{margin:0;font-size:13.5px;color:var(--dim)}
  .story .card b{color:var(--ink)}
  .controls{display:flex;gap:12px;align-items:center;margin:18px 0;flex-wrap:wrap}
  button.run{font-size:17px;font-weight:700;color:#06121f;background:linear-gradient(180deg,#6fd6ff,#3aa8ef);
             border:0;border-radius:10px;padding:14px 30px;cursor:pointer}
  button.run:hover{filter:brightness(1.08)}
  button.run:disabled{opacity:.55;cursor:wait}
  .hint{font-size:13px;color:var(--dim)}
  .spinner{display:none;align-items:center;gap:10px;color:var(--dim);font-size:14px}
  .spinner.on{display:flex}
  .dot{width:12px;height:12px;border-radius:50%;background:var(--accent);animation:pulse 1s infinite}
  @keyframes pulse{0%,100%{opacity:.25;transform:scale(.8)}50%{opacity:1;transform:scale(1.15)}}
  .cols{display:grid;grid-template-columns:1.35fr 1fr;gap:14px;margin-top:8px}
  @media(max-width:900px){.cols{grid-template-columns:1fr}}
  .panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
  .panel h2{margin:0 0 10px;font-size:15px;text-transform:uppercase;letter-spacing:.8px;color:var(--dim)}
  .panel h2 .n{color:var(--accent)}
  .loop{display:flex;gap:6px;margin:0 0 12px;flex-wrap:wrap}
  .loop span{font-size:12px;font-weight:700;padding:4px 10px;border-radius:20px;background:var(--panel2);
             border:1px solid var(--line);color:var(--dim)}
  .loop span.hot{color:#06121f;background:var(--green);border-color:var(--green)}
  #trace{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12.6px;
         max-height:640px;overflow:auto;background:var(--panel2);border:1px solid var(--line);
         border-radius:8px;padding:12px 14px;white-space:pre-wrap}
  #trace .blk{margin:10px 0 2px;padding:7px 10px;border-radius:6px;color:var(--amber);font-weight:700;
             background:rgba(255,197,84,.07);border:1px solid rgba(255,197,84,.25)}
  #trace .plan{margin:8px 0;padding:10px 12px;border-radius:8px;background:rgba(76,194,255,.10);
             border:1px solid var(--accent);color:var(--ink);font-weight:700}
  #trace .tool{margin:6px 0;padding:6px 10px;border-left:3px solid var(--violet);
             background:rgba(179,157,255,.07)}
  #trace .tool b{color:var(--violet)}
  #trace .step{margin:8px 0 2px;font-weight:700;color:var(--green)}
  #trace .dec{margin:6px 0;padding:8px 10px;border-radius:6px;background:rgba(61,220,132,.08);
             border:1px solid rgba(61,220,132,.4)}
  #trace .ln{color:var(--dim)}
  #results .stat{display:flex;justify-content:space-between;gap:10px;padding:9px 2px;
                 border-bottom:1px dashed var(--line);font-size:14px}
  #results .stat:last-child{border-bottom:0}
  #results .k{color:var(--dim)}
  #results .v{font-weight:700;text-align:right}
  #results .v.good{color:var(--green)}
  #results .v.big{color:var(--amber);font-size:16px}
  .empty{color:var(--dim);font-size:14px;text-align:center;padding:40px 10px}
  .err{background:rgba(255,122,144,.1);border:1px solid var(--red);border-radius:8px;
       padding:12px;color:var(--red);font-size:14px;margin-top:10px}
  footer{margin-top:26px;color:var(--dim);font-size:12.5px;border-top:1px solid var(--line);padding-top:14px}
  kbd{background:var(--panel2);border:1px solid var(--line);border-radius:4px;padding:1px 6px;font-size:12px}
</style>
</head>
<body>
<div class="wrap">

<header class="top">
  <div class="tag">LIVE DEMO &mdash; runs locally, stdlib only</div>
  <h1>AeroYield <span class="ai">AI</span> &mdash; An Agentic AI Revenue Management System for Airlines</h1>
  <p class="sub"><i>&ldquo;The AI agent that thinks like an airline revenue manager.&rdquo;</i>
  This is the <b>airline&rsquo;s</b> pricing agent &mdash; not a passenger price predictor.
  One route (<b>SFO &rarr; BOS</b>), 180 seats, fare <b>$320</b>, 120 booked / 60 remaining,
  14 days to departure. One orchestrator + three intelligence tools run the
  <b>Observe &rarr; Analyze &rarr; Decide &rarr; Act &rarr; Verify</b> loop, out loud.
  All data is synthetic sample data; price moves are staged to a simulated approval queue.</p>
</header>

<div class="story">
  <div class="card"><h3>The scenario</h3><p>Three events hit at once: a <b>Boston festival</b> is announced, <b>competitor fares rise</b>, and <b>booking pace</b> runs ahead of baseline.</p></div>
  <div class="card"><h3>The decision</h3><p>The agent reads the signals, prices the event premium, and recommends <b>$320 &rarr; $350</b> &mdash; optimizing for <b>profit</b>, not just revenue.</p></div>
  <div class="card"><h3>The twist</h3><p>A rival drops to <b>$270</b>. The agent verifies comparability, then <b>does not auto-follow</b> &mdash; it fences a <b>$299</b> bucket instead of starting a price war.</p></div>
</div>

<div class="controls">
  <button class="run" id="runBtn" onclick="runDemo()">&#9654; Run live demo</button>
  <div class="spinner" id="spin"><div class="dot"></div> Running demo.py &hellip;</div>
  <span class="hint">Executes <kbd>python3 demo.py</kbd> on this machine and renders the agent trace below. Deterministic: byte-identical every run.</span>
</div>

<div class="cols">
  <div class="panel">
    <h2><span class="n">01</span> &mdash; Agent trace</h2>
    <div class="loop" id="loop">
      <span data-s="OBSERVE">OBSERVE</span><span data-s="ANALYZE">ANALYZE</span><span data-s="DECIDE">DECIDE</span><span data-s="ACT">ACT</span><span data-s="VERIFY">VERIFY</span>
    </div>
    <div id="trace"><div class="empty">Press <b>&ldquo;Run live demo&rdquo;</b> to watch the agent work through the decision loop.</div></div>
  </div>
  <div class="panel">
    <h2><span class="n">02</span> &mdash; Results</h2>
    <div id="results"><div class="empty">Headline numbers appear here after the run.</div></div>
  </div>
</div>

<footer>
  AeroYield AI demo &mdash; served from <kbd>app.py</kbd> (Python stdlib <kbd>http.server</kbd>, localhost only, no network calls).
  Full details, data-honesty notes, and speaker notes live in the README.
</footer>
</div>

<script>
function esc(s){return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}
function runDemo(){
  var btn=document.getElementById("runBtn"), spin=document.getElementById("spin");
  btn.disabled=true; spin.classList.add("on");
  document.querySelectorAll("#loop span").forEach(function(s){s.classList.remove("hot");});
  var t0=performance.now(), step=0;
  var cyc=setInterval(function(){ // animate the loop while the demo runs
    var spans=document.querySelectorAll("#loop span");
    spans.forEach(function(s){s.classList.remove("hot");});
    spans[step%spans.length].classList.add("hot"); step++;
  },350);
  fetch("/api/run").then(function(r){return r.json();}).then(function(d){
    clearInterval(cyc);
    document.querySelectorAll("#loop span").forEach(function(s){s.classList.add("hot");});
    spin.classList.remove("on"); btn.disabled=false;
    var secs=((performance.now()-t0)/1000).toFixed(2);
    if(d.ok){ renderTrace(d.output); renderResults(d.output, secs); }
    else{
      document.getElementById("trace").innerHTML='<div class="err"><b>Demo failed.</b><br>'+esc(d.error||"unknown error")+"</div>";
      document.getElementById("results").innerHTML='<div class="empty">No results &mdash; the demo did not complete.</div>';
    }
  }).catch(function(e){
    clearInterval(cyc); spin.classList.remove("on"); btn.disabled=false;
    document.getElementById("trace").innerHTML='<div class="err"><b>Request failed:</b> '+esc(String(e))+"</div>";
  });
}
function renderTrace(out){
  var lines=out.split("\\n"), html="", bar=/^=+$/;
  lines.forEach(function(raw){
    var line=raw, cls="ln";
    if(bar.test(line.trim())) return;                       // skip ===== separators
    var t=line.trim();
    if(t.indexOf("[ORCHESTRATOR] PLAN")==0){
      html+='<div class="plan">&#9679; PLAN &mdash; '+esc(t.replace("[ORCHESTRATOR] PLAN -- ",""))+"</div>"; return;
    }
    if(t.indexOf("[ORCHESTRATOR]")==0){
      html+='<div class="plan">'+esc(t)+"</div>"; return;
    }
    if(t.indexOf("[TOOL]")==0){ cls="tool"; }
    else if(/^(OBSERVE|ANALYZE|DECIDE|ACT|VERIFY)(\\b| --)/.test(t)){ cls="step"; }
    else if(t.indexOf("RECOMMENDATION:")==0){ cls="dec"; }
    else if(/^LIVE SCENARIO|^TWIST|^SCENARIO SIMULATIONS|^KILLER DIFFERENTIATOR|^SUMMARY/.test(t)){
      html+='<div class="blk">'+esc(t)+"</div>"; return;
    }
    var body=esc(line).split("$299").join("<b>$299</b>");
    html+='<div class="'+cls+'">'+body+"</div>";
  });
  document.getElementById("trace").innerHTML=html;
}
function stat(k,v,cls){return '<div class="stat"><span class="k">'+k+'</span><span class="v '+(cls||"")+'">'+v+"</span></div>";}
function renderResults(out, secs){
  // demo.py prints "$320 -> $350" unescaped (raw subprocess stdout).
  var m1=out.match(/RECOMMENDATION: (\\$320 -> \\$350)\\s*\\[([A-Z]+)\\]/);
  var m2=out.match(/HEADLINE: agentic profit (\\$[0-9,]+) vs fixed (\\$[0-9,]+) \\(\\+(\\d+)%\\)/);
  var m3=out.match(/agentic sold\\s+(\\d+) seats vs (\\d+); forecast error ([0-9.]+)% vs ([0-9.]+)%/);
  var m4=out.match(/shock-scenario \\(S2\\)\\s+profit (\\$[0-9,]+) vs (\\$[0-9,]+)/);
  var m5=out.match(/LESSON: (\\$280 -> \\$[0-9,]+) expected revenue BEATS (\\$400 -> \\$[0-9,]+)/);
  var m6=out.match(/vs holding (\\$320): (\\+\\$[0-9,]+)/);
  var h="";
  if(m1) h+=stat("Recommendation", m1[1]+" &mdash; "+m1[2], "big");
  if(m6) h+=stat("Expected gain vs holding $320", m6[2], "good");
  if(m5) h+=stat("Counterintuitive lesson", m5[1]+" beats "+m5[2], "good");
  if(m2) h+=stat("Agentic profit vs fixed fare", m2[1]+" vs "+m2[2]+" (+"+m2[3]+"%)", "good");
  if(m3) h+=stat("Seats sold", m3[1]+" vs "+m3[2], "good");
  if(m3) h+=stat("Forecast error", m3[3]+"% vs "+m3[4]+"%", "good");
  if(m4) h+=stat("Shock-scenario (S2) profit", m4[1]+" vs "+m4[2], "good");
  h+=stat("Competitor $270 response", "Fenced $299 bucket, hold $350", "good");
  h+=stat("Run time", secs+"s &mdash; deterministic", "");
  if(!h) h='<div class="empty">Could not parse results.</div>';
  document.getElementById("results").innerHTML=h;
}
</script>
</body>
</html>
"""


def run_demo():
    """Execute demo.py; return (ok, payload)."""
    try:
        proc = subprocess.run(
            [sys.executable, str(DEMO)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(HERE),
        )
    except subprocess.TimeoutExpired:
        return False, {"error": "demo.py timed out after 60s"}
    except OSError as e:
        return False, {"error": "could not start demo.py: %s" % e}
    if proc.returncode != 0:
        return False, {"error": "demo.py exited %d: %s"
                       % (proc.returncode, proc.stderr[-2000:])}
    return True, {"output": proc.stdout}


class Handler(BaseHTTPRequestHandler):
    server_version = "AeroYieldUI/1.0"

    def log_message(self, fmt, *args):  # quieter logs
        sys.stderr.write("[app] %s\n" % (fmt % args))

    def _send(self, code, body, ctype):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/" or self.path.startswith("/?"):
            self._send(200, PAGE, "text/html")
        elif self.path == "/api/run":
            ok, payload = run_demo()
            payload["ok"] = ok
            self._send(200, json.dumps(payload), "application/json")
        else:
            self._send(404, "not found", "text/plain")

    # Disallow anything that could change state.
    def do_POST(self): self._send(405, "method not allowed", "text/plain")
    def do_PUT(self): self._send(405, "method not allowed", "text/plain")
    def do_DELETE(self): self._send(405, "method not allowed", "text/plain")


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print("=" * 60)
    print("  AeroYield AI -- demo web UI")
    print()
    print("  Open in Chrome: http://localhost:%d" % PORT)
    print()
    print("  (listening on %s:%d -- localhost only; Ctrl+C to stop)" % (HOST, PORT))
    print("=" * 60)
    sys.stdout.flush()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[app] stopped.")


if __name__ == "__main__":
    try:
        main()
    except OSError as e:
        if e.errno == errno.EADDRINUSE:
            sys.stderr.write(
                "\nERROR: port %d is already in use.\n"
                "Another copy of app.py (or another app) is already listening.\n"
                "Stop it first, then run: python3 app.py\n" % PORT)
            sys.exit(1)
        raise
