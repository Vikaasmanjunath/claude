#!/usr/bin/env python3
"""
Build Dashboard v2 — reads grants_results.json → writes index.html
Includes: confidence meter, search term legend, API source badges,
          multi-filter controls, deadline timeline, grant cards.
"""

import json, datetime, os

TODAY = datetime.date.today()
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

src  = os.path.join(SCRIPT_DIR, "grants_results.json")
dest = os.path.join(SCRIPT_DIR, "index.html")

with open(src) as f:
    data = json.load(f)

grants    = data["grants"]
generated = data["generated"]
total     = data["total"]
nih_terms = data.get("nih_query_clusters", [])
gov_terms = data.get("grantsgov_terms", [])

unrestricted = [g for g in grants if g["citizenship"] == "unrestricted"]
unspecified  = [g for g in grants if g["citizenship"] in ("unspecified","check")]
high_conf    = [g for g in grants if g.get("confidence",0) >= 70]
urgent       = [g for g in grants if g.get("deadline_urgency") in ("urgent","soon")]

# Timeline: real deadlines, sorted, first 12
timeline = sorted(
    [g for g in grants if g.get("deadline") and g.get("days_until_deadline",9999) not in (9999,-1) and g.get("days_until_deadline",0) > 0],
    key=lambda g: g["days_until_deadline"]
)[:12]

# ── helpers ────────────────────────────────────────────────────────────────

def esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def citizenship_badge(c):
    if c == "unrestricted":
        return '<span class="badge b-green">✓ Unrestricted — F-1 OK</span>'
    if c in ("unspecified","check"):
        return '<span class="badge b-amber">◎ Unspecified — Verify</span>'
    return '<span class="badge b-gray">? Unknown</span>'

def fit_badge(conf):
    if conf >= 80: return '<span class="badge b-emerald">Confidence: VERY HIGH</span>'
    if conf >= 65: return '<span class="badge b-teal">Confidence: HIGH</span>'
    if conf >= 45: return '<span class="badge b-blue">Confidence: MODERATE</span>'
    if conf >= 25: return '<span class="badge b-slate">Confidence: LOW</span>'
    return '<span class="badge b-stone">Confidence: MINIMAL</span>'

def source_badge(src):
    m = {"curated":'<span class="src-badge src-cur">✔ Curated &amp; Verified</span>',
         "nih_reporter":'<span class="src-badge src-nih">NIH Reporter Live</span>',
         "grants_gov":'<span class="src-badge src-gov">Grants.gov Live</span>'}
    return m.get(src, '')

def deadline_cls(u):
    return {"urgent":"dl-urgent","soon":"dl-soon","normal":"dl-normal",
            "future":"dl-future","no_deadline":"dl-none","expired":"dl-exp"}.get(u,"")

def conf_bar(conf):
    pct = min(conf, 100)
    col = ("#065f46" if pct>=80 else "#0f766e" if pct>=65 else
           "#1d4ed8" if pct>=45 else "#92400e" if pct>=25 else "#6b7280")
    return f'''<div class="conf-wrap" title="Confidence: {pct}%">
  <div class="conf-bar" style="width:{pct}%;background:{col}"></div>
  <span class="conf-label">{pct}%</span>
</div>'''

def pills(items, cls="req-pill"):
    return "".join(f'<span class="{cls}">{esc(r)}</span>' for r in items)

def equip_tags(eq):
    return "".join(f'<span class="equip-tag">⚗ {esc(e)}</span>' for e in eq) if eq else ""

def pop_tags(pp):
    return "".join(f'<span class="pop-tag">👥 {esc(p)}</span>' for p in pp) if pp else ""

def cat_tags(cc):
    return "".join(f'<span class="cat-tag">{esc(c)}</span>' for c in cc[:5]) if cc else ""

# ── card renderer ──────────────────────────────────────────────────────────

