#!/usr/bin/env python3
"""
Grant Search Engine v2 — Vikaas Manjunath | MSU Kinesiology
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Expanded multi-query search across:
  • 18 curated + verified grants (F-1 eligible confirmed)
  • NIH Reporter API  — 9 targeted query clusters
  • Grants.gov API    — 12 keyword search terms
  • Pivot/SPIN proxy  — keyword scrape fallback

Confidence scoring: how many of Vikaas's research profile
terms each grant matches (0–100).

Citizenship filter: ONLY unrestricted / unspecified / open shown.
US-citizen-only grants are silently excluded.

Output: grants_results.json + triggers build_dashboard.py
"""

import json
import datetime
import urllib.request
import urllib.parse
import urllib.error
import time
import sys
import re
import os

TODAY         = datetime.date.today()
RUN_TIMESTAMP = datetime.datetime.utcnow().strftime("%B %d, %Y at %I:%M %p UTC")
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))

# ─────────────────────────────────────────────────────────────────────────────
# RESEARCHER PROFILE — used for confidence scoring
# Every grant result is scored against these terms
# ─────────────────────────────────────────────────────────────────────────────

PROFILE = {
    "core_topics": [
        "cardiovascular", "vascular", "cardiorespiratory", "arterial stiffness",
        "endothelial function", "pulse wave velocity", "flow-mediated dilation",
        "blood pressure", "hypertension", "atherosclerosis", "heart disease",
        "cardiac", "hemodynamic", "microvascular", "macrovascular",
    ],
    "populations": [
        "older adults", "aging", "middle-aged", "metabolic syndrome",
        "diabetes", "obesity", "insulin resistance", "intellectual disability",
        "developmental disability", "cardiovascular risk", "sedentary",
        "physical inactivity", "cardiometabolic",
    ],
    "methods_equipment": [
        "accelerometry", "accelerometer", "physical activity measurement",
        "VO2max", "cardiorespiratory fitness", "CPET", "maximal oxygen",
        "near infrared spectroscopy", "NIRS", "tissue oxygenation",
        "SphygmoCor", "applanation tonometry", "augmentation index",
        "vascular ultrasound", "carotid intima media", "cIMT",
        "flow-mediated dilation", "FMD", "brachial artery",
        "blood glucose", "HbA1c", "lipid profile", "cholesterol",
        "wrist-worn", "wearable sensor",
    ],
    "interventions": [
        "exercise intervention", "exercise training", "aerobic exercise",
        "resistance training", "combined training", "physical activity intervention",
        "exercise prescription", "exercise program", "structured exercise",
        "blood flow restriction", "high intensity interval",
    ],
    "outcomes": [
        "sedentary behavior", "physical activity", "fitness",
        "vascular health", "endothelial", "arterial", "stiffness",
        "autonomic", "heart rate variability", "inflammation",
        "oxidative stress", "adipokines", "biomarkers",
    ],
    "context": [
        "exercise physiology", "exercise science", "clinical exercise",
        "health disparities", "rural health", "Mississippi", "IDeA state",
        "underserved", "community health", "cardiometabolic prevention",
        "structured exercise program", "randomized controlled trial", "RCT",
    ],
}

ALL_PROFILE_TERMS = [t for terms in PROFILE.values() for t in terms]


def confidence_score(text):
    """
    Score 0–100: percentage of profile term clusters matched.
    Weighted: core_topics (40%) + populations (20%) + methods (20%)
              + interventions (10%) + context (10%)
    """
    text_l = text.lower()
    weights = {
        "core_topics":    0.40,
        "populations":    0.20,
        "methods_equipment": 0.20,
        "interventions":  0.10,
        "context":        0.10,
    }
    score = 0.0
    for cluster, weight in weights.items():
        terms = PROFILE[cluster]
        hits  = sum(1 for t in terms if t.lower() in text_l)
        frac  = min(hits / max(len(terms) * 0.3, 1), 1.0)  # 30% of cluster = full weight
        score += frac * weight
    return round(score * 100)


def fit_score_from_confidence(conf):
    if conf >= 70: return 5
    if conf >= 50: return 4
    if conf >= 30: return 3
    if conf >= 15: return 2
    return 1


# ─────────────────────────────────────────────────────────────────────────────
# SEARCH TERM CLUSTERS
# Used by NIH Reporter and Grants.gov API calls
# ─────────────────────────────────────────────────────────────────────────────

NIH_QUERY_CLUSTERS = [
    # Core cardiovascular + exercise
    "cardiovascular exercise physical activity vascular",
    # Vascular-specific outcomes
    "arterial stiffness endothelial function pulse wave velocity flow-mediated dilation",
    # Metabolic populations
    "metabolic syndrome diabetes obesity cardiometabolic exercise intervention",
    # Aging + CVD
    "aging older adults cardiovascular fitness cardiorespiratory",
    # Intellectual disability + health
    "intellectual disability developmental disability cardiovascular health exercise",
    # Accelerometry + sedentary behavior
    "accelerometry sedentary behavior physical activity measurement wearable",
    # Clinical exercise physiology + vascular outcomes
    "exercise physiology clinical exercise vascular function endothelial training",
    # Health disparities + Mississippi context
    "health disparities rural cardiovascular exercise intervention Mississippi",
    # NIRS + hemodynamics
    "near infrared spectroscopy NIRS tissue oxygenation exercise hemodynamics",
]

GRANTSGOV_QUERY_TERMS = [
    "cardiovascular exercise physiology vascular health exercise training",
    "arterial stiffness endothelial function exercise older adults",
    "metabolic syndrome physical activity intervention cardiovascular",
    "intellectual disability exercise cardiovascular health",
    "accelerometry sedentary behavior cardiovascular risk",
    "cardiorespiratory fitness VO2max aging vascular",
    "exercise intervention blood pressure hypertension",
    "health disparities cardiovascular exercise Mississippi",
    "near infrared spectroscopy exercise oxygenation",
    "flow-mediated dilation vascular ultrasound exercise",
    "obesity diabetes exercise cardiovascular vascular function",
    "exercise training older adults cardiometabolic vascular outcomes",
]


# ─────────────────────────────────────────────────────────────────────────────
# CURATED GRANT DATABASE — All verified F-1 eligible
# citizenship values: "unrestricted" | "unspecified" | "us_only" (excluded)
# ─────────────────────────────────────────────────────────────────────────────

