#!/usr/bin/env python3
"""
Build Dashboard — minimal white aesthetic
Reads grants_results.json, writes index.html
"""

import json, datetime, os

TODAY = datetime.date.today()
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(SCRIPT_DIR, "grants_results.json")) as f:
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

timeline = sorted(
    [g for g in grants if g.get("deadline") and 0 < g.get("days_until_deadline",9999) < 9999],
    key=lambda g: g["days_until_deadline"]
)[:10]

def esc(s):
    return str(s).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def citizenship_pill(c):
    if c == "unrestricted":
        return '<span class="pill pill-green">F-1 eligible</span>'
    if c in ("unspecified","check"):
        return '<span class="pill pill-amber">Verify citizenship</span>'
    return '<span class="pill pill-gray">Unknown</span>'

def conf_pill(conf):
    if conf >= 80: return f'<span class="pill pill-green">{conf}% match</span>'
    if conf >= 65: return f'<span class="pill pill-teal">{conf}% match</span>'
    if conf >= 45: return f'<span class="pill pill-blue">{conf}% match</span>'
    return f'<span class="pill pill-gray">{conf}% match</span>'

def status_dot(u):
    if u == "urgent": return '<span class="dot dot-red"></span>'
    if u == "soon":   return '<span class="dot dot-amber"></span>'
    if u == "active": return '<span class="dot dot-green"></span>'
    return '<span class="dot dot-gray"></span>'

def deadline_color(u):
    return {"urgent":"#c0392b","soon":"#b45309","normal":"#18100a","future":"#888"}.get(u,"#18100a")

def req_tags(reqs):
    return "".join(f'<span class="tag">{esc(r)}</span>' for r in reqs)

def eq_tags(eq):
    return "".join(f'<span class="tag tag-eq">{esc(e)}</span>' for e in eq) if eq else ""

def pop_tags(pp):
    return "".join(f'<span class="tag tag-pop">{esc(p)}</span>' for p in pp) if pp else ""

def source_label(src):
    m = {"curated":"Curated & verified","nih_reporter":"NIH Reporter","grants_gov":"Grants.gov"}
    return m.get(src, src)

def card(g, idx):
    conf  = g.get("confidence", 0)
    days  = g.get("days_until_deadline", 9999)
    urg   = g.get("deadline_urgency","normal")
    dl_color = deadline_color(urg)
    days_str = f" · {days}d" if 0 < days < 9999 else ""

    eq_html  = eq_tags(g.get("equipment_relevance",[]))
    pop_html = pop_tags(g.get("populations",[]))
    eq_sec   = f'<div class="card-field"><div class="field-label">Equipment match</div><div class="tag-row">{eq_html}</div></div>' if eq_html else ""
    pop_sec  = f'<div class="card-field"><div class="field-label">Populations</div><div class="tag-row">{pop_html}</div></div>' if pop_html else ""
    sn       = f'<div class="strategic-note">{esc(g.get("strategic_note",""))}</div>' if g.get("strategic_note") else ""

    return f"""<div class="card" data-conf="{conf}" data-citizenship="{g['citizenship']}" data-source="{g['source']}" data-status="{g.get('status','')}" data-urgency="{urg}" data-cats="{' '.join(g.get('category',[]))}">
  <div class="card-header">
    <div class="card-header-left">
      <div class="org-label">{esc(g['org'])}</div>
      <h2 class="card-title">{esc(g['title'])}</h2>
    </div>
    <div class="card-header-right">
      {conf_pill(conf)}
      {citizenship_pill(g['citizenship'])}
    </div>
  </div>

  <div class="card-meta">
    <div class="meta-item">
      <span class="meta-label">Deadline</span>
      <span class="meta-value" style="color:{dl_color}">{esc(g.get('deadline_display','TBD'))}{days_str}</span>
    </div>
    <div class="meta-item">
      <span class="meta-label">Amount</span>
      <span class="meta-value">{esc(g.get('amount_display','Varies'))}</span>
    </div>
    <div class="meta-item">
      <span class="meta-label">Duration</span>
      <span class="meta-value">{esc(g.get('duration','Varies'))}</span>
    </div>
    <div class="meta-item">
      <span class="meta-label">Source</span>
      <span class="meta-value">{source_label(g['source'])}</span>
    </div>
  </div>

  <div class="card-field">
    <div class="field-label">What they expect from the applicant</div>
    <ul class="expect-list">{chr(10).join(f'<li>{esc(item)}</li>' for item in g.get('what_they_expect', g.get('requirements', [])))}</ul>
  </div>

  <div class="card-field">
    <div class="field-label">How you fit</div>
    <p class="field-text">{esc(g.get('how_you_fit', g.get('fit_rationale', '')))}</p>
  </div>

  <div class="card-field">
    <div class="field-label">Citizenship / visa</div>
    <p class="field-text">{esc(g.get('citizenship_note',''))} <span class="cite">— {esc(g.get('citizenship_source',''))}</span></p>
  </div>

  {eq_sec}
  {pop_sec}

  <div class="card-field">
    <div class="field-label">Requirements</div>
    <div class="tag-row">{req_tags(g.get('requirements',[]))}</div>
  </div>

  {sn}

  <div class="card-footer">
    <a href="{esc(g.get('url','#'))}" target="_blank" rel="noopener" class="apply-link">View grant &rarr;</a>
    <span class="status-label">{g.get('status','').upper()}</span>
  </div>
</div>"""