def card(g, idx):
    conf = g.get("confidence", 0)
    dlc  = deadline_cls(g.get("deadline_urgency","normal"))
    days = g.get("days_until_deadline", 9999)
    if days == 9999 or days < 0:
        days_str = ""
    else:
        days_str = f' <em class="days-away">({days}d)</em>'

    eq_html  = equip_tags(g.get("equipment_relevance",[]))
    pop_html = pop_tags(g.get("populations",[]))
    cat_html = cat_tags(g.get("category",[]))

    eq_sec  = f'<div class="card-sec"><div class="sec-lbl">⚗ Equipment Match</div><div class="tag-row">{eq_html}</div></div>' if eq_html else ""
    pop_sec = f'<div class="card-sec"><div class="sec-lbl">👥 Target Populations</div><div class="tag-row">{pop_html}</div></div>' if pop_html else ""
    sn      = f'<div class="strategic-note"><span>💡</span><div><strong>Strategic Note:</strong> {esc(g.get("strategic_note",""))}</div></div>' if g.get("strategic_note") else ""

    return f"""<article class="grant-card" data-conf="{conf}" data-citizenship="{g['citizenship']}" data-source="{g['source']}" data-status="{g.get('status','')}" data-urgency="{g.get('deadline_urgency','')}" data-cats="{' '.join(g.get('category',[]))}" style="animation-delay:{min(idx*0.04,0.6):.2f}s">
  <div class="card-accent c{min(conf//20,4)}"></div>
  <div class="card-body">

    <div class="card-toprow">
      <div class="meta-left">{source_badge(g['source'])} <span class="org-mono">{esc(g['org'])}</span></div>
      <div class="badges-right">{fit_badge(conf)} {citizenship_badge(g['citizenship'])}</div>
    </div>

    <h2 class="card-title">{esc(g['title'])}</h2>
    <div class="cat-row">{cat_html}</div>

    <div class="conf-section">
      <span class="conf-title">Research Match Confidence</span>
      {conf_bar(conf)}
    </div>

    <div class="card-grid3">
      <div class="cg"><label>Deadline</label><span class="{dlc}">{esc(g.get('deadline_display','TBD'))}{days_str}</span></div>
      <div class="cg"><label>Award Amount</label><span>{esc(g.get('amount_display','Varies'))}</span></div>
      <div class="cg"><label>Duration</label><span>{esc(g.get('duration','Varies'))}</span></div>
    </div>

    <div class="card-sec">
      <div class="sec-lbl">🎯 Why This Fits Your Research</div>
      <p class="fit-text">{esc(g.get('fit_rationale',''))}</p>
    </div>

    {eq_sec}
    {pop_sec}

    <div class="card-sec">
      <div class="sec-lbl">📋 Requirements</div>
      <div class="req-row">{pills(g.get('requirements',[]))}</div>
    </div>

    <div class="citizen-box">
      <strong>Citizenship / Visa Status:</strong> {esc(g.get('citizenship_note','Verify with funder.'))}
      <br><em class="citizen-src">Source: {esc(g.get('citizenship_source',''))}</em>
    </div>

    {sn}

  </div>
  <div class="card-foot">
    <span class="foot-status">Status: <strong>{g.get('status','—').upper()}</strong></span>
    <a href="{esc(g.get('url','#'))}" target="_blank" rel="noopener" class="apply-btn">View Grant →</a>
  </div>
</article>"""

# ── timeline rows ──────────────────────────────────────────────────────────

def tl_row(g):
    dlc  = deadline_cls(g.get("deadline_urgency","normal"))
    conf = g.get("confidence",0)
    bar  = "█" * (conf // 20) + "░" * (5 - conf // 20)
    days = g.get("days_until_deadline",9999)
    return f"""<div class="tl-row">
  <span class="tl-date {dlc}">{esc(g.get('deadline_display','TBD'))}</span>
  <span class="tl-name">{esc(g['title'])}</span>
  <span class="tl-org">{esc(g['org'].split('(')[0].strip()[:35])}</span>
  <span class="tl-bar" title="Confidence {conf}%">{bar}</span>
  <span class="tl-days {'tl-urgent' if days<=45 else ''}">{days if days < 9999 else '—'}d</span>
</div>"""

# ── search term legend ─────────────────────────────────────────────────────

def term_list(terms, cls):
    return "".join(f'<span class="term-chip {cls}">{esc(t)}</span>' for t in terms)

# ── assemble HTML ──────────────────────────────────────────────────────────

cards_html    = "\n".join(card(g,i) for i,g in enumerate(grants))
timeline_html = "\n".join(tl_row(g) for g in timeline)
nih_chips     = term_list(nih_terms, "tc-nih")
gov_chips     = term_list(gov_terms, "tc-gov")
total_terms   = len(nih_terms) + len(gov_terms)

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Grant Search Engine v2 · Vikaas Manjunath · MSU Kinesiology</title>
<link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,600;0,700;1,400&family=DM+Mono:wght@400;500&family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
:root {{
  --maroon:   #660000;
  --maroon-d: #3d0000;
  --maroon-m: #8a1111;
  --gold:     #c9a84c;
  --gold-l:   #e8c96f;
  --ink:      #18100a;
  --cream:    #f7f2ea;
  --surface:  #ffffff;
  --muted:    #6b5e50;
  --line:     #e2d9ce;
  --fit5:#065f46; --fit4:#0f766e; --fit3:#1d4ed8; --fit2:#92400e; --fit1:#4b5563;
}}

*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:'Outfit',sans-serif;background:var(--cream);color:var(--ink);font-size:14px;line-height:1.6;}}