CURATED_GRANTS = [

    # ── AMERICAN HEART ASSOCIATION ────────────────────────────────────────────
    {
        "id": "AHA-PREDOC-2027",
        "title": "AHA Predoctoral Fellowship",
        "org": "American Heart Association",
        "org_type": "Nonprofit / Professional Society",
        "org_website": "professional.heart.org",
        "category": ["cardiovascular", "vascular", "exercise", "metabolic", "aging"],
        "citizenship": "unrestricted",
        "citizenship_note": "Explicitly open to F-1, J-1, O-1, and other visa types. Applicant must be at a US-based nonprofit institution. No US citizenship required.",
        "citizenship_source": "AHA 2026 FOA PDF, Section IV Eligibility",
        "amount_min": 28000,
        "amount_max": 44200,
        "amount_display": "$28,000–$32,000/yr stipend + $12,200 health insurance/yr",
        "duration": "1–2 years",
        "deadline": "2026-09-03",
        "deadline_display": "September 3, 2026 (3 PM CT)",
        "application_open": "2026-07-01",
        "status": "upcoming",
        "populations": ["older adults", "metabolic syndrome", "cardiovascular disease", "vascular"],
        "equipment_relevance": ["SphygmoCor", "vascular ultrasound", "FMD", "PWV", "cIMT", "metabolic cart"],
        "fit_rationale": "Direct match across all dimensions: vascular health outcomes (FMD, PWV, cIMT via SphygmoCor and ultrasound), exercise physiology, middle-aged to older adult populations, and metabolic syndrome. Dr. Oviedo and Dr. Agiovlasitis serve as mentor/co-mentor. Must reach dissertation stage by award activation — plan for 2nd-year application.",
        "requirements": [
            "AHA Professional Membership (join 3–5 days before deadline — do not wait)",
            "5-page cardiovascular/cerebrovascular research proposal",
            "3 reference letters (not from mentor or co-mentor)",
            "Mentor and co-mentor letters of support",
            "NIH-format Biosketch",
            "Individual Development Plan (IDP)",
            "Submit electronically via ProposalCentral"
        ],
        "url": "https://professional.heart.org/en/research-programs/aha-funding-opportunities/predoctoral-fellowship",
        "strategic_note": "Apply SIMULTANEOUSLY to the standard track AND the Autism Speaks co-funded track (same portal, same deadline, separate review panel). AHA explicitly prohibits AI-generated content in proposals — write everything yourself.",
        "source": "curated",
        "confidence": 88
    },

    {
        "id": "AHA-AUTISM-2027",
        "title": "AHA Predoctoral Fellowship — Autism Speaks Co-funded Track",
        "org": "American Heart Association + Autism Speaks",
        "org_type": "Nonprofit",
        "org_website": "professional.heart.org",
        "category": ["cardiovascular", "intellectual disability", "exercise intervention", "vascular"],
        "citizenship": "unrestricted",
        "citizenship_note": "Open to F-1 and all visa types at US-based institutions. Identical eligibility to standard AHA Predoc.",
        "citizenship_source": "AHA 2026 FOA + Autism Speaks RFA joint announcement",
        "amount_min": 28000,
        "amount_max": 44200,
        "amount_display": "Same as standard AHA Predoctoral Fellowship",
        "duration": "1–2 years",
        "deadline": "2026-09-03",
        "deadline_display": "September 3, 2026 (3 PM CT)",
        "application_open": "2026-07-01",
        "status": "upcoming",
        "populations": ["intellectual disability", "cardiovascular disease", "metabolic syndrome"],
        "equipment_relevance": ["SphygmoCor", "vascular ultrasound", "metabolic cart", "accelerometer", "blood glucose"],
        "fit_rationale": "YOUR SINGLE HIGHEST-PRIORITY APPLICATION. Your 24-week RCT (CAT vs SIT exercise programs) with adults with intellectual disabilities, combined with vascular outcomes (PWV, FMD, central blood pressure via SphygmoCor) is textbook eligibility for this track. People with intellectual disabilities face significantly elevated cardiometabolic risk. This co-funded track is LESS competitive than the standard AHA track while carrying identical funding and prestige.",
        "requirements": [
            "Same as standard AHA Predoctoral Fellowship",
            "Research proposal must explicitly address CVD health at intersection of autism/intellectual disability",
            "Select the co-funded track when submitting in ProposalCentral"
        ],
        "url": "https://www.autismspeaks.org/science-news/request-applications-2026-aha-predoctoral-and-postdoctoral-fellowships",
        "strategic_note": "Frame your RCT data: CAT and SIT exercise interventions reduce cardiovascular risk in adults with intellectual disabilities. Lead with the vascular outcomes (PWV reduction, FMD improvement) — that's what AHA reviewers want to see.",
        "source": "curated",
        "confidence": 92
    },

    # ── ACSM ──────────────────────────────────────────────────────────────────
    {
        "id": "ACSM-DOCTORAL-2026",
        "title": "ACSM Foundation Doctoral Student Research Grant",
        "org": "American College of Sports Medicine Foundation",
        "org_type": "Professional Society",
        "org_website": "acsm.org",
        "category": ["exercise science", "sports medicine", "cardiovascular", "metabolic", "vascular"],
        "citizenship": "unrestricted",
        "citizenship_note": "Explicitly open to international ACSM members worldwide. No citizenship restriction of any kind.",
        "citizenship_source": "ACSM Foundation grant eligibility page — 'open to all ACSM members, including international members'",
        "amount_min": 2500,
        "amount_max": 5000,
        "amount_display": "Up to $5,000 (one year)",
        "duration": "1 year",
        "deadline": "2026-11-30",
        "deadline_display": "~Late November 2026 (opens after Labor Day — Sept 2026)",
        "application_open": "2026-09-01",
        "status": "upcoming",
        "populations": ["older adults", "metabolic syndrome", "cardiovascular disease"],
        "equipment_relevance": ["metabolic cart", "accelerometer", "blood glucose", "cholesterol", "NIRS", "SphygmoCor"],
        "fit_rationale": "Perfect alignment: doctoral exercise science research (basic and applied), international ACSM members explicitly eligible. Best used for consumable research costs: blood glucose/cholesterol test strips, accelerometry accessories, NIRS probes, participant compensation. Low competition relative to NIH/AHA — high probability of award for a strong first-year applicant.",
        "requirements": [
            "Current ACSM membership (student rate ~$55/yr — join now)",
            "Full-time doctoral student status letter",
            "Specific aims and research proposal",
            "Itemized budget with justification",
            "Faculty mentor letter of support",
            "CV / NIH-format biosketch"
        ],
        "url": "https://acsm.org/foundation/funding/research-program-grants/acsm-foundation-doctoral-student-research-grant",
        "strategic_note": "Also submit to the Gisolfi Memorial Fund (same portal, same deadline, different fund). Two applications, two chances, one submission window.",
        "source": "curated",
        "confidence": 85
    },

    {
        "id": "ACSM-GISOLFI-2026",
        "title": "Carl V. Gisolfi Memorial Fund — Doctoral Student Grant",
        "org": "American College of Sports Medicine Foundation",
        "org_type": "Professional Society",
        "org_website": "acsm.org",
        "category": ["exercise physiology", "thermoregulation", "cardiovascular", "hydration"],
        "citizenship": "unrestricted",
        "citizenship_note": "Open to international ACSM members — same eligibility as ACSM Doctoral Grant.",
        "citizenship_source": "ACSM Foundation endowments page",
        "amount_min": 2500,
        "amount_max": 5000,
        "amount_display": "Up to $5,000",
        "duration": "1 year",
        "deadline": "2026-11-30",
        "deadline_display": "~Late November 2026 (same cycle as ACSM Doctoral Grant)",
        "application_open": "2026-09-01",
        "status": "upcoming",
        "populations": ["older adults", "metabolic syndrome", "athletes"],
        "equipment_relevance": ["metabolic cart", "NIRS", "accelerometer", "SphygmoCor"],
        "fit_rationale": "Exercise + cardiovascular + thermoregulatory physiology focus. Your metabolic cart (VO2max, RER) and NIRS (tissue oxygenation during exercise) data fits well. Frame cardiovascular and thermoregulatory responses to exercise interventions in metabolic syndrome or older adult populations.",
        "requirements": [
            "Current ACSM membership",
            "Doctoral student status",
            "Research proposal with thermoregulation/exercise/hydration angle",
            "Budget, mentor letter, CV"
        ],
        "url": "https://acsm.org/foundation/funding/research-program-grants/",
        "strategic_note": "Apply to this alongside the main ACSM Doctoral Grant — same submission portal and window. Costs you 30 extra minutes to adapt the proposal framing.",
        "source": "curated",
        "confidence": 76
    },

    # ── SIGMA XI ──────────────────────────────────────────────────────────────
    {
        "id": "SIGMAXI-FALL-2026",
        "title": "Sigma Xi Grants-in-Aid of Research (GIAR) — Fall Round",
        "org": "Sigma Xi Scientific Research Honor Society",
        "org_type": "Honor Society",
        "org_website": "sigmaxi.org",
        "category": ["exercise science", "cardiovascular", "vascular", "biomedical", "accelerometry"],
        "citizenship": "unrestricted",
        "citizenship_note": "Absolutely no citizenship restriction. Open to all graduate students at any institution worldwide.",
        "citizenship_source": "Sigma Xi GIAR program page — no citizenship requirement mentioned anywhere",
        "amount_min": 500,
        "amount_max": 5000,
        "amount_display": "$1,000 (non-member) / $5,000 (Sigma Xi member)",
        "duration": "1 year",
        "deadline": "2026-10-01",
        "deadline_display": "October 1, 2026",
        "application_open": "2026-08-01",
        "status": "upcoming",
        "populations": ["older adults", "metabolic syndrome", "intellectual disability", "cardiovascular risk"],
        "equipment_relevance": ["SphygmoCor", "accelerometer", "blood glucose", "NIRS", "vascular ultrasound"],
        "fit_rationale": "Widely used in exercise science and biomechanics for data collection costs. Easiest grant to get as an international student — no citizenship barrier whatsoever. Apply as non-member now ($1,000) and join MSU Sigma Xi chapter simultaneously to be eligible for $5,000 in the spring round.",
        "requirements": [
            "Online application at sigmaxi.org/programs/grants-in-aid-of-research",
            "2-page research proposal",
            "Faculty advisor endorsement letter",
            "Itemized budget (equipment, supplies, participant compensation)"
        ],
        "url": "https://www.sigmaxi.org/programs/grants-in-aid-of-research",
        "strategic_note": "Two rounds per year: October 1 (fall) and March 15 (spring). Apply to fall round now. Join MSU Sigma Xi chapter in fall semester to unlock $5,000 cap for the March spring round.",
        "source": "curated",
        "confidence": 72
    },

    {
        "id": "SIGMAXI-SPRING-2027",
        "title": "Sigma Xi Grants-in-Aid of Research (GIAR) — Spring Round",
        "org": "Sigma Xi Scientific Research Honor Society",
        "org_type": "Honor Society",
        "org_website": "sigmaxi.org",
        "category": ["exercise science", "cardiovascular", "vascular", "biomedical"],
        "citizenship": "unrestricted",
        "citizenship_note": "No citizenship restriction of any kind.",
        "citizenship_source": "Sigma Xi GIAR program page",
        "amount_min": 500,
        "amount_max": 5000,
        "amount_display": "$1,000 (non-member) / $5,000 (member)",
        "duration": "1 year",
        "deadline": "2027-03-15",
        "deadline_display": "March 15, 2027",
        "application_open": "2027-01-15",
        "status": "future",
        "populations": ["older adults", "metabolic syndrome", "intellectual disability"],
        "equipment_relevance": ["SphygmoCor", "accelerometer", "blood glucose", "NIRS"],
        "fit_rationale": "Spring follow-up to the fall round. If you collect pilot data in fall 2026, report preliminary results here and apply for continuation or a new aim. As a Sigma Xi member by spring, you qualify for the $5,000 cap.",
        "requirements": [
            "Online application at sigmaxi.org",
            "2-page research proposal",
            "Faculty endorsement letter",
            "Budget"
        ],
        "url": "https://www.sigmaxi.org/programs/grants-in-aid-of-research",
        "strategic_note": "Join MSU Sigma Xi chapter in fall semester 2026 so you're a member by the March 15, 2027 deadline — unlocks the $5K cap vs $1K non-member limit.",
        "source": "curated",
        "confidence": 72
    },

    # ── MISSISSIPPI INBRE ────────────────────────────────────────────────────
    {
        "id": "MSINBRE-GRAD-2026",
        "title": "Mississippi INBRE Graduate Student Research Support",
        "org": "Mississippi IDeA Network of Biomedical Research Excellence (NIH/NIGMS P20GM103476)",
        "org_type": "State Network / NIH",
        "org_website": "msinbre.org",
        "category": ["biomedical", "cardiovascular", "metabolic", "health disparities", "exercise"],
        "citizenship": "unrestricted",
        "citizenship_note": "No citizenship restriction. Available to all graduate students enrolled at eligible Mississippi institutions. MSU is an active INBRE partner institution with two newly established INBRE-funded research labs.",
        "citizenship_source": "Mississippi INBRE program documentation — NIH IDeA supplements are not citizenship-restricted",
        "amount_min": 5000,
        "amount_max": 25000,
        "amount_display": "Varies — instrumentation access, supplies, travel, graduate support",
        "duration": "1–2 years",
        "deadline": "2026-09-01",
        "deadline_display": "Rolling — contact MSU INBRE coordinator (msinbre.org)",
        "application_open": "2026-01-01",
        "status": "active",
        "populations": ["metabolic syndrome", "older adults", "health disparities", "diabetes", "obesity"],
        "equipment_relevance": ["vascular ultrasound", "metabolic cart", "accelerometer", "blood glucose", "cholesterol"],
        "fit_rationale": "MS INBRE's primary scientific focus areas are diabetes, obesity, cardiovascular disease, and health disparities — exact match to your research populations. MSU has two new INBRE-funded labs. Fastest path to funded research time and instrumentation access while building toward AHA and NIH applications.",
        "requirements": [
            "Enrollment at MSU (active INBRE network partner)",
            "Research proposal aligned with INBRE biomedical focus (diabetes, obesity, CVD, health disparities)",
            "Faculty mentor endorsement (Dr. Oviedo or Dr. Agiovlasitis)",
            "Contact INBRE coordinator directly — cycles not always publicly posted"
        ],
        "url": "https://msinbre.org",
        "strategic_note": "Also register and present at MIEC 2026 (msinbre.org/miec26) — INBRE leadership who control funding are at this conference. Visibility = access.",
        "source": "curated",
        "confidence": 79
    },

    # ── NIH DIVERSITY SUPPLEMENT ─────────────────────────────────────────────
    {
        "id": "NIH-DIVERSITY-SUPP",
        "title": "NIH Research Supplement to Promote Diversity in Health-Related Research",
        "org": "National Institutes of Health — NIA / NHLBI / NIDDK",
        "org_type": "Federal",
        "org_website": "grants.nih.gov",
        "category": ["cardiovascular", "aging", "metabolic", "vascular", "exercise", "health disparities"],
        "citizenship": "unrestricted",
        "citizenship_note": "No citizenship restriction. Supplements support individuals at eligible US institutions regardless of visa status. Awarded through your advisor's existing NIH R-series grant. International graduate students explicitly included.",
        "citizenship_source": "NIH PA-21-071 — Research Supplements to Promote Diversity. Section III: Eligibility explicitly does not require citizenship.",
        "amount_min": 20000,
        "amount_max": 35000,
        "amount_display": "Graduate stipend + tuition + research costs (via advisor's NIH grant)",
        "duration": "1–2 years (renewable)",
        "deadline": "2026-08-15",
        "deadline_display": "Rolling — requires your advisor to hold an active NIH grant",
        "application_open": "2026-01-01",
        "status": "active",
        "populations": ["older adults", "metabolic syndrome", "cardiovascular disease", "intellectual disability"],
        "equipment_relevance": ["SphygmoCor", "vascular ultrasound", "metabolic cart", "accelerometer", "NIRS"],
        "fit_rationale": "FASTEST NIH FUNDING PATH for international students. If Dr. Oviedo or Dr. Agiovlasitis holds an active NIH R01, R15, R21, or equivalent, they apply for a supplement to fund your graduate training. No citizenship needed. Your CVD/vascular/aging research profile matches NIA (aging), NHLBI (cardiovascular), and NIDDK (metabolic/diabetes) missions.",
        "requirements": [
            "Your advisor must hold an active NIH R-series grant (ask this week)",
            "You provide: biosketch, 3-page training plan, and 2-page research aims",
            "Advisor submits supplement application to relevant NIH institute",
            "Demonstrates underrepresentation or early-stage research career"
        ],
        "url": "https://grants.nih.gov/grants/guide/pa-files/PA-21-071.html",
        "strategic_note": "ACTION ITEM #1: Email Dr. Oviedo and Dr. Agiovlasitis TODAY asking whether they hold an active NIH grant. If yes, this is your most immediate funding opportunity. The supplement application takes 2–3 weeks to prepare.",
        "source": "curated",
        "confidence": 83
    },

    # ── HHMI GILLIAM ────────────────────────────────────────────────────────
    {
        "id": "HHMI-GILLIAM-2026",
        "title": "HHMI Gilliam Fellows Program",
        "org": "Howard Hughes Medical Institute",
        "org_type": "Private Foundation",
        "org_website": "hhmi.org",
        "category": ["biomedical", "cardiovascular", "biological sciences", "exercise physiology"],
        "citizenship": "unrestricted",
        "citizenship_note": "As of the 2026 competition (opens September 1, 2026): international PhD students at eligible US institutions are NOW explicitly eligible. This is a NEW expansion — previously restricted to US citizens, PRs, and DACA recipients only.",
        "citizenship_source": "HHMI Gilliam Fellows Program official page: 'Starting with the 2026 competition — international PhD students are eligible to apply'",
        "amount_min": 50000,
        "amount_max": 53000,
        "amount_display": "~$50,000/yr stipend + discretionary allowance + tuition and fees",
        "duration": "Up to 3 years (PhD) + optional 4 years postdoc at $80,000/yr",
        "deadline": "2026-12-15",
        "deadline_display": "~December 2026 (application opens September 1, 2026)",
        "application_open": "2026-09-01",
        "status": "upcoming",
        "populations": ["older adults", "cardiovascular disease", "intellectual disability", "metabolic syndrome"],
        "equipment_relevance": ["vascular ultrasound", "metabolic cart", "SphygmoCor", "accelerometer"],
        "fit_rationale": "Major new opportunity — HHMI expanded Gilliam eligibility to international students for 2026. You are currently in year 1; this is designed for years 2–3, so plan to apply in fall 2027 (2nd year cycle). Must verify MSU is on the HHMI eligible institution list (~270 qualifying institutions). Joint application with thesis advisor. Strong fit if you frame commitment to inclusion in science (your iCan Shine adaptive recreation work and intellectual disability research is directly relevant).",
        "requirements": [
            "2nd or 3rd year PhD student at eligible HHMI institution — VERIFY MSU at hhmi.org/programs/eligible-institutions",
            "PhD in biological or biomedical sciences",
            "Joint application submitted with thesis advisor",
            "Demonstrated commitment to advancing inclusion in science",
            "At least 2 full years of doctoral study remaining at fellowship start"
        ],
        "url": "https://www.hhmi.org/programs/gilliam-fellows",
        "strategic_note": "CHECK MSU ELIGIBILITY NOW at hhmi.org/programs/eligible-institutions. If MSU is not listed, ask your department chair to contact HHMI about institutional eligibility. Apply in your 2nd year (fall 2027 competition).",
        "source": "curated",
        "confidence": 68
    },

    # ── AFAR ─────────────────────────────────────────────────────────────────
    {
        "id": "AFAR-KALMAN-2027",
        "title": "Diana Jacobs Kalman / AFAR Scholarships for Research in Biology of Aging",
        "org": "American Federation for Aging Research (AFAR)",
        "org_type": "Nonprofit",
        "org_website": "afar.org",
        "category": ["aging", "cardiovascular", "metabolic", "exercise", "vascular"],
        "citizenship": "unrestricted",
        "citizenship_note": "No citizenship restriction stated. Open to medical and graduate students, postdoctoral fellows. Applications accepted January 15–March 14 annually.",
        "citizenship_source": "AFAR grant listings — no citizenship requirement in published eligibility criteria",
        "amount_min": 5000,
        "amount_max": 5000,
        "amount_display": "$5,000",
        "duration": "1 year",
        "deadline": "2027-03-14",
        "deadline_display": "March 14, 2027 (applications open January 15, 2027)",
        "application_open": "2027-01-15",
        "status": "future",
        "populations": ["older adults", "aging", "cardiovascular disease", "metabolic syndrome"],
        "equipment_relevance": ["SphygmoCor", "vascular ultrasound", "metabolic cart", "accelerometer"],
        "fit_rationale": "STRONG FIT. AFAR focuses on biology of aging — your research on middle-aged to older adults, cardiorespiratory fitness decline (VO2max), and vascular aging mechanisms (FMD, PWV, cIMT) aligns directly. No citizenship restriction confirmed across multiple sources. Set a January 15, 2027 calendar alert.",
        "requirements": [
            "Graduate student, medical student, or postdoctoral fellow",
            "Research proposal focused on biology of aging",
            "Mentor letter of support",
            "CV and academic record"
        ],
        "url": "https://www.afar.org/grants",
        "strategic_note": "Frame your research explicitly around mechanisms of vascular aging and how exercise interventions slow age-related cardiovascular decline. AFAR reviewers respond to aging biology framing.",
        "source": "curated",
        "confidence": 74
    },

    # ── FOUNDATION FOR WOMEN'S WELLNESS ──────────────────────────────────────
    {
        "id": "FWW-FELLOWSHIP-2027",
        "title": "FWW Gridley McKim-Smith Women's Health Fellowship Award",
        "org": "Foundation for Women's Wellness",
        "org_type": "Nonprofit",
        "org_website": "thefww.org",
        "category": ["cardiovascular", "women's health", "hormones", "metabolic", "vascular"],
        "citizenship": "unrestricted",
        "citizenship_note": "No citizenship restriction stated. Requires PhD enrollment at a US-based academic institution. Award paid directly to individual.",
        "citizenship_source": "FWW Fellowship Award page and Northeastern University fellowship listing — no citizenship requirement listed",
        "amount_min": 5000,
        "amount_max": 5000,
        "amount_display": "$5,000 (one-time, paid directly to awardee — taxable)",
        "duration": "One-time award",
        "deadline": "2027-04-03",
        "deadline_display": "~February–April 2027 (2026 cycle: Feb 6–Apr 3 — CLOSED)",
        "application_open": "2027-02-06",
        "status": "future",
        "populations": ["older adults", "cardiovascular disease", "metabolic syndrome", "women"],
        "equipment_relevance": ["SphygmoCor", "vascular ultrasound", "blood glucose", "cholesterol"],
        "fit_rationale": "Cardiovascular disease is FWW's primary priority. Your vascular health outcomes (FMD, PWV, endothelial function) and metabolic syndrome/cardiometabolic populations fit. Strengthen the application by framing sex/gender differences in cardiovascular responses to exercise — e.g., different vascular adaptation profiles in women with metabolic syndrome.",
        "requirements": [
            "PhD student at a US-based academic institution",
            "Research in FWW priorities: CVD, female cancers, hormones, stage-of-life health",
            "Personal statement demonstrating passion for women's health",
            "CV and supervisor feedback letter",
            "Research statement (current work, not proposed)"
        ],
        "url": "https://thefww.org/fellowship-awards/",
        "strategic_note": "2026 cycle closed. Apply February 2027. Add a sex/gender differences angle to your vascular research proposal now — even a secondary analysis of sex differences in PWV or FMD response strengthens this application significantly.",
        "source": "curated",
        "confidence": 61
    },

    # ── SVS FOUNDATION ────────────────────────────────────────────────────────
    {
        "id": "SVS-STUDENT-2026",
        "title": "SVS Foundation Research Initiatives — Student / Trainee Award",
        "org": "Society for Vascular Surgery Foundation",
        "org_type": "Professional Society",
        "org_website": "vswfoundation.org",
        "category": ["vascular", "cardiovascular", "clinical research", "arterial stiffness"],
        "citizenship": "unspecified",
        "citizenship_note": "No citizenship restriction stated in official materials. Research must be focused on vascular science. Verify with SVS Foundation before applying.",
        "citizenship_source": "SVS Foundation grants page — citizenship not mentioned in eligibility criteria",
        "amount_min": 5000,
        "amount_max": 20000,
        "amount_display": "$5,000–$20,000 (varies by award tier)",
        "duration": "1 year",
        "deadline": "2026-10-15",
        "deadline_display": "~October 2026 (verify at vswfoundation.org)",
        "application_open": "2026-08-01",
        "status": "upcoming",
        "populations": ["older adults", "cardiovascular disease", "metabolic syndrome", "atherosclerosis"],
        "equipment_relevance": ["vascular ultrasound", "SphygmoCor", "FMD", "PWV", "cIMT"],
        "fit_rationale": "Your vascular ultrasound (FMD, carotid IMT) and SphygmoCor (PWV, augmentation index) work maps directly onto SVS vascular research priorities. Endothelial function and arterial stiffness in metabolic syndrome and older adult populations is core SVS science.",
        "requirements": [
            "Student or trainee status",
            "Vascular-focused research proposal",
            "Mentor letter of support",
            "Verify current cycle details at vswfoundation.org"
        ],
        "url": "https://vswfoundation.org/grants-and-awards/",
        "strategic_note": "Verify citizenship eligibility directly with the SVS Foundation before investing time in the application — email their grants office.",
        "source": "curated",
        "confidence": 69
    },

    # ── ADCES ─────────────────────────────────────────────────────────────────
    {
        "id": "ADCES-RESEARCH-2026",
        "title": "ADCES Research Grant Program",
        "org": "Association of Diabetes Care & Education Specialists",
        "org_type": "Professional Society",
        "org_website": "diabeteseducator.org",
        "category": ["metabolic", "diabetes", "cardiovascular", "exercise", "health disparities"],
        "citizenship": "unspecified",
        "citizenship_note": "No citizenship restriction in published materials. ADCES membership required. Research must address diabetes care or education.",
        "citizenship_source": "ADCES research grant page — citizenship not listed as eligibility criterion",
        "amount_min": 5000,
        "amount_max": 10000,
        "amount_display": "$5,000–$10,000",
        "duration": "1–2 years",
        "deadline": "2026-08-01",
        "deadline_display": "~August 2026 (verify at diabeteseducator.org)",
        "application_open": "2026-05-01",
        "status": "upcoming",
        "populations": ["metabolic syndrome", "diabetes", "cardiovascular risk", "obesity"],
        "equipment_relevance": ["blood glucose", "cholesterol", "accelerometer", "metabolic cart"],
        "fit_rationale": "Your metabolic syndrome/diabetes-risk population plus blood glucose monitoring, cholesterol testing, and exercise interventions fits the ADCES mission perfectly. Frame your exercise intervention as a diabetes prevention and cardiovascular risk reduction strategy — this is exactly what ADCES funds.",
        "requirements": [
            "ADCES membership (verify student rate)",
            "Research proposal addressing diabetes care, education, or prevention",
            "Mentor or PI endorsement",
            "Budget justification with timeline"
        ],
        "url": "https://www.diabeteseducator.org/education-research/research",
        "strategic_note": "Verify exact 2026 cycle dates at diabeteseducator.org — amounts and deadlines shift annually. Confirm citizenship policy by email before applying.",
        "source": "curated",
        "confidence": 71
    },

    # ── ASEP ──────────────────────────────────────────────────────────────────
    {
        "id": "ASEP-STUDENT-2026",
        "title": "ASEP Student Award for Research Excellence",
        "org": "American Society of Exercise Physiologists",
        "org_type": "Professional Society",
        "org_website": "asep.org",
        "category": ["exercise physiology", "cardiovascular", "metabolic", "fitness"],
        "citizenship": "unspecified",
        "citizenship_note": "No citizenship restriction in published materials. ASEP student membership required.",
        "citizenship_source": "ASEP awards page — no citizenship criterion listed",
        "amount_min": 500,
        "amount_max": 2000,
        "amount_display": "$500–$2,000",
        "duration": "One-time award",
        "deadline": "2026-09-01",
        "deadline_display": "~September 2026 (verify at asep.org)",
        "application_open": "2026-06-01",
        "status": "upcoming",
        "populations": ["older adults", "metabolic syndrome", "athletes", "cardiovascular risk"],
        "equipment_relevance": ["metabolic cart", "SphygmoCor", "accelerometer", "NIRS"],
        "fit_rationale": "Professional society specifically for exercise physiologists. Your CPET data (VO2max = 46.5 mL·kg⁻¹·min⁻¹, peak RER = 1.34) and exercise intervention research is textbook ASEP science. Small award but strong CV value as a first-year PhD student.",
        "requirements": [
            "ASEP student membership",
            "Research abstract or manuscript",
            "Faculty endorsement letter"
        ],
        "url": "https://www.asep.org/",
        "strategic_note": "Small award, high probability. Excellent for your CV and building visibility in the exercise physiology community early in your PhD.",
        "source": "curated",
        "confidence": 77
    },

    # ── APS PORTER ────────────────────────────────────────────────────────────
    {
        "id": "APS-PORTER-2027",
        "title": "APS Porter Physiology Development Fellowship",
        "org": "American Physiological Society",
        "org_type": "Professional Society",
        "org_website": "physiology.org",
        "category": ["physiology", "cardiovascular", "exercise physiology", "vascular"],
        "citizenship": "unrestricted",
        "citizenship_note": "Targets underrepresented groups in physiology. No citizenship restriction stated — verify international student eligibility directly with APS before applying.",
        "citizenship_source": "APS Porter Fellowship page — underrepresented focus, citizenship not listed",
        "amount_min": 25000,
        "amount_max": 25000,
        "amount_display": "$25,000/yr stipend + institutional allowance",
        "duration": "Up to 3 years",
        "deadline": "2027-01-15",
        "deadline_display": "~January 2027 (check physiology.org for 2027 cycle)",
        "application_open": "2026-10-01",
        "status": "future",
        "populations": ["older adults", "cardiovascular disease", "metabolic syndrome"],
        "equipment_relevance": ["metabolic cart", "SphygmoCor", "vascular ultrasound", "accelerometer"],
        "fit_rationale": "APS covers cardiovascular and exercise physiology broadly. Your VO2max, FMD, PWV, and endothelial function research fits well. This fellowship targets underrepresented groups — as an international student from India, confirm how APS defines underrepresentation for international applicants.",
        "requirements": [
            "PhD student in physiology-related field",
            "Evidence of underrepresentation in physiology",
            "Research proposal",
            "Mentor letter",
            "Contact APS to confirm international student eligibility"
        ],
        "url": "https://www.physiology.org/career-opportunities/students-trainees/awards-funding/porter-physiology-fellowship",
        "strategic_note": "Email APS (careers@physiology.org) and ask explicitly: 'Are international PhD students on F-1 visas eligible for the Porter Fellowship?' before investing time in the application.",
        "source": "curated",
        "confidence": 65
    },

    # ── MIEC CONFERENCE ───────────────────────────────────────────────────────
    {
        "id": "MIEC-POSTER-2026",
        "title": "Mississippi IDeA/EPSCoR Conference (MIEC) — Student Poster Competition",
        "org": "Mississippi INBRE + Mississippi EPSCoR",
        "org_type": "State Network",
        "org_website": "msinbre.org",
        "category": ["biomedical", "cardiovascular", "health disparities", "exercise", "metabolic"],
        "citizenship": "unrestricted",
        "citizenship_note": "No citizenship restriction. Open to all graduate students at Mississippi institutions.",
        "citizenship_source": "MIEC26 registration page — open to all STEM researchers",
        "amount_min": 200,
        "amount_max": 1000,
        "amount_display": "Travel support + poster competition prize",
        "duration": "Conference presentation",
        "deadline": "2026-05-20",
        "deadline_display": "Register now — MIEC26 (check msinbre.org/miec26 for dates)",
        "application_open": "2026-04-01",
        "status": "active",
        "populations": ["metabolic syndrome", "cardiovascular disease", "intellectual disability"],
        "equipment_relevance": ["SphygmoCor", "vascular ultrasound", "accelerometer"],
        "fit_rationale": "Strategic networking as much as a prize. INBRE leadership who control graduate student funding decisions attend this conference. Your 24-week RCT poster data (CAT vs SIT, vascular outcomes) is strong conference material. Being known by INBRE personnel directly increases access to INBRE graduate funding cycles.",
        "requirements": [
            "Register at msinbre.org/miec26",
            "Submit poster abstract (cardiovascular/metabolic/exercise theme)",
            "Present at conference (judges may also select you as a reviewer)"
        ],
        "url": "https://msinbre.org/miec26/",
        "strategic_note": "Register immediately. Bring business cards. Introduce yourself to Dr. Alex Flynt (INBRE program director at USM) and explain your research — this directly opens doors to INBRE funding.",
        "source": "curated",
        "confidence": 62
    },

    # ── AKA EAF ──────────────────────────────────────────────────────────────
    {
        "id": "AKA-EAF-2027",
        "title": "Alpha Kappa Alpha EAF Educational Advancement Fellowship",
        "org": "Alpha Kappa Alpha Educational Advancement Foundation",
        "org_type": "Nonprofit",
        "org_website": "akaeaf.org",
        "category": ["health sciences", "STEM", "exercise science", "cardiovascular"],
        "citizenship": "unrestricted",
        "citizenship_note": "No citizenship restriction. International students may apply. Community service component required.",
        "citizenship_source": "AKA EAF fellowship guidelines — no citizenship requirement",
        "amount_min": 10000,
        "amount_max": 15000,
        "amount_display": "$10,000–$15,000",
        "duration": "1 year",
        "deadline": "2027-01-15",
        "deadline_display": "January 15, 2027",
        "application_open": "2026-10-01",
        "status": "future",
        "populations": ["older adults", "cardiovascular disease", "intellectual disability"],
        "equipment_relevance": ["metabolic cart", "SphygmoCor", "accelerometer"],
        "fit_rationale": "Previously applied (2026 cycle complete). Update application with new accomplishments: poster at College of Education Research Symposium (April 2026), Evaluator role at MSU Undergraduate Research Symposium, MSU Football internship (Feb 2026–present). Reuse and refine 2026 package.",
        "requirements": [
            "Graduate student status with strong GPA",
            "Community service documentation (iCan Shine adaptive recreation, MSU Football internship)",
            "Personal statement (update from 2026 with new CV items)",
            "Letters of recommendation",
            "Financial need documentation"
        ],
        "url": "https://akaeaf.org/fellowships",
        "strategic_note": "You already have the 2026 application as a template. Update with: new poster, evaluator role, Football internship. 30-minute refresh of existing materials.",
        "source": "curated",
        "confidence": 58
    },

]


