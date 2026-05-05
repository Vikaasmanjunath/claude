# 🔬 Grant Search Engine v2
### Vikaas Manjunath · PhD Student · MSU Kinesiology

Automated cardiovascular health grant discovery — **F-1 visa eligible grants only**.  
Runs 21 search terms across 3 data sources every Monday. Builds and deploys a live filterable dashboard.

---

## 🌐 Live Dashboard
**[→ https://YOUR_USERNAME.github.io/vikaas-grant-search](https://YOUR_USERNAME.github.io/vikaas-grant-search)**  
*(Replace YOUR_USERNAME after setup)*

---

## ⚡ Setup (one time, ~10 minutes)

### 1. Create the Repository
- Go to **github.com** → click **"+"** → **New repository**
- Name: `vikaas-grant-search`
- Set to: **Public**
- Do NOT check "Initialize with README"
- Click **Create repository**

### 2. Upload Files
On your new repo page, click **"Add file → Upload files"** and upload:
```
index.html
grants_results.json
search_grants.py
build_dashboard.py
README.md
last_run.txt      ← create this as an empty file
```

### 3. Create the Workflow File
- Click **"Add file → Create new file"**
- In the filename box, type exactly: `.github/workflows/grant_search.yml`
- Paste the contents of `grant_search.yml` from this package
- Click **"Commit new file"**

### 4. Enable GitHub Pages
- Go to **Settings → Pages** (left sidebar)
- Source: **GitHub Actions**
- Click **Save**

### 5. Run Manually (first time)
- Go to **Actions tab**
- Click **"🔬 Automated Grant Search v2"**
- Click **"Run workflow" → "Run workflow"**
- Wait ~2 minutes → your dashboard is live

**From then on: every Monday at 8 AM UTC, it runs automatically.**

---

## 📡 Search Terms Used (21 total)

### NIH Reporter API — 9 Query Clusters
Searches active grants with activity codes: `F31, F99, T32, R15, R21`

| # | Cluster |
|---|---------|
| 1 | `cardiovascular exercise physical activity vascular` |
| 2 | `arterial stiffness endothelial function pulse wave velocity flow-mediated dilation` |
| 3 | `metabolic syndrome diabetes obesity cardiometabolic exercise intervention` |
| 4 | `aging older adults cardiovascular fitness cardiorespiratory` |
| 5 | `intellectual disability developmental disability cardiovascular health exercise` |
| 6 | `accelerometry sedentary behavior physical activity measurement wearable` |
| 7 | `kinesiology exercise physiology sports medicine vascular health` |
| 8 | `health disparities rural cardiovascular exercise physical activity` |
| 9 | `near infrared spectroscopy NIRS tissue oxygenation exercise hemodynamics` |

### Grants.gov API — 12 Keyword Searches
Searches posted + forecasted federal opportunities

| # | Term |
|---|------|
| 1 | `cardiovascular exercise physiology vascular health kinesiology` |
| 2 | `arterial stiffness endothelial function exercise older adults` |
| 3 | `metabolic syndrome physical activity intervention cardiovascular` |
| 4 | `intellectual disability exercise cardiovascular health` |
| 5 | `accelerometry sedentary behavior cardiovascular risk` |
| 6 | `cardiorespiratory fitness VO2max aging vascular` |
| 7 | `exercise intervention blood pressure hypertension` |
| 8 | `health disparities cardiovascular exercise Mississippi` |
| 9 | `near infrared spectroscopy exercise oxygenation` |
| 10 | `flow-mediated dilation vascular ultrasound exercise` |
| 11 | `obesity diabetes exercise cardiovascular prevention` |
| 12 | `physical activity older adults cardiometabolic outcomes` |

---

## 📊 Confidence Scoring

Each grant is scored 0–100% based on how well it matches your research profile:

| Profile Cluster | Weight | Terms Matched Against |
|----------------|--------|----------------------|
| Core topics | 40% | cardiovascular, vascular, arterial stiffness, endothelial function, PWV, FMD, blood pressure... |
| Populations | 20% | older adults, metabolic syndrome, diabetes, intellectual disability, sedentary... |
| Methods / Equipment | 20% | accelerometry, VO2max, NIRS, SphygmoCor, vascular ultrasound, cIMT, FMD... |
| Interventions | 10% | exercise intervention, aerobic exercise, resistance training, HIIT... |
| Context | 10% | kinesiology, exercise physiology, Mississippi, health disparities, rural... |

**Score ≥ 70% = High Confidence** (strong fit with your research profile)

---

## 🏷️ Citizenship Labels

| Label | Meaning | Dashboard Badge |
|-------|---------|----------------|
| `unrestricted` | Explicitly open to F-1 and international students | ✅ Green |
| `unspecified` | No citizenship mentioned — verify with funder | ⚠️ Amber |
| `check` | Live API result — verify per activity code | ⚠️ Amber |
| `us_only` | US citizens / PRs only — **excluded entirely** | ❌ Not shown |

---

## ✏️ Adding a New Grant

Edit `search_grants.py` → find `CURATED_GRANTS` list → add:

```python
{
    "id": "UNIQUE-ID-2026",
    "title": "Grant Name",
    "org": "Funding Organization",
    "org_type": "Nonprofit",
    "org_website": "funder.org",
    "category": ["cardiovascular", "exercise"],
    "citizenship": "unrestricted",            # unrestricted / unspecified / us_only
    "citizenship_note": "Exact language from FOA about citizenship",
    "citizenship_source": "Where you found this — FOA section, page, date",
    "amount_min": 5000,
    "amount_max": 25000,
    "amount_display": "$5,000–$25,000",
    "duration": "1–2 years",
    "deadline": "2026-11-01",                 # YYYY-MM-DD
    "deadline_display": "November 1, 2026",
    "application_open": "2026-08-01",
    "status": "upcoming",                     # active / upcoming / future / monitor
    "populations": ["older adults", "metabolic syndrome"],
    "equipment_relevance": ["SphygmoCor", "accelerometer"],
    "fit_rationale": "Why this fits your research...",
    "requirements": ["Requirement 1", "Requirement 2"],
    "url": "https://funder.org/apply",
    "strategic_note": "Strategic advice for applying...",
    "source": "curated"
},
```

Commit → next Monday's workflow picks it up automatically.

---

## 📁 Files

| File | Description |
|------|-------------|
| `search_grants.py` | Main engine — curated DB + NIH Reporter API (9 queries) + Grants.gov API (12 queries) |
| `build_dashboard.py` | Reads `grants_results.json` → generates `index.html` |
| `grants_results.json` | Search output (auto-generated, committed each run) |
| `index.html` | Live dashboard (auto-generated, do not edit manually) |
| `.github/workflows/grant_search.yml` | GitHub Actions — runs every Monday + deploys |
| `last_run.txt` | Timestamp of last automated run |

---

*Built for precision. Every curated grant verified against official funder websites.*  
*Citizenship source cited for every grant — no guessing.*