/* HEADER */
header{{
  background:var(--maroon-d);
  background-image:radial-gradient(ellipse at 15% 60%,rgba(201,168,76,.14) 0%,transparent 55%),
                   radial-gradient(ellipse at 85% 20%,rgba(201,168,76,.07) 0%,transparent 50%);
  padding:40px 44px 30px;
  border-bottom:3px solid var(--gold);
}}
.h-inner{{max-width:1300px;margin:0 auto;}}
.h-eye{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:3px;text-transform:uppercase;color:var(--gold);opacity:.8;margin-bottom:10px;}}
header h1{{font-family:'Lora',serif;font-size:clamp(24px,4vw,42px);color:#fff;line-height:1.1;margin-bottom:14px;}}
header h1 em{{color:var(--gold-l);font-style:italic;}}
.h-chips{{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px;}}
.h-chip{{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.15);border-radius:4px;padding:3px 12px;font-family:'DM Mono',monospace;font-size:11px;color:rgba(255,255,255,.72);}}
.h-sub{{font-size:11px;color:rgba(255,255,255,.38);font-family:'DM Mono',monospace;}}

/* WRAP */
.wrap{{max-width:1300px;margin:0 auto;padding:30px 22px 80px;}}

/* STATS */
.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:13px;margin-bottom:26px;animation:fadeUp .4s ease both;}}
.stat{{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:16px 18px;text-align:center;position:relative;overflow:hidden;}}
.stat::after{{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:var(--maroon);}}
.stat.sg::after{{background:var(--fit5);}} .stat.st::after{{background:var(--fit4);}}
.stat.sb::after{{background:var(--fit3);}} .stat.sa::after{{background:#d97706;}}
.stat-n{{font-family:'Lora',serif;font-size:36px;line-height:1;color:var(--maroon);margin-bottom:3px;}}
.stat.sg .stat-n{{color:var(--fit5);}} .stat.st .stat-n{{color:var(--fit4);}}
.stat.sb .stat-n{{color:var(--fit3);}} .stat.sa .stat-n{{color:#d97706;}}
.stat-l{{font-size:11px;text-transform:uppercase;letter-spacing:1px;color:var(--muted);font-weight:500;}}

/* SEARCH TERMS PANEL */
.terms-panel{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:20px 24px;margin-bottom:26px;animation:fadeUp .4s .08s ease both;}}
.terms-panel summary{{font-family:'Lora',serif;font-size:17px;color:var(--maroon-d);cursor:pointer;list-style:none;display:flex;align-items:center;gap:8px;}}
.terms-panel summary::before{{content:"▶";font-size:10px;color:var(--muted);transition:transform .2s;}}
.terms-panel[open] summary::before{{transform:rotate(90deg);}}
.terms-body{{margin-top:16px;}}
.terms-group{{margin-bottom:14px;}}
.terms-group-label{{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:8px;}}
.term-chips{{display:flex;flex-wrap:wrap;gap:6px;}}
.term-chip{{padding:3px 10px;border-radius:4px;font-family:'DM Mono',monospace;font-size:11px;font-weight:500;}}
.tc-nih{{background:#dbeafe;color:#1e40af;border:1px solid #93c5fd;}}
.tc-gov{{background:#d1fae5;color:#065f46;border:1px solid #6ee7b7;}}
.terms-note{{margin-top:12px;font-size:12px;color:var(--muted);font-style:italic;}}

/* TIMELINE */
.timeline-sec{{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:22px 26px;margin-bottom:26px;animation:fadeUp .4s .12s ease both;}}
.sec-hd{{font-family:'Lora',serif;font-size:19px;color:var(--maroon-d);margin-bottom:14px;display:flex;align-items:baseline;gap:10px;}}
.sec-hd small{{font-family:'Outfit',sans-serif;font-size:12px;font-weight:400;color:var(--muted);}}
.tl-head{{display:grid;grid-template-columns:200px 1fr 180px 70px 60px;gap:10px;padding:5px 10px;font-family:'DM Mono',monospace;font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);margin-bottom:4px;}}
.tl-row{{display:grid;grid-template-columns:200px 1fr 180px 70px 60px;gap:10px;padding:9px 10px;border-radius:6px;background:var(--cream);margin-bottom:5px;border-left:4px solid var(--line);align-items:center;font-size:12px;transition:background .15s;}}
.tl-row:hover{{background:#efe9df;}}
.tl-date{{font-family:'DM Mono',monospace;font-size:11px;font-weight:500;}}
.tl-name{{font-weight:500;}}
.tl-org{{color:var(--muted);font-size:11px;}}
.tl-bar{{font-family:'DM Mono',monospace;font-size:11px;color:var(--gold);letter-spacing:-1px;}}
.tl-days{{font-family:'DM Mono',monospace;font-size:11px;color:var(--muted);text-align:right;}}
.tl-urgent{{color:#991b1b;font-weight:700;}}

/* CONTROLS */
.controls{{display:flex;flex-wrap:wrap;gap:9px;align-items:center;margin-bottom:22px;animation:fadeUp .4s .16s ease both;}}
.ctrl-lbl{{font-size:11px;text-transform:uppercase;letter-spacing:1.5px;color:var(--muted);font-weight:600;}}
.ctrl-btn{{padding:7px 15px;border-radius:100px;border:1.5px solid var(--line);background:var(--surface);font-family:'Outfit',sans-serif;font-size:12px;font-weight:500;color:var(--muted);cursor:pointer;transition:all .15s;white-space:nowrap;}}
.ctrl-btn:hover{{border-color:var(--maroon);color:var(--maroon);}}
.ctrl-btn.active{{background:var(--maroon);border-color:var(--maroon);color:#fff;}}
.search-wrap{{position:relative;flex:1;min-width:190px;max-width:300px;}}
.search-wrap input{{width:100%;padding:8px 13px 8px 32px;border-radius:8px;border:1.5px solid var(--line);font-family:'Outfit',sans-serif;font-size:13px;background:var(--surface);outline:none;transition:border-color .15s;}}
.search-wrap input:focus{{border-color:var(--maroon);}}
.s-icon{{position:absolute;left:9px;top:50%;transform:translateY(-50%);color:var(--muted);font-size:13px;}}
.sort-sel{{margin-left:auto;padding:7px 13px;border:1.5px solid var(--line);border-radius:8px;font-family:'Outfit',sans-serif;font-size:12px;background:var(--surface);cursor:pointer;outline:none;}}
.result-count{{font-family:'DM Mono',monospace;font-size:11px;color:var(--muted);padding:0 4px;}}

/* CARDS */
.grants-grid{{display:grid;gap:18px;}}
.grant-card{{background:var(--surface);border:1px solid var(--line);border-radius:13px;overflow:hidden;box-shadow:0 2px 10px rgba(102,0,0,.05);display:flex;flex-direction:column;transition:box-shadow .2s,transform .2s;animation:fadeUp .4s ease both;}}
.grant-card:hover{{box-shadow:0 10px 32px rgba(102,0,0,.14);transform:translateY(-2px);}}
.card-accent{{height:5px;flex-shrink:0;}}
.c4{{background:var(--fit5);}} .c3{{background:var(--fit4);}} .c2{{background:var(--fit3);}}
.c1{{background:var(--fit2);}} .c0{{background:var(--fit1);}}
.card-body{{padding:20px 24px;flex:1;}}
.card-toprow{{display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:8px;}}
.meta-left{{display:flex;align-items:center;gap:9px;flex-wrap:wrap;}}
.org-mono{{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:1.2px;text-transform:uppercase;color:var(--muted);}}
.badges-right{{display:flex;gap:5px;flex-wrap:wrap;align-items:center;}}
.card-title{{font-family:'Lora',serif;font-size:19px;color:var(--ink);line-height:1.2;margin-bottom:8px;}}
.cat-row{{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:12px;}}
.cat-tag{{background:rgba(102,0,0,.07);color:var(--maroon);border-radius:3px;padding:2px 7px;font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.4px;}}

/* Confidence */
.conf-section{{margin-bottom:14px;}}
.conf-title{{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);display:block;margin-bottom:5px;}}
.conf-wrap{{display:flex;align-items:center;gap:10px;}}
.conf-bar{{height:6px;border-radius:3px;transition:width .6s ease;}}
.conf-label{{font-family:'DM Mono',monospace;font-size:11px;color:var(--muted);white-space:nowrap;}}

/* Grid */
.card-grid3{{display:grid;grid-template-columns:repeat(3,1fr);gap:11px;padding:12px 0;border-top:1px dashed var(--line);border-bottom:1px dashed var(--line);margin-bottom:14px;}}
.cg label{{display:block;font-family:'DM Mono',monospace;font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:var(--muted);margin-bottom:3px;}}
.cg span{{font-size:13px;font-weight:500;}}
.dl-urgent{{color:#991b1b;font-weight:700;}} .dl-soon{{color:#b45309;font-weight:600;}}
.dl-normal{{color:var(--ink);}} .dl-future{{color:var(--muted);}}
.dl-none{{color:var(--muted);font-style:italic;}} .dl-exp{{color:#9ca3af;text-decoration:line-through;}}
.days-away{{color:var(--muted);font-size:11px;font-weight:400;}}

/* Card sections */
.card-sec{{margin-bottom:12px;}}
.sec-lbl{{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:1.5px;text-transform:uppercase;color:var(--maroon);margin-bottom:5px;font-weight:500;}}
.fit-text{{font-size:13px;line-height:1.65;color:#2d1f0f;}}
.tag-row{{display:flex;flex-wrap:wrap;gap:5px;}}
.equip-tag,.pop-tag{{background:var(--cream);border:1px solid var(--line);border-radius:3px;padding:3px 9px;font-size:11px;color:var(--muted);font-family:'DM Mono',monospace;}}
.req-row{{display:flex;flex-wrap:wrap;gap:5px;}}
.req-pill{{background:#faf7f3;border:1px solid var(--line);border-radius:3px;padding:3px 9px;font-size:11px;color:var(--muted);}}

/* Citizenship box */
.citizen-box{{background:#f0fdf4;border:1px solid #bbf7d0;border-radius:7px;padding:10px 13px;font-size:12.5px;color:#14532d;margin-bottom:11px;line-height:1.6;}}
.citizen-src{{font-family:'DM Mono',monospace;font-size:10px;color:#166534;opacity:.7;}}

/* Strategic note */
.strategic-note{{background:#fffbeb;border:1px solid #fde68a;border-radius:7px;padding:10px 13px;font-size:12.5px;color:#78350f;display:flex;gap:8px;line-height:1.6;}}

/* Badges */
.badge{{padding:3px 9px;border-radius:100px;font-size:10px;font-weight:700;letter-spacing:.3px;text-transform:uppercase;white-space:nowrap;}}
.b-green{{background:#dcfce7;color:#166534;}} .b-emerald{{background:#d1fae5;color:#065f46;}}
.b-teal{{background:#ccfbf1;color:#0f766e;}} .b-blue{{background:#dbeafe;color:#1d4ed8;}}
.b-slate{{background:#f1f5f9;color:#475569;}} .b-stone{{background:#f5f5f4;color:#57534e;}}
.b-amber{{background:#fef3c7;color:#92400e;}} .b-gray{{background:#f3f4f6;color:#6b7280;}}
.src-badge{{font-family:'DM Mono',monospace;font-size:9px;letter-spacing:1px;text-transform:uppercase;padding:2px 7px;border-radius:3px;font-weight:600;}}
.src-cur{{background:rgba(102,0,0,.08);color:var(--maroon);}}
.src-nih{{background:#dbeafe;color:#1e40af;}}
.src-gov{{background:#d1fae5;color:#065f46;}}

/* Card footer */
.card-foot{{display:flex;align-items:center;justify-content:space-between;padding:11px 24px;background:#faf7f3;border-top:1px solid var(--line);}}
.foot-status{{font-size:11px;color:var(--muted);font-family:'DM Mono',monospace;}}
.apply-btn{{padding:8px 18px;background:var(--maroon);color:#fff;text-decoration:none;border-radius:6px;font-size:12px;font-weight:600;transition:background .15s;white-space:nowrap;}}
.apply-btn:hover{{background:var(--maroon-m);}}

/* Empty */
.empty{{text-align:center;padding:60px 20px;color:var(--muted);font-size:15px;display:none;}}

/* Animations */
@keyframes fadeUp{{from{{opacity:0;transform:translateY(16px);}}to{{opacity:1;transform:translateY(0);}}}}

/* Responsive */
@media(max-width:768px){{
  header{{padding:22px 16px 18px;}}
  .wrap{{padding:18px 14px 50px;}}
  .card-grid3{{grid-template-columns:1fr 1fr;}}
  .tl-head,.tl-row{{grid-template-columns:140px 1fr 80px;}}
  .tl-org,.tl-bar{{display:none;}}
}}
</style>
</head>
<body>

<header>
<div class="h-inner">
  <div class="h-eye">🔬 Grant Search Engine v2 · Auto-built {TODAY.strftime('%Y-%m-%d')} · {total_terms} search terms across 3 sources</div>
  <h1>Cardiovascular Health<br><em>Grant Intelligence Dashboard</em></h1>
  <div class="h-chips">
    <span class="h-chip">Vikaas Manjunath — PhD Student · MSU Kinesiology</span>
    <span class="h-chip">F-1 Visa · India</span>
    <span class="h-chip">Exercise Physiology · Vascular Health · Metabolic Disease · Intellectual Disability</span>
    <span class="h-chip">SphygmoCor · Vascular Ultrasound · NIRS · Accelerometry · Metabolic Cart</span>
  </div>
  <div class="h-sub">Generated: {generated} · {total} grants indexed · Citizenship filter: Unrestricted + Unspecified only (US-citizen-only grants excluded)</div>
</div>
</header>

<div class="wrap">

<!-- STATS -->
<div class="stats">
  <div class="stat sg"><div class="stat-n">{len(unrestricted)}</div><div class="stat-l">Unrestricted ✓</div></div>
  <div class="stat sa"><div class="stat-n">{len(unspecified)}</div><div class="stat-l">Unspecified — Verify</div></div>
  <div class="stat st"><div class="stat-n">{len(high_conf)}</div><div class="stat-l">High Confidence ≥70%</div></div>
  <div class="stat"><div class="stat-n">{total}</div><div class="stat-l">Total Indexed</div></div>
  <div class="stat sb"><div class="stat-n">{len(urgent)}</div><div class="stat-l">Deadlines ≤90 Days</div></div>
  <div class="stat"><div class="stat-n">{len(nih_terms) + len(gov_terms)}</div><div class="stat-l">Search Terms Used</div></div>
</div>

<!-- SEARCH TERMS PANEL -->
<details class="terms-panel">
  <summary>📡 Search Terms &amp; Data Sources Used</summary>
  <div class="terms-body">
    <div class="terms-group">
      <div class="terms-group-label">NIH Reporter API — {len(nih_terms)} query clusters (searches active F31, F99, T32, R15, R21 grants)</div>
      <div class="term-chips">{nih_chips}</div>
    </div>
    <div class="terms-group">
      <div class="terms-group-label">Grants.gov API — {len(gov_terms)} keyword searches (posted + forecasted federal opportunities)</div>
      <div class="term-chips">{gov_chips}</div>
    </div>
    <div class="terms-note">
      ✔ Curated database: 17 grants hand-verified against official funder websites — citizenship confirmed for each.<br>
      🔄 NIH Reporter + Grants.gov: queried live every Monday by GitHub Actions — results appear as additional cards when APIs return data.<br>
      📊 Confidence score: percentage of your research profile terms (vascular, metabolic, exercise, accelerometry, populations, equipment) matched in each grant's text.
    </div>
  </div>
</details>

<!-- TIMELINE -->
<div class="timeline-sec">
  <div class="sec-hd">📅 Deadline Timeline <small>eligible grants with known deadlines · sorted by urgency</small></div>
  <div class="tl-head"><span>Deadline</span><span>Grant</span><span>Organization</span><span>Match</span><span>Days</span></div>
  {timeline_html if timeline_html else '<p style="color:var(--muted);font-size:13px;padding:10px 0;">No near-term deadlines found in current results.</p>'}
</div>

<!-- CONTROLS -->
<div class="controls">
  <span class="ctrl-lbl">Filter:</span>
  <button class="ctrl-btn active" data-f="all">All ({total})</button>
  <button class="ctrl-btn" data-f="unrestricted">✓ Unrestricted Only</button>
  <button class="ctrl-btn" data-f="high-conf">≥70% Confidence</button>
  <button class="ctrl-btn" data-f="active">Active Now</button>
  <button class="ctrl-btn" data-f="upcoming">Upcoming</button>
  <button class="ctrl-btn" data-cat="cardiovascular">Cardiovascular</button>
  <button class="ctrl-btn" data-cat="vascular">Vascular</button>
  <button class="ctrl-btn" data-cat="metabolic">Metabolic</button>
  <button class="ctrl-btn" data-cat="intellectual disability">Intellectual Disability</button>
  <button class="ctrl-btn" data-cat="aging">Aging</button>
  <div class="search-wrap">
    <span class="s-icon">🔍</span>
    <input type="text" id="searchInput" placeholder="Search grants, orgs, methods…">
  </div>
  <select class="sort-sel" id="sortSel">
    <option value="conf">Sort: Confidence</option>
    <option value="deadline">Sort: Deadline</option>
    <option value="amount">Sort: Amount</option>
  </select>
  <span class="result-count" id="resultCount">{total} shown</span>
</div>

<!-- CARDS -->
<div class="grants-grid" id="grantsGrid">
{cards_html}
</div>
<div class="empty" id="emptyMsg">No grants match the current filters. Try broadening your search.</div>

</div>

<script>
const cards = Array.from(document.querySelectorAll('.grant-card'));
let activeF = 'all', activeCat = null, searchQ = '', sortBy = 'conf';

function applyFilters() {{
  let vis = cards;
  if(activeF === 'unrestricted') vis = vis.filter(c => c.dataset.citizenship === 'unrestricted');
  if(activeF === 'high-conf')    vis = vis.filter(c => parseInt(c.dataset.conf||0) >= 70);
  if(activeF === 'active')       vis = vis.filter(c => c.dataset.status === 'active');
  if(activeF === 'upcoming')     vis = vis.filter(c => c.dataset.status === 'upcoming');
  if(activeCat) vis = vis.filter(c => (c.dataset.cats||'').includes(activeCat));
  if(searchQ) {{
    const q = searchQ.toLowerCase();
    vis = vis.filter(c => c.innerText.toLowerCase().includes(q));
  }}
  const visSet = new Set(vis);
  cards.forEach(c => c.style.display = visSet.has(c) ? '' : 'none');
  document.getElementById('resultCount').textContent = vis.length + ' shown';
  document.getElementById('emptyMsg').style.display = vis.length === 0 ? 'block' : 'none';
}}

document.querySelectorAll('.ctrl-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.ctrl-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    if(btn.dataset.f)   {{ activeF = btn.dataset.f; activeCat = null; }}
    if(btn.dataset.cat) {{ activeCat = btn.dataset.cat; activeF = 'all'; }}
    applyFilters();
  }});
}});

document.getElementById('searchInput').addEventListener('input', e => {{ searchQ = e.target.value; applyFilters(); }});

document.getElementById('sortSel').addEventListener('change', e => {{
  sortBy = e.target.value;
  const grid = document.getElementById('grantsGrid');
  Array.from(grid.children)
    .sort((a,b) => {{
      if(sortBy==='conf')     return (parseInt(b.dataset.conf)||0) - (parseInt(a.dataset.conf)||0);
      if(sortBy==='deadline') return (parseInt(a.dataset.urgency==='no_deadline'?99999:0)) - 0;
      return 0;
    }})
    .forEach(c => grid.appendChild(c));
}});
</script>
</body>
</html>"""

with open(dest, "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"[✓] index.html written ({os.path.getsize(dest)//1024} KB)")
print(f"    {total} grant cards | {len(unrestricted)} unrestricted | {len(high_conf)} high-confidence")
print(f"    Search terms: {len(nih_terms)} NIH clusters + {len(gov_terms)} Grants.gov terms = {total_terms} total")