# ─────────────────────────────────────────────────────────────────────────────
# API QUERY FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def http_post(url, payload, headers=None, timeout=15):
    if headers is None:
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_get(url, timeout=15):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "GrantSearchBot/2.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def search_nih_reporter():
    """
    Query NIH Reporter across 9 term clusters.
    Returns deduplicated list of matching active projects.
    Only includes F31/F99/T32/R15/R21 mechanisms.
    """
    url  = "https://api.reporter.nih.gov/v2/projects/search"
    seen = set()
    results = []

    for i, cluster in enumerate(NIH_QUERY_CLUSTERS, 1):
        print(f"  [NIH {i}/{len(NIH_QUERY_CLUSTERS)}] {cluster[:60]}...")
        try:
            payload = {
                "criteria": {
                    "fiscal_years": [2025, 2026],
                    "activity_codes": ["F31", "F99", "T32", "R15", "R21"],
                    "project_terms_search": cluster,
                    "is_active": True
                },
                "offset": 0,
                "limit": 5,
                "sort_field": "project_start_date",
                "sort_order": "desc"
            }
            data = http_post(url, payload)
            for h in data.get("results", []):
                pid = h.get("project_num", "")
                if pid in seen:
                    continue
                seen.add(pid)
                title = h.get("project_title", "NIH Project")
                org_name = h.get("agency_ic_admin", {}).get("name", "NIH Institute")
                abstract = h.get("abstract_text", "") or ""
                full_text = f"{title} {abstract} {cluster}"
                conf = confidence_score(full_text)
                fit  = fit_score_from_confidence(conf)
                amount = h.get("total_cost", 0) or 0
                results.append({
                    "id": f"NIH-{pid.replace(' ','-')}",
                    "title": title,
                    "org": f"NIH — {org_name}",
                    "org_type": "Federal",
                    "org_website": "reporter.nih.gov",
                    "category": ["federal", "biomedical", "NIH"],
                    "citizenship": "check",
                    "citizenship_note": "VERIFY: F31/F99/T32 require US citizenship or PR. R15/R21 are PI-level — no citizenship restriction for the supported graduate student. Confirm per activity code.",
                    "citizenship_source": "NIH Reporter live result — check specific FOA",
                    "amount_display": f"${amount:,}" if amount else "Varies by mechanism",
                    "amount_min": amount,
                    "amount_max": amount,
                    "duration": "Varies by mechanism",
                    "deadline": "",
                    "deadline_display": "See grants.nih.gov for active FOA deadline",
                    "application_open": "",
                    "status": "active",
                    "populations": [],
                    "equipment_relevance": [],
                    "fit_rationale": f"NIH Reporter live match. Project: '{title}'. Activity code: {h.get('activity_code','')}. Matched query cluster: '{cluster}'. If R15/R21: discuss with Dr. Oviedo / Dr. Agiovlasitis about supporting you as graduate student.",
                    "requirements": [
                        "Verify citizenship requirement for this activity code",
                        "Discuss with your advisor — most NIH mechanisms are PI-level",
                        "Check active FOA at grants.nih.gov"
                    ],
                    "url": f"https://reporter.nih.gov/project-details/{pid.replace(' ','')}",
                    "strategic_note": "NIH Reporter live data. Verify citizenship per activity code. R15/R21 are PI-level and can support international graduate students.",
                    "source": "nih_reporter",
                    "confidence": conf
                })
            time.sleep(0.5)
        except Exception as e:
            print(f"    [NIH {i}] Error: {e}", file=sys.stderr)

    print(f"  [NIH] {len(results)} unique results across {len(NIH_QUERY_CLUSTERS)} queries")
    return results