cards_html   = "\n".join(card(g,i) for i,g in enumerate(grants))
tl_rows      = ""
for g in timeline:
    days = g.get("days_until_deadline",9999)
    urg  = g.get("deadline_urgency","normal")
    dc   = deadline_color(urg)
    tl_rows += f"""<div class="tl-row">
  <span class="tl-date" style="color:{dc}">{esc(g.get('deadline_display','TBD'))}</span>
  <span class="tl-name">{esc(g['title'])}</span>
  <span class="tl-days" style="color:{dc}">{days}d</span>
</div>"""

total_terms = len(nih_terms) + len(gov_terms)

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Grant Search · Vikaas Manjunath · MSU</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&display=swap" rel="stylesheet">
<style>
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  font-family: 'Inter', -apple-system, sans-serif;
  background: #ffffff;
  color: #111;
  font-size: 14px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}}

a {{ color: inherit; text-decoration: none; }}

/* ── HEADER ── */
.header {{
  border-bottom: 1px solid #e8e8e8;
  padding: 48px 48px 36px;
  max-width: 1100px;
  margin: 0 auto;
}}

.header-eyebrow {{
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #888;
  margin-bottom: 12px;
}}

.header h1 {{
  font-size: 28px;
  font-weight: 300;
  color: #111;
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin-bottom: 8px;
}}

.header-sub {{
  font-size: 13px;
  color: #888;
  margin-bottom: 20px;
}}

.header-chips {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}}

.header-chip {{
  font-size: 11px;
  color: #555;
  border: 1px solid #e0e0e0;
  border-radius: 100px;
  padding: 3px 10px;
}}

/* ── WRAP ── */
.wrap {{
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 48px 80px;
}}

/* ── STATS ── */
.stats {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 1px;
  background: #e8e8e8;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  overflow: hidden;
  margin: 36px 0 32px;
}}

.stat {{
  background: #fff;
  padding: 20px 20px 16px;
}}

.stat-n {{
  font-size: 30px;
  font-weight: 300;
  color: #111;
  letter-spacing: -0.03em;
  line-height: 1;
  margin-bottom: 4px;
}}

.stat-l {{
  font-size: 11px;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}}

/* ── TIMELINE ── */
.section {{
  margin-bottom: 32px;
}}

.section-title {{
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #888;
  margin-bottom: 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
}}

.tl-row {{
  display: grid;
  grid-template-columns: 220px 1fr 60px;
  gap: 16px;
  align-items: baseline;
  padding: 9px 0;
  border-bottom: 1px solid #f5f5f5;
  font-size: 13px;
}}