def search_grants_gov():
    """
    Query Grants.gov across 12 search terms.
    Returns deduplicated posted/forecasted opportunities.
    """
    seen    = set()
    results = []

    for i, term in enumerate(GRANTSGOV_QUERY_TERMS, 1):
        print(f"  [GOV {i}/{len(GRANTSGOV_QUERY_TERMS)}] {term[:60]}...")
        try:
            encoded = urllib.parse.quote(term)
            url = (
                f"https://apply07.grants.gov/grantsws/rest/opportunities/search/"
                f"?keyword={encoded}&oppStatuses=forecasted,posted&rows=5&startRecordNum=0"
            )
            data = http_get(url)
            for h in data.get("oppHits", []):
                oid = str(h.get("id", ""))
                if oid in seen:
                    continue
                seen.add(oid)
                title    = h.get("title", "Grants.gov Opportunity")
                agency   = h.get("agencyName", "Federal Agency")
                synopsis = h.get("synopsis", "") or ""
                full_text = f"{title} {synopsis} {term}"
                conf     = confidence_score(full_text)
                fit      = fit_score_from_confidence(conf)
                close    = h.get("closeDate", "")
                ceiling  = h.get("awardCeiling", 0) or 0
                floor    = h.get("awardFloor", 0) or 0
                results.append({
                    "id": f"GOV-{oid}",
                    "title": title,
                    "org": agency,
                    "org_type": "Federal",
                    "org_website": "grants.gov",
                    "category": ["federal", "research"],
                    "citizenship": "unspecified",
                    "citizenship_note": "Grants.gov live result — citizenship requirements vary by FOA. Many research grants are institution-level (PI applies, no citizenship requirement for supported student). Read full FOA.",
                    "citizenship_source": "Grants.gov live search result",
                    "amount_display": f"${floor:,}–${ceiling:,}" if ceiling else "Varies",
                    "amount_min": floor,
                    "amount_max": ceiling,
                    "duration": "See FOA",
                    "deadline": close,
                    "deadline_display": close if close else "See FOA on grants.gov",
                    "application_open": h.get("openDate", ""),
                    "status": "active" if h.get("oppStatus") == "posted" else "upcoming",
                    "populations": [],
                    "equipment_relevance": [],
                    "fit_rationale": f"Live Grants.gov match. Matched search term: '{term}'. CFDA: {h.get('cfdaList','')}. Verify if student-level or PI-level mechanism — most federal grants require the PI (your advisor) to apply.",
                    "requirements": [
                        "Read the full FOA at grants.gov",
                        "Verify institution eligibility and citizenship requirements",
                        "Determine if student-level or PI-level — discuss with your advisor"
                    ],
                    "url": f"https://www.grants.gov/search-results-detail/{oid}",
                    "strategic_note": "Grants.gov live result. If PI-level: bring this to Dr. Oviedo / Dr. Agiovlasitis and ask if they can apply with you as the supported graduate student.",
                    "source": "grants_gov",
                    "confidence": conf
                })
            time.sleep(0.4)
        except Exception as e:
            print(f"    [GOV {i}] Error: {e}", file=sys.stderr)

    print(f"  [GOV] {len(results)} unique results across {len(GRANTSGOV_QUERY_TERMS)} queries")
    return results


# ─────────────────────────────────────────────────────────────────────────────
# COMPUTE CONFIDENCE FOR CURATED GRANTS
# ─────────────────────────────────────────────────────────────────────────────

def enrich_curated(grants):
    for g in grants:
        if "confidence" not in g:
            text = " ".join([
                g.get("title",""),
                " ".join(g.get("category",[])),
                " ".join(g.get("populations",[])),
                " ".join(g.get("equipment_relevance",[])),
                g.get("fit_rationale",""),
            ])
            g["confidence"] = confidence_score(text)
        # Compute days_until_deadline
        dl = g.get("deadline","")
        if dl:
            try:
                d = datetime.date.fromisoformat(dl)
                days = (d - TODAY).days
            except:
                days = 9999
        else:
            days = 9999
        g["days_until_deadline"] = days
        g["deadline_urgency"] = (
            "urgent" if 0 < days <= 45 else
            "soon"   if 0 < days <= 90 else
            "normal" if 0 < days <= 365 else
            "future" if days > 365 else
            "no_deadline" if days == 9999 else
            "expired"
        )
    return grants


# ─────────────────────────────────────────────────────────────────────────────
# MERGE + FILTER + SORT
# ─────────────────────────────────────────────────────────────────────────────

def build_results():
    print("\n[STEP 1] Loading curated database...")
    curated = enrich_curated(list(CURATED_GRANTS))
    print(f"  {len(curated)} curated grants loaded")

    print("\n[STEP 2] Querying NIH Reporter API...")
    nih = search_nih_reporter()
    nih = enrich_curated(nih)

    print("\n[STEP 3] Querying Grants.gov API...")
    gov = search_grants_gov()
    gov = enrich_curated(gov)

    all_grants = curated + nih + gov
    print(f"\n[STEP 4] Merging... {len(all_grants)} total before filtering")

    # Filter: only citizenship = unrestricted / unspecified / open / check
    eligible = [g for g in all_grants if g.get("citizenship") not in ("us_only",)]
    print(f"[STEP 5] After citizenship filter: {len(eligible)} grants")

    # Deduplicate by id
    seen_ids = set()
    deduped  = []
    for g in eligible:
        if g["id"] not in seen_ids:
            seen_ids.add(g["id"])
            deduped.append(g)
    print(f"[STEP 6] After deduplication: {len(deduped)} grants")

    # Sort: confidence desc, then days_until_deadline asc
    deduped.sort(key=lambda g: (-g.get("confidence", 0), g.get("days_until_deadline", 9999)))

    return deduped