.tl-date {{ font-weight: 500; font-size: 12px; }}
.tl-name {{ color: #333; }}
.tl-days {{ text-align: right; font-size: 12px; font-weight: 500; }}

/* ── CONTROLS ── */
.controls {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 24px;
}}

.filter-btn {{
  padding: 6px 14px;
  border-radius: 100px;
  border: 1px solid #e0e0e0;
  background: #fff;
  font-family: inherit;
  font-size: 12px;
  color: #555;
  cursor: pointer;
  transition: all 0.12s;
  white-space: nowrap;
}}

.filter-btn:hover {{ border-color: #111; color: #111; }}
.filter-btn.active {{ background: #111; border-color: #111; color: #fff; }}

.search-box {{
  flex: 1;
  min-width: 180px;
  max-width: 280px;
  padding: 6px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 100px;
  font-family: inherit;
  font-size: 13px;
  color: #111;
  background: #fff;
  outline: none;
  transition: border-color 0.12s;
}}

.search-box:focus {{ border-color: #111; }}

.sort-box {{
  margin-left: auto;
  padding: 6px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  font-family: inherit;
  font-size: 12px;
  color: #555;
  background: #fff;
  cursor: pointer;
  outline: none;
}}

.count-label {{
  font-size: 12px;
  color: #aaa;
}}

/* ── CARDS ── */
.cards-list {{
  display: flex;
  flex-direction: column;
  gap: 0;
}}

.card {{
  border-bottom: 1px solid #f0f0f0;
  padding: 28px 0;
  transition: background 0.12s;
}}

.card:first-child {{ border-top: 1px solid #f0f0f0; }}

.card-header {{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}}

.org-label {{
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #888;
  margin-bottom: 4px;
}}

.card-title {{
  font-size: 17px;
  font-weight: 500;
  color: #111;
  letter-spacing: -0.01em;
  line-height: 1.3;
}}

.card-header-right {{
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  flex-shrink: 0;
  align-items: flex-start;
}}

/* Pills */
.pill {{
  font-size: 11px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 100px;
  white-space: nowrap;
}}

.pill-green  {{ background: #e8f5e9; color: #2e7d32; }}
.pill-teal   {{ background: #e0f2f1; color: #00695c; }}
.pill-blue   {{ background: #e3f2fd; color: #1565c0; }}
.pill-amber  {{ background: #fff8e1; color: #f57f17; }}
.pill-gray   {{ background: #f5f5f5; color: #666; }}

/* Meta row */
.card-meta {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 14px 16px;
  margin-bottom: 18px;
}}

.meta-item {{ display: flex; flex-direction: column; gap: 2px; }}
.meta-label {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; color: #aaa; }}
.meta-value {{ font-size: 13px; color: #111; font-weight: 500; }}

/* Fields */
.card-field {{ margin-bottom: 14px; }}

.field-label {{
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #aaa;
  margin-bottom: 5px;
}}

.field-text {{
  font-size: 13px;
  color: #333;
  line-height: 1.65;
}}

.cite {{ font-size: 11px; color: #bbb; }}

/* Tags */
.tag-row {{ display: flex; flex-wrap: wrap; gap: 5px; }}

.tag {{
  font-size: 11px;
  color: #555;
  background: #f5f5f5;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  padding: 2px 8px;
}}

.tag-eq  {{ background: #f0f4ff; color: #3730a3; border-color: #e0e7ff; }}
.tag-pop {{ background: #f0fdf4; color: #166534; border-color: #d1fae5; }}

/* Strategic note */
.strategic-note {{
  font-size: 12px;
  color: #666;
  background: #fffbf0;
  border-left: 2px solid #f59e0b;
  border-radius: 0;
  padding: 10px 14px;
  margin-bottom: 14px;
  line-height: 1.6;
}}

/* Card footer */
.card-footer {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 14px;
  border-top: 1px solid #f5f5f5;
  margin-top: 4px;
}}

.apply-link {{
  font-size: 13px;
  font-weight: 500;
  color: #111;
  border-bottom: 1px solid #111;
  padding-bottom: 1px;
  transition: opacity 0.12s;
}}

.apply-link:hover {{ opacity: 0.5; }}

.status-label {{
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #bbb;
}}

/* Dots */
.dot {{
  display: inline-block;
  width: 7px; height: 7px;
  border-radius: 50%;
  margin-right: 5px;
}}
.dot-green {{ background: #22c55e; }}
.dot-amber {{ background: #f59e0b; }}
.dot-red   {{ background: #ef4444; }}
.dot-gray  {{ background: #d1d5db; }}

/* Empty */
.empty {{
  text-align: center;
  padding: 60px 0;
  color: #aaa;
  font-size: 14px;
  display: none;
}}

/* Search terms details */
.terms-section {{
  margin-bottom: 32px;
}}

details summary {{
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #888;
  cursor: pointer;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;
  list-style: none;
  display: flex;
  align-items: center;
  gap: 8px;
}}

details summary::-webkit-details-marker {{ display: none; }}
details summary::before {{ content: "+"; font-size: 14px; }}
details[open] summary::before {{ content: "−"; }}

.terms-body {{ padding-top: 14px; display: flex; flex-direction: column; gap: 12px; }}
.terms-group-lbl {{ font-size: 11px; color: #aaa; margin-bottom: 6px; }}
.term-chips {{ display: flex; flex-wrap: wrap; gap: 5px; }}
.tc {{ font-size: 11px; padding: 3px 10px; border-radius: 100px; }}
.tc-nih {{ background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }}
.tc-gov {{ background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }}

@media(max-width:768px) {{
  .header {{ padding: 28px 20px 24px; }}
  .wrap {{ padding: 0 20px 60px; }}
  .tl-row {{ grid-template-columns: 160px 1fr 50px; }}
  .card-meta {{ grid-template-columns: 1fr 1fr; }}
}}

.expect-list {{
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 0;
}}

.expect-list li {{
  font-size: 13px;
  color: #333;
  padding-left: 14px;
  position: relative;
  line-height: 1.55;
}}

.expect-list li::before {{
  content: "\2013";
  position: absolute;
  left: 0;
  color: #bbb;
}}
</style>
</head>
<body>

<div class="header">
  <div class="header-eyebrow">Grant search engine &middot; {TODAY.strftime('%B %d, %Y')} &middot; {total_terms} search terms</div>
  <h1>Cardiovascular health research funding</h1>
  <div class="header-sub">Vikaas Manjunath &middot; PhD Student, Kinesiology, MSU &middot; F-1 visa &middot; Generated {generated}</div>
  <div class="header-chips">
    <span class="header-chip">Exercise physiology</span>
    <span class="header-chip">Vascular health (FMD / PWV / cIMT)</span>
    <span class="header-chip">Metabolic syndrome</span>
    <span class="header-chip">Intellectual disability</span>
    <span class="header-chip">Accelerometry</span>
    <span class="header-chip">NIRS</span>
    <span class="header-chip">SphygmoCor</span>
    <span class="header-chip">Older adults</span>
  </div>
</div>

<div class="wrap">

<div class="stats">
  <div class="stat"><div class="stat-n">{total}</div><div class="stat-l">Total grants</div></div>
  <div class="stat"><div class="stat-n">{len(unrestricted)}</div><div class="stat-l">F-1 eligible</div></div>
  <div class="stat"><div class="stat-n">{len(unspecified)}</div><div class="stat-l">Verify citizenship</div></div>
  <div class="stat"><div class="stat-n">{len(high_conf)}</div><div class="stat-l">High confidence</div></div>
  <div class="stat"><div class="stat-n">{len(urgent)}</div><div class="stat-l">Due within 90d</div></div>
</div>

<div class="section">
  <div class="section-title">Upcoming deadlines</div>
  {tl_rows if tl_rows else '<p style="font-size:13px;color:#aaa;padding:12px 0">No near-term deadlines found.</p>'}
</div>

<div class="terms-section">
  <details>
    <summary>Search terms used ({total_terms} total)</summary>
    <div class="terms-body">
      <div>
        <div class="terms-group-lbl">NIH Reporter API &mdash; {len(nih_terms)} query clusters</div>
        <div class="term-chips">{''.join(f'<span class="tc tc-nih">{esc(t)}</span>' for t in nih_terms)}</div>
      </div>
      <div>
        <div class="terms-group-lbl">Grants.gov API &mdash; {len(gov_terms)} keyword searches</div>
        <div class="term-chips">{''.join(f'<span class="tc tc-gov">{esc(t)}</span>' for t in gov_terms)}</div>
      </div>
    </div>
  </details>
</div>

<div class="controls">
  <button class="filter-btn active" data-f="all">All ({total})</button>
  <button class="filter-btn" data-f="unrestricted">F-1 eligible</button>
  <button class="filter-btn" data-f="high-conf">High confidence</button>
  <button class="filter-btn" data-f="active">Active now</button>
  <button class="filter-btn" data-cat="cardiovascular">Cardiovascular</button>
  <button class="filter-btn" data-cat="vascular">Vascular</button>
  <button class="filter-btn" data-cat="metabolic">Metabolic</button>
  <button class="filter-btn" data-cat="intellectual disability">Intellectual disability</button>
  <input type="text" class="search-box" id="searchInput" placeholder="Search grants...">
  <select class="sort-box" id="sortSel">
    <option value="conf">Sort by confidence</option>
    <option value="deadline">Sort by deadline</option>
  </select>
  <span class="count-label" id="countLabel">{total} shown</span>
</div>

<div class="cards-list" id="cardsList">
{cards_html}
</div>
<div class="empty" id="emptyMsg">No grants match the current filters.</div>

</div>

<script>
const cards = Array.from(document.querySelectorAll('.card'));
let activeF = 'all', activeCat = null, searchQ = '';

function applyFilters() {{
  let vis = cards;
  if (activeF === 'unrestricted') vis = vis.filter(c => c.dataset.citizenship === 'unrestricted');
  if (activeF === 'high-conf')    vis = vis.filter(c => parseInt(c.dataset.conf||0) >= 70);
  if (activeF === 'active')       vis = vis.filter(c => c.dataset.status === 'active');
  if (activeCat) vis = vis.filter(c => (c.dataset.cats||'').includes(activeCat));
  if (searchQ) {{
    const q = searchQ.toLowerCase();
    vis = vis.filter(c => c.innerText.toLowerCase().includes(q));
  }}
  const visSet = new Set(vis);
  cards.forEach(c => c.style.display = visSet.has(c) ? '' : 'none');
  document.getElementById('countLabel').textContent = vis.length + ' shown';
  document.getElementById('emptyMsg').style.display = vis.length === 0 ? 'block' : 'none';
}}

document.querySelectorAll('.filter-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    if (btn.dataset.f)   {{ activeF = btn.dataset.f; activeCat = null; }}
    if (btn.dataset.cat) {{ activeCat = btn.dataset.cat; activeF = 'all'; }}
    applyFilters();
  }});
}});

document.getElementById('searchInput').addEventListener('input', e => {{
  searchQ = e.target.value;
  applyFilters();
}});

document.getElementById('sortSel').addEventListener('change', e => {{
  const grid = document.getElementById('cardsList');
  Array.from(grid.children)
    .sort((a, b) => e.target.value === 'conf'
      ? (parseInt(b.dataset.conf)||0) - (parseInt(a.dataset.conf)||0)
      : (parseInt(a.dataset.urgency==='no_deadline'?99999:a.dataset.conf)) - 0)
    .forEach(c => grid.appendChild(c));
}});
</script>

</body>
</html>"""

out_path = os.path.join(SCRIPT_DIR, "index.html")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(HTML)

print(f"[ok] index.html written ({os.path.getsize(out_path)//1024} KB) — {total} cards")