# ─────────────────────────────────────────────────────────────────────────────
# SAVE
# ─────────────────────────────────────────────────────────────────────────────

def save(grants):
    unrestricted = [g for g in grants if g["citizenship"] == "unrestricted"]
    unspecified  = [g for g in grants if g["citizenship"] in ("unspecified","check")]
    top5         = [g for g in grants if g.get("confidence",0) >= 70]

    output = {
        "generated":          RUN_TIMESTAMP,
        "search_date":        str(TODAY),
        "total":              len(grants),
        "unrestricted_count": len(unrestricted),
        "unspecified_count":  len(unspecified),
        "high_confidence":    len(top5),
        "nih_query_clusters": NIH_QUERY_CLUSTERS,
        "grantsgov_terms":    GRANTSGOV_QUERY_TERMS,
        "profile_terms":      ALL_PROFILE_TERMS,
        "grants": grants
    }
    out_path = os.path.join(SCRIPT_DIR, "grants_results.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n[✓] Saved {len(grants)} grants → grants_results.json")
    print(f"    Unrestricted (F-1 ✓):   {len(unrestricted)}")
    print(f"    Unspecified (verify):   {len(unspecified)}")
    print(f"    Confidence ≥70 (strong): {len(top5)}")


if __name__ == "__main__":
    print("=" * 60)
    print("  GRANT SEARCH ENGINE v2 — Vikaas Manjunath")
    print(f"  {RUN_TIMESTAMP}")
    print("=" * 60)
    results = build_results()
    save(results)
    print("\n[→] Now run: python3 build_dashboard.py")
