"""
Therapy Area Registry — the single source of truth for the DROP Tax platform.

Every therapy-area / indication that the platform can structure and price is
defined here ONCE. The value engine, the applicability ("Brain") resolver, the
web-sweeper query builder, and the frontend all read from this registry, so
adding a new indication is a data change here — not a code change elsewhere.

Design notes
------------
* Endpoints are defined PER INDICATION (not per therapy area) because the
  clinically relevant endpoint differs by indication.
* Every endpoint carries a benefit `direction` and a `norm` spec. The engine
  uses `norm` to convert a raw endpoint value into a normalised efficacy score
  e in [0, 1] (1 = best achievable), from which a downstream "event / failure"
  proxy probability is derived, giving a therapy-area-appropriate,
  honestly-labelled relative proxy.
* `treatment_model` / `route_default` / `care_settings` seed the applicability
  resolver; drug-level metadata overrides them when known.

Every endpoint here is defined per indication for the covered therapy areas.
"""

from typing import Optional, Dict, Any, List


# ──────────────────────────────────────────────────────────────────────────
# Endpoint normalisation
# ──────────────────────────────────────────────────────────────────────────
# norm.type semantics (value → efficacy score e in [0,1], 1 = best):
#   "months"        time-to-event; e = value / good
#   "reduction_pct" a % reduction in a lower-better biomarker; e = value / good
#   "rate_pct"      a higher-better % (responder / functional independence); e = value / good
#   "hr"            hazard ratio (lower-better); RRR = 1 - HR; e = RRR / good
#   "mmhg"          absolute mmHg reduction (lower-better outcome); e = value / good
# `good` is the value at which efficacy is considered maximal for scaling.

def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def normalize_efficacy(norm: Dict[str, Any], value: Optional[float]) -> Optional[float]:
    """Convert a raw endpoint value into an efficacy score e in [0,1] (1=best).
    Returns None when the value is missing — callers must NOT fabricate."""
    if value is None or norm is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None

    ntype = norm.get("type")
    good = float(norm.get("good", 1) or 1)

    if ntype == "hr":
        rrr = 1.0 - v
        return _clamp(rrr / good)
    if ntype in ("months", "reduction_pct", "rate_pct", "mmhg"):
        return _clamp(v / good)
    return None


def event_probability_from_primary(entry: Dict[str, Any], value: Optional[float]) -> Optional[float]:
    """Downstream clinical-event / treatment-failure proxy in [0.02, 0.98].
    Higher efficacy → lower event probability. None when value is missing."""
    if not entry:
        return None
    e = normalize_efficacy(entry["primary_endpoint"].get("norm"), value)
    if e is None:
        return None
    return _clamp(1.0 - e, 0.02, 0.98)


# ──────────────────────────────────────────────────────────────────────────
# The registry
# ──────────────────────────────────────────────────────────────────────────
# Each endpoint: {key, label, unit, direction, norm, definition}
# Each entry:    {category, indication, aliases, primary_endpoint,
#                 secondary_endpoints, safety_label, hazard_ratio_label,
#                 event, treatment_model, route_default, care_settings,
#                 search_terms, comorbidity_rules}

INDICATION_REGISTRY: Dict[str, Dict[str, Any]] = {

    # ═══════════════ CVD — Cardiology & Lipidology ═══════════════
    "cardiovascular risk reduction": {
        "category": "CVD",
        "indication": "Cardiovascular Risk Reduction",
        "aliases": ["cv risk reduction", "mace reduction", "cardiovascular outcomes", "ascvd risk reduction",
                    "secondary prevention", "post-pci", "acute coronary syndrome", "acs", "antiplatelet"],
        "primary_endpoint": {
            "key": "mace_hr", "label": "3-pt MACE Risk Reduction", "unit": "HR", "direction": "lower_better",
            "norm": {"type": "hr", "good": 0.30},
            "definition": "Hazard ratio for 3-point Major Adverse Cardiovascular Events (CV death, MI, stroke) vs comparator. HR<1 means fewer events; a 30% relative risk reduction is treated as maximal benefit for scoring.",
        },
        "secondary_endpoints": [
            {"key": "cv_mortality_hr", "label": "CV Mortality HR", "unit": "HR", "direction": "lower_better",
             "definition": "Hazard ratio for cardiovascular death."},
            {"key": "acm_hr", "label": "All-cause Mortality HR", "unit": "HR", "direction": "lower_better",
             "definition": "Hazard ratio for death from any cause."},
            {"key": "nnt", "label": "Number Needed to Treat", "unit": "patients", "direction": "lower_better",
             "definition": "Patients treated to prevent one event."},
        ],
        "safety_label": "Serious AEs",
        "hazard_ratio_label": "MACE HR",
        "event": {"label": "Major cardiovascular event (MI / stroke / CV death)", "cost_key": "major_event_cost"},
        "treatment_model": "chronic_ongoing", "route_default": "sc_injection", "care_settings": ["HOME", "OPD"],
        "search_terms": ['"{drug}" cardiovascular outcomes MACE hazard ratio', '"{drug}" CV death myocardial infarction stroke risk reduction'],
        "comorbidity_rules": [
            {"id": "renal", "label": "Renal Impairment", "note": "Dose review for renally-cleared agents."},
            {"id": "diabetes", "label": "Diabetes", "note": "Common comorbidity; may broaden indication."},
        ],
    },
    "heart failure": {
        "category": "CVD",
        "indication": "Heart Failure",
        "aliases": ["hfref", "hfpef", "chronic heart failure", "cardiac failure", "heart-failure"],
        "primary_endpoint": {
            "key": "hf_event_hr", "label": "CV-death / HF-hospitalisation HR", "unit": "HR", "direction": "lower_better",
            "norm": {"type": "hr", "good": 0.25},
            "definition": "Hazard ratio for the composite of cardiovascular death or heart-failure hospitalisation vs comparator.",
        },
        "secondary_endpoints": [
            {"key": "kccq", "label": "KCCQ Score Change", "unit": "points", "direction": "higher_better",
             "definition": "Kansas City Cardiomyopathy Questionnaire — patient-reported HF health status."},
            {"key": "ntprobnp", "label": "NT-proBNP Change", "unit": "%", "direction": "lower_better",
             "definition": "Change in NT-proBNP, a biomarker of cardiac wall stress."},
        ],
        "safety_label": "Serious AEs",
        "hazard_ratio_label": "HF-event HR",
        "event": {"label": "Heart-failure hospitalisation", "cost_key": "major_event_cost"},
        "treatment_model": "chronic_ongoing", "route_default": "oral", "care_settings": ["HOME"],
        "search_terms": ['"{drug}" heart failure hospitalization cardiovascular death hazard ratio', '"{drug}" HFrEF HFpEF outcomes trial'],
        "comorbidity_rules": [
            {"id": "renal", "label": "Renal Impairment", "note": "Monitor eGFR/potassium."},
            {"id": "hypotension", "label": "Hypotension", "note": "Titrate to avoid symptomatic hypotension."},
        ],
    },
    "hypercholesterolemia": {
        "category": "CVD",
        "indication": "Hypercholesterolemia / Dyslipidemia",
        "aliases": ["dyslipidemia", "dyslipidaemia", "high cholesterol", "ldl lowering", "hyperlipidemia",
                    "ascvd", "familial hypercholesterolemia", "high ldl", "hypertriglyceridemia",
                    "triglyceride", "statin", "lipid"],
        "primary_endpoint": {
            "key": "ldl_reduction", "label": "LDL-C Reduction", "unit": "%", "direction": "lower_better",
            "norm": {"type": "reduction_pct", "good": 55.0},
            "definition": "Percentage reduction in LDL cholesterol vs baseline; ~55% is treated as maximal for scoring.",
        },
        "secondary_endpoints": [
            {"key": "apob", "label": "ApoB Reduction", "unit": "%", "direction": "lower_better",
             "definition": "Reduction in apolipoprotein B."},
            {"key": "lpa", "label": "Lp(a) Reduction", "unit": "%", "direction": "lower_better",
             "definition": "Reduction in lipoprotein(a)."},
            {"key": "mace_hr", "label": "MACE HR", "unit": "HR", "direction": "lower_better",
             "definition": "Cardiovascular outcome benefit where available."},
        ],
        "safety_label": "Serious AEs",
        "hazard_ratio_label": "MACE HR",
        "event": {"label": "Atherosclerotic cardiovascular event", "cost_key": "major_event_cost"},
        "treatment_model": "chronic_ongoing", "route_default": "oral", "care_settings": ["HOME"],
        "search_terms": ['"{drug}" LDL cholesterol reduction percent lipid lowering', '"{drug}" ApoB Lp(a) cardiovascular outcomes'],
        "comorbidity_rules": [
            {"id": "hepatic", "label": "Hepatic Impairment", "note": "Monitor transaminases for some agents."},
            {"id": "diabetes", "label": "Diabetes", "note": "Frequent comorbidity in ASCVD."},
        ],
    },
    "hypertension": {
        "category": "CVD",
        "indication": "Hypertension",
        "aliases": ["high blood pressure", "resistant hypertension", "htn", "hypertensive",
                    "antihypertensive", "controlled hypotension"],
        "primary_endpoint": {
            "key": "sbp_reduction", "label": "Systolic BP Reduction", "unit": "mmHg", "direction": "lower_better",
            "norm": {"type": "mmhg", "good": 20.0},
            "definition": "Absolute reduction in systolic blood pressure vs comparator; ~20 mmHg treated as maximal for scoring.",
        },
        "secondary_endpoints": [
            {"key": "dbp_reduction", "label": "Diastolic BP Reduction", "unit": "mmHg", "direction": "lower_better",
             "definition": "Absolute reduction in diastolic blood pressure."},
            {"key": "bp_control_rate", "label": "BP Control Rate", "unit": "%", "direction": "higher_better",
             "definition": "Proportion achieving guideline BP target."},
        ],
        "safety_label": "Serious AEs",
        "hazard_ratio_label": "CV-event HR",
        "event": {"label": "Hypertensive cardiovascular event", "cost_key": "major_event_cost"},
        "treatment_model": "chronic_ongoing", "route_default": "oral", "care_settings": ["HOME"],
        "search_terms": ['"{drug}" systolic blood pressure reduction mmHg hypertension', '"{drug}" blood pressure control rate trial'],
        "comorbidity_rules": [
            {"id": "renal", "label": "Renal Impairment", "note": "Common in resistant hypertension."},
        ],
    },

    "chronic stable angina": {
        "category": "CVD",
        "indication": "Chronic Stable Angina",
        "aliases": ["angina", "angina pectoris", "antianginal", "stable angina", "anginal prophylaxis"],
        "primary_endpoint": {
            "key": "angina_frequency", "label": "Angina Frequency Reduction", "unit": "%", "direction": "lower_better",
            "norm": {"type": "reduction_pct", "good": 50.0},
            "definition": "Percentage reduction in weekly angina episodes vs baseline; ~50% treated as maximal for scoring.",
        },
        "secondary_endpoints": [
            {"key": "ett", "label": "Exercise Tolerance Time", "unit": "sec", "direction": "higher_better",
             "definition": "Increase in total exercise treadmill time."},
            {"key": "gtn_use", "label": "Short-acting Nitrate Use", "unit": "%", "direction": "lower_better",
             "definition": "Reduction in rescue nitrate consumption."},
        ],
        "safety_label": "Serious AEs",
        "hazard_ratio_label": "Ischaemic-event HR",
        "event": {"label": "Acute coronary event / revascularisation", "cost_key": "major_event_cost"},
        "treatment_model": "chronic_ongoing", "route_default": "oral", "care_settings": ["HOME"],
        "search_terms": ['"{drug}" chronic stable angina episodes exercise tolerance trial',
                         '"{drug}" antianginal efficacy nitrate use'],
        "comorbidity_rules": [
            {"id": "hypotension", "label": "Hypotension", "note": "Nitrates and some agents lower BP."},
        ],
    },
    "arrhythmia": {
        "category": "CVD",
        "indication": "Cardiac Arrhythmia (Rhythm Control)",
        "aliases": ["arrhythmias", "ventricular arrhythmia", "atrial flutter", "sinus rhythm",
                    "supraventricular", "svt", "tachycardia", "vt/vf", "antiarrhythmic"],
        "primary_endpoint": {
            "key": "sinus_rhythm", "label": "Sinus-Rhythm Maintenance", "unit": "%", "direction": "higher_better",
            "norm": {"type": "rate_pct", "good": 70.0},
            "definition": "Proportion maintaining sinus rhythm (or free of arrhythmia recurrence) at follow-up.",
        },
        "secondary_endpoints": [
            {"key": "recurrence_hr", "label": "Arrhythmia Recurrence HR", "unit": "HR", "direction": "lower_better",
             "definition": "Hazard ratio for arrhythmia recurrence vs comparator."},
            {"key": "hosp_rate", "label": "Cardiovascular Hospitalisation", "unit": "%", "direction": "lower_better",
             "definition": "Rate of cardiovascular hospitalisation."},
        ],
        "safety_label": "Proarrhythmia / serious AEs",
        "hazard_ratio_label": "Recurrence HR",
        "event": {"label": "Arrhythmia-related hospitalisation", "cost_key": "major_event_cost"},
        "treatment_model": "chronic_ongoing", "route_default": "oral", "care_settings": ["HOME", "OPD"],
        "search_terms": ['"{drug}" sinus rhythm maintenance atrial fibrillation recurrence trial',
                         '"{drug}" antiarrhythmic efficacy proarrhythmia safety'],
        "comorbidity_rules": [
            {"id": "hepatic", "label": "Hepatic Impairment", "note": "Amiodarone and others require LFT monitoring."},
            {"id": "thyroid", "label": "Thyroid Disease", "note": "Amiodarone affects thyroid function."},
        ],
    },
    "venous thromboembolism": {
        "category": "CVD",
        "indication": "Thromboembolism Prevention (AF / VTE)",
        "aliases": ["vte", "non-valvular af", "deep vein thrombosis", "dvt", "pulmonary embolism",
                    "anticoagulation", "anticoagulant", "mechanical heart valve", "valve prosthesis",
                    "thromboprophylaxis", "antithrombotic"],
        "primary_endpoint": {
            "key": "stroke_se_hr", "label": "Stroke / Systemic-Embolism HR", "unit": "HR", "direction": "lower_better",
            "norm": {"type": "hr", "good": 0.35},
            "definition": "Hazard ratio for stroke or systemic embolism (AF) or recurrent VTE vs comparator.",
        },
        "secondary_endpoints": [
            {"key": "vte_recurrence", "label": "VTE Recurrence HR", "unit": "HR", "direction": "lower_better",
             "definition": "Hazard ratio for recurrent venous thromboembolism."},
            {"key": "acm_hr", "label": "All-cause Mortality HR", "unit": "HR", "direction": "lower_better",
             "definition": "Hazard ratio for death from any cause."},
        ],
        "safety_label": "Major bleeding",
        "hazard_ratio_label": "Stroke/SE HR",
        "event": {"label": "Stroke or thromboembolic event", "cost_key": "major_event_cost"},
        "treatment_model": "chronic_ongoing", "route_default": "oral", "care_settings": ["HOME"],
        "search_terms": ['"{drug}" atrial fibrillation stroke systemic embolism hazard ratio major bleeding',
                         '"{drug}" venous thromboembolism recurrence anticoagulation trial'],
        "comorbidity_rules": [
            {"id": "bleeding_risk", "label": "Bleeding Risk", "note": "Assess HAS-BLED; contraindicated in active bleeding."},
            {"id": "renal", "label": "Renal Impairment", "note": "DOAC dose adjustment by creatinine clearance."},
        ],
    },

    # ═══════════════ CVS — Cerebrovascular & Acute Vascular ═══════════════
    "acute ischemic stroke": {
        "category": "CVS",
        "indication": "Acute Ischemic Stroke",
        "aliases": ["ischemic stroke", "ischaemic stroke", "acute stroke", "thrombolysis stroke"],
        "primary_endpoint": {
            "key": "functional_independence", "label": "Functional Independence (mRS 0–2)", "unit": "%", "direction": "higher_better",
            "norm": {"type": "rate_pct", "good": 60.0},
            "definition": "Proportion achieving modified Rankin Scale 0–2 (functional independence) at 90 days.",
        },
        "secondary_endpoints": [
            {"key": "recanalization", "label": "Recanalisation Rate", "unit": "%", "direction": "higher_better",
             "definition": "Proportion achieving vessel recanalisation."},
        ],
        "safety_label": "Symptomatic ICH",
        "hazard_ratio_label": "Poor-outcome HR",
        "event": {"label": "Disability / rehabilitation burden", "cost_key": "major_event_cost"},
        "treatment_model": "acute_single_dose", "route_default": "iv_bolus", "care_settings": ["IPD"],
        "search_terms": ['"{drug}" acute ischemic stroke functional independence mRS thrombolysis', '"{drug}" stroke recanalization symptomatic intracranial hemorrhage'],
        "comorbidity_rules": [
            {"id": "bleeding_risk", "label": "Bleeding Risk", "note": "Contraindication screening for thrombolytics."},
        ],
    },
    "acute myocardial infarction": {
        "category": "CVS",
        "indication": "Acute Myocardial Infarction",
        "aliases": ["stemi", "acute mi", "heart attack", "myocardial infarction"],
        "primary_endpoint": {
            "key": "reperfusion", "label": "Reperfusion / TIMI-3 Flow", "unit": "%", "direction": "higher_better",
            "norm": {"type": "rate_pct", "good": 70.0},
            "definition": "Proportion achieving successful reperfusion (TIMI grade 3 flow).",
        },
        "secondary_endpoints": [
            {"key": "mortality_90d", "label": "90-day Mortality", "unit": "%", "direction": "lower_better",
             "definition": "Death within 90 days."},
        ],
        "safety_label": "Major bleeding",
        "hazard_ratio_label": "Mortality HR",
        "event": {"label": "Reinfarction / cardiac event", "cost_key": "major_event_cost"},
        "treatment_model": "acute_single_dose", "route_default": "iv_bolus", "care_settings": ["IPD"],
        "search_terms": ['"{drug}" acute myocardial infarction reperfusion TIMI flow', '"{drug}" STEMI mortality bleeding trial'],
        "comorbidity_rules": [
            {"id": "bleeding_risk", "label": "Bleeding Risk", "note": "Screen before fibrinolysis."},
        ],
    },

    # ═══════════════ Metabolic — Endocrinology ═══════════════
    "chronic weight management": {
        "category": "Metabolic",
        "indication": "Chronic Weight Management",
        "aliases": ["obesity", "weight management", "weight loss", "overweight"],
        "primary_endpoint": {
            "key": "weight_reduction", "label": "Mean Body-Weight Reduction", "unit": "%", "direction": "higher_better",
            "norm": {"type": "rate_pct", "good": 20.0},
            "definition": "Mean percentage body-weight reduction vs baseline; ~20% treated as maximal for scoring.",
        },
        "secondary_endpoints": [
            {"key": "responder_5", "label": "≥5% Weight-loss Responders", "unit": "%", "direction": "higher_better",
             "definition": "Proportion losing at least 5% body weight."},
            {"key": "responder_10", "label": "≥10% Weight-loss Responders", "unit": "%", "direction": "higher_better",
             "definition": "Proportion losing at least 10% body weight."},
            {"key": "waist", "label": "Waist Circumference Change", "unit": "cm", "direction": "lower_better",
             "definition": "Reduction in waist circumference."},
        ],
        "safety_label": "Serious / GI AEs",
        "hazard_ratio_label": None,
        "event": {"label": "Obesity-related complication", "cost_key": "complication_cost"},
        "treatment_model": "chronic_ongoing", "route_default": "sc_injection", "care_settings": ["HOME"],
        "search_terms": ['"{drug}" body weight reduction percent obesity trial', '"{drug}" weight loss responders SURMOUNT STEP'],
        "comorbidity_rules": [
            {"id": "diabetes", "label": "Diabetes", "note": "Overlaps with T2D indication."},
            {"id": "gi", "label": "GI Disorders", "note": "GI tolerability affects adherence."},
        ],
    },
    "type 2 diabetes": {
        "category": "Metabolic",
        "indication": "Type 2 Diabetes",
        "aliases": ["t2dm", "t2d", "diabetes mellitus type 2", "diabetes", "glycaemic", "glycemic",
                    "insulin", "prandial insulin", "basal insulin", "hyperglyc"],
        "primary_endpoint": {
            "key": "hba1c_reduction", "label": "HbA1c Reduction", "unit": "%", "direction": "lower_better",
            "norm": {"type": "reduction_pct", "good": 2.0},
            "definition": "Absolute HbA1c reduction (percentage points) vs baseline; ~2.0 points treated as maximal for scoring.",
        },
        "secondary_endpoints": [
            {"key": "fpg", "label": "Fasting Plasma Glucose", "unit": "%", "direction": "lower_better",
             "definition": "Reduction in fasting plasma glucose."},
            {"key": "hba1c_target", "label": "% Achieving HbA1c <7%", "unit": "%", "direction": "higher_better",
             "definition": "Proportion reaching glycaemic target."},
            {"key": "weight", "label": "Weight Change", "unit": "kg", "direction": "lower_better",
             "definition": "Body-weight change (weight-loss is favourable)."},
        ],
        "safety_label": "Serious / GI AEs",
        "hazard_ratio_label": None,
        "event": {"label": "Diabetic complication", "cost_key": "complication_cost"},
        "treatment_model": "chronic_ongoing", "route_default": "oral", "care_settings": ["HOME"],
        "search_terms": ['"{drug}" HbA1c reduction type 2 diabetes trial', '"{drug}" fasting glucose glycemic control'],
        "comorbidity_rules": [
            {"id": "renal", "label": "Renal Impairment", "note": "Dose adjust some agents by eGFR."},
            {"id": "cardiac", "label": "Cardiac Disease", "note": "Prefer agents with CV benefit."},
        ],
    },

    # ═══════════════ Women's Health — Gynecology ═══════════════
    "vasomotor symptoms": {
        "category": "Women's Health",
        "indication": "Vasomotor Symptoms",
        "aliases": ["vms", "menopause", "menopausal hot flashes", "hot flushes", "menopausal symptoms",
                    "menopausal hrt", "hormone replacement", "atrophic vaginitis", "hypoestrogenism"],
        "primary_endpoint": {
            "key": "vms_frequency", "label": "VMS Frequency Reduction", "unit": "%", "direction": "lower_better",
            "norm": {"type": "reduction_pct", "good": 60.0},
            "definition": "Percentage reduction in frequency of moderate-to-severe vasomotor symptoms vs baseline.",
        },
        "secondary_endpoints": [
            {"key": "vms_severity", "label": "VMS Severity Reduction", "unit": "%", "direction": "lower_better",
             "definition": "Reduction in VMS severity score."},
            {"key": "sleep", "label": "Sleep Disturbance Improvement", "unit": "%", "direction": "higher_better",
             "definition": "Improvement in sleep measures."},
        ],
        "safety_label": "Serious AEs",
        "hazard_ratio_label": None,
        "event": {"label": "Persistent symptom burden", "cost_key": "complication_cost"},
        "treatment_model": "chronic_ongoing", "route_default": "oral", "care_settings": ["HOME"],
        "search_terms": ['"{drug}" vasomotor symptoms hot flash frequency reduction menopause', '"{drug}" SKYLIGHT VMS trial'],
        "comorbidity_rules": [
            {"id": "hepatic", "label": "Hepatic Impairment", "note": "Monitor LFTs for some NK3 antagonists."},
        ],
    },
    "osteoporosis": {
        "category": "Women's Health",
        "indication": "Osteoporosis",
        "aliases": ["postmenopausal osteoporosis", "bone loss", "fracture prevention", "osteopenia",
                    "bone mineral density", "vitamin d deficiency"],
        "primary_endpoint": {
            "key": "vertebral_fracture_hr", "label": "Vertebral-Fracture Risk Reduction", "unit": "HR", "direction": "lower_better",
            "norm": {"type": "hr", "good": 0.60},
            "definition": "Hazard ratio for new vertebral fracture vs comparator; ~60% relative risk reduction treated as maximal.",
        },
        "secondary_endpoints": [
            {"key": "bmd_spine", "label": "BMD Change (Spine)", "unit": "%", "direction": "higher_better",
             "definition": "Percentage change in lumbar-spine bone mineral density."},
            {"key": "bmd_hip", "label": "BMD Change (Hip)", "unit": "%", "direction": "higher_better",
             "definition": "Percentage change in total-hip bone mineral density."},
            {"key": "nonvert_fracture", "label": "Non-vertebral Fracture RRR", "unit": "HR", "direction": "lower_better",
             "definition": "Hazard ratio for non-vertebral fracture."},
        ],
        "safety_label": "Serious AEs",
        "hazard_ratio_label": "Fracture HR",
        "event": {"label": "Osteoporotic fracture", "cost_key": "major_event_cost"},
        "treatment_model": "fixed_course", "route_default": "sc_injection", "care_settings": ["OPD", "HOME"],
        "search_terms": ['"{drug}" vertebral fracture risk reduction osteoporosis trial', '"{drug}" bone mineral density spine hip ARCH FRAME'],
        "comorbidity_rules": [
            {"id": "cardiac", "label": "Cardiac Disease", "note": "CV risk labelling for some anabolic agents."},
            {"id": "hypocalcemia", "label": "Hypocalcemia", "note": "Correct calcium/vitamin D before start."},
        ],
    },
    "endometriosis": {
        "category": "Women's Health",
        "indication": "Endometriosis",
        "aliases": ["endometriosis-associated pain", "pelvic pain endometriosis"],
        "primary_endpoint": {
            "key": "dysmenorrhea_responder", "label": "Dysmenorrhoea Responder Rate", "unit": "%", "direction": "higher_better",
            "norm": {"type": "rate_pct", "good": 55.0},
            "definition": "Proportion of responders for menstrual pelvic pain (dysmenorrhoea) with reduced/stable rescue analgesic use.",
        },
        "secondary_endpoints": [
            {"key": "nmpp", "label": "Non-menstrual Pelvic Pain Responder", "unit": "%", "direction": "higher_better",
             "definition": "Responder rate for non-menstrual pelvic pain."},
            {"key": "analgesic_use", "label": "Analgesic Use Reduction", "unit": "%", "direction": "lower_better",
             "definition": "Reduction in rescue analgesic use."},
        ],
        "safety_label": "BMD loss (GnRH antagonists)",
        "hazard_ratio_label": None,
        "event": {"label": "Uncontrolled pain / surgery", "cost_key": "complication_cost"},
        "treatment_model": "fixed_course", "route_default": "oral", "care_settings": ["HOME"],
        "search_terms": ['"{drug}" endometriosis dysmenorrhea pelvic pain responder trial', '"{drug}" GnRH antagonist endometriosis bone mineral density'],
        "comorbidity_rules": [
            {"id": "low_bmd", "label": "Low BMD", "note": "GnRH antagonists reduce BMD; limit duration / add-back."},
        ],
    },
    "uterine fibroids": {
        "category": "Women's Health",
        "indication": "Uterine Fibroids",
        "aliases": ["uterine leiomyoma", "fibroids", "myoma"],
        "primary_endpoint": {
            "key": "mbl_responder", "label": "Menstrual Blood-Loss Responder (<80 mL & ≥50% ↓)", "unit": "%", "direction": "higher_better",
            "norm": {"type": "rate_pct", "good": 70.0},
            "definition": "Proportion achieving menstrual blood loss <80 mL AND ≥50% reduction from baseline (alkaline-hematin).",
        },
        "secondary_endpoints": [
            {"key": "amenorrhea", "label": "Amenorrhoea Rate", "unit": "%", "direction": "higher_better",
             "definition": "Proportion achieving amenorrhoea."},
            {"key": "hemoglobin", "label": "Haemoglobin Improvement", "unit": "g/dL", "direction": "higher_better",
             "definition": "Improvement in haemoglobin."},
        ],
        "safety_label": "BMD loss",
        "hazard_ratio_label": None,
        "event": {"label": "Anaemia / hysterectomy", "cost_key": "complication_cost"},
        "treatment_model": "fixed_course", "route_default": "oral", "care_settings": ["HOME"],
        "search_terms": ['"{drug}" uterine fibroids menstrual blood loss responder trial', '"{drug}" leiomyoma amenorrhea hemoglobin LIBERTY'],
        "comorbidity_rules": [
            {"id": "low_bmd", "label": "Low BMD", "note": "GnRH antagonists reduce BMD; add-back therapy typical."},
            {"id": "anemia", "label": "Anaemia", "note": "Correct iron deficiency."},
        ],
    },
    "postpartum haemorrhage": {
        "category": "Women's Health",
        "indication": "Postpartum Haemorrhage (Prevention & Treatment)",
        "aliases": ["pph", "postpartum hemorrhage", "uterine atony", "uterotonic",
                    "uterine involution", "refractory pph"],
        "primary_endpoint": {
            "key": "pph_reduction", "label": "PPH Incidence Reduction (blood loss ≥500 mL)", "unit": "%",
            "direction": "lower_better", "norm": {"type": "reduction_pct", "good": 50.0},
            "definition": "Relative reduction in the proportion of women with postpartum blood loss ≥500 mL.",
        },
        "secondary_endpoints": [
            {"key": "mean_blood_loss", "label": "Mean Blood Loss", "unit": "mL", "direction": "lower_better",
             "definition": "Mean measured postpartum blood loss."},
            {"key": "transfusion_rate", "label": "Transfusion Rate", "unit": "%", "direction": "lower_better",
             "definition": "Proportion requiring blood transfusion."},
        ],
        "safety_label": "Serious AEs",
        "hazard_ratio_label": "Haemorrhage HR",
        "event": {"label": "Maternal haemorrhage requiring transfusion/surgery", "cost_key": "major_event_cost"},
        "treatment_model": "acute_single_dose", "route_default": "iv_bolus", "care_settings": ["IPD"],
        "search_terms": ['"{drug}" postpartum haemorrhage prevention blood loss randomised trial',
                         '"{drug}" uterotonic third stage labour transfusion'],
        "comorbidity_rules": [
            {"id": "hypertension", "label": "Hypertension", "note": "Ergometrine contraindicated in hypertension/pre-eclampsia."},
        ],
    },
    "preterm labour": {
        "category": "Women's Health",
        "indication": "Preterm Labour (Tocolysis)",
        "aliases": ["tocolysis", "tocolytic", "threatened preterm labor", "threatened preterm labour",
                    "preterm birth", "suppression of preterm labor"],
        "primary_endpoint": {
            "key": "delay_48h", "label": "Birth Delayed ≥48 h", "unit": "%", "direction": "higher_better",
            "norm": {"type": "rate_pct", "good": 80.0},
            "definition": "Proportion of women undelivered 48 hours after starting tocolysis — the window for antenatal steroids and transfer.",
        },
        "secondary_endpoints": [
            {"key": "delay_7d", "label": "Birth Delayed ≥7 days", "unit": "%", "direction": "higher_better",
             "definition": "Proportion undelivered at 7 days."},
            {"key": "nicu_admission", "label": "NICU Admission", "unit": "%", "direction": "lower_better",
             "definition": "Neonatal intensive care admission rate."},
        ],
        "safety_label": "Serious maternal AEs",
        "hazard_ratio_label": "Preterm-birth HR",
        "event": {"label": "Preterm birth / neonatal intensive care", "cost_key": "major_event_cost"},
        "treatment_model": "fixed_course", "route_default": "iv_infusion", "care_settings": ["IPD"],
        "search_terms": ['"{drug}" tocolysis preterm labour delay 48 hours randomised trial',
                         '"{drug}" preterm birth neonatal outcomes tocolytic'],
        "comorbidity_rules": [
            {"id": "cardiac", "label": "Cardiac Disease", "note": "Beta-agonist tocolytics raise maternal cardiac risk."},
        ],
    },
    "labour induction": {
        "category": "Women's Health",
        "indication": "Labour Induction & Cervical Ripening",
        "aliases": ["induction of labor", "induction of labour", "cervical ripening", "cervical priming",
                    "augmentation of labor", "augmentation of labour"],
        "primary_endpoint": {
            "key": "vaginal_delivery_24h", "label": "Vaginal Delivery within 24 h", "unit": "%",
            "direction": "higher_better", "norm": {"type": "rate_pct", "good": 70.0},
            "definition": "Proportion achieving vaginal delivery within 24 hours of induction.",
        },
        "secondary_endpoints": [
            {"key": "caesarean_rate", "label": "Caesarean Section Rate", "unit": "%", "direction": "lower_better",
             "definition": "Proportion delivered by caesarean section."},
            {"key": "time_to_delivery", "label": "Induction-to-Delivery Interval", "unit": "hours", "direction": "lower_better",
             "definition": "Mean time from induction to delivery."},
        ],
        "safety_label": "Uterine hyperstimulation",
        "hazard_ratio_label": "Caesarean HR",
        "event": {"label": "Caesarean section / prolonged labour", "cost_key": "major_event_cost"},
        "treatment_model": "acute_single_dose", "route_default": "iv_infusion", "care_settings": ["IPD"],
        "search_terms": ['"{drug}" induction of labour vaginal delivery 24 hours randomised trial',
                         '"{drug}" cervical ripening caesarean rate'],
        "comorbidity_rules": [
            {"id": "prior_caesarean", "label": "Previous Caesarean", "note": "Prostaglandin induction raises rupture risk after caesarean."},
        ],
    },
    "iron deficiency anaemia": {
        "category": "Women's Health",
        "indication": "Iron-Deficiency Anaemia (Pregnancy & Postpartum)",
        "aliases": ["iron-deficiency anemia", "iron deficiency anemia", "antianemic", "anaemia",
                    "megaloblastic anemia", "neural-tube-defect prevention", "iron deficiency"],
        "primary_endpoint": {
            "key": "hb_increase", "label": "Haemoglobin Increase", "unit": "g/dL", "direction": "higher_better",
            "norm": {"type": "rate_pct", "good": 3.0},
            "definition": "Mean rise in haemoglobin from baseline; ~3 g/dL treated as maximal correction for scoring.",
        },
        "secondary_endpoints": [
            {"key": "ferritin", "label": "Ferritin Repletion", "unit": "ng/mL", "direction": "higher_better",
             "definition": "Increase in serum ferritin (iron stores)."},
            {"key": "transfusion_avoided", "label": "Transfusion Avoidance", "unit": "%", "direction": "higher_better",
             "definition": "Proportion avoiding blood transfusion."},
        ],
        "safety_label": "Serious AEs",
        "hazard_ratio_label": None,
        "event": {"label": "Severe anaemia requiring transfusion", "cost_key": "complication_cost"},
        "treatment_model": "fixed_course", "route_default": "oral", "care_settings": ["HOME", "OPD"],
        "search_terms": ['"{drug}" iron deficiency anaemia haemoglobin increase pregnancy trial',
                         '"{drug}" ferritin repletion intravenous iron'],
        "comorbidity_rules": [
            {"id": "gi", "label": "GI Intolerance", "note": "Oral iron tolerability drives adherence; IV avoids this."},
        ],
    },
    "pre-eclampsia": {
        "category": "Women's Health",
        "indication": "Pre-eclampsia / Eclampsia",
        "aliases": ["eclampsia", "severe pre-eclampsia", "seizure prophylaxis", "pre-eclamptic"],
        "primary_endpoint": {
            "key": "eclampsia_hr", "label": "Eclamptic Seizure Risk Reduction", "unit": "HR",
            "direction": "lower_better", "norm": {"type": "hr", "good": 0.50},
            "definition": "Hazard ratio for eclamptic seizure vs comparator or placebo.",
        },
        "secondary_endpoints": [
            {"key": "maternal_mortality", "label": "Maternal Mortality", "unit": "%", "direction": "lower_better",
             "definition": "Maternal death rate."},
        ],
        "safety_label": "Serious maternal AEs",
        "hazard_ratio_label": "Seizure HR",
        "event": {"label": "Eclamptic seizure / maternal critical care", "cost_key": "major_event_cost"},
        "treatment_model": "acute_single_dose", "route_default": "iv_infusion", "care_settings": ["IPD"],
        "search_terms": ['"{drug}" eclampsia seizure prophylaxis magnesium randomised trial',
                         '"{drug}" pre-eclampsia maternal outcomes'],
        "comorbidity_rules": [
            {"id": "renal", "label": "Renal Impairment", "note": "Magnesium accumulates in renal impairment — monitor levels."},
        ],
    },
    "fetal lung maturation": {
        "category": "Women's Health",
        "indication": "Fetal Lung Maturation (Antenatal Corticosteroid)",
        "aliases": ["antenatal corticosteroid", "fetal lung maturity", "respiratory distress syndrome prophylaxis"],
        "primary_endpoint": {
            "key": "rds_hr", "label": "Neonatal RDS Risk Reduction", "unit": "HR",
            "direction": "lower_better", "norm": {"type": "hr", "good": 0.45},
            "definition": "Hazard ratio for neonatal respiratory distress syndrome after antenatal corticosteroid.",
        },
        "secondary_endpoints": [
            {"key": "neonatal_mortality", "label": "Neonatal Mortality", "unit": "%", "direction": "lower_better",
             "definition": "Neonatal death rate."},
        ],
        "safety_label": "Serious AEs",
        "hazard_ratio_label": "RDS HR",
        "event": {"label": "Neonatal intensive care admission", "cost_key": "major_event_cost"},
        "treatment_model": "acute_single_dose", "route_default": "sc_injection", "care_settings": ["IPD"],
        "search_terms": ['"{drug}" antenatal corticosteroid neonatal respiratory distress syndrome trial',
                         '"{drug}" fetal lung maturation preterm outcomes'],
        "comorbidity_rules": [
            {"id": "diabetes", "label": "Diabetes", "note": "Antenatal steroids raise maternal glucose."},
        ],
    },
    "heavy menstrual bleeding": {
        "category": "Women's Health",
        "indication": "Heavy Menstrual Bleeding (Menorrhagia)",
        "aliases": ["menorrhagia", "hmb", "abnormal uterine bleeding", "heavy periods",
                    "dysfunctional uterine bleeding", "postpartum haemorrhage", "postpartum hemorrhage"],
        "primary_endpoint": {
            "key": "mbl_reduction", "label": "Menstrual Blood-Loss Reduction (alkaline-hematin)", "unit": "%", "direction": "lower_better",
            "norm": {"type": "reduction_pct", "good": 50.0},
            "definition": "Percentage reduction in objectively-measured menstrual blood loss (alkaline-hematin method) vs baseline.",
        },
        "secondary_endpoints": [
            {"key": "hemoglobin", "label": "Haemoglobin / Ferritin Improvement", "unit": "g/dL", "direction": "higher_better",
             "definition": "Improvement in haemoglobin / iron stores."},
            {"key": "amenorrhea", "label": "Amenorrhoea Rate", "unit": "%", "direction": "higher_better",
             "definition": "Proportion achieving amenorrhoea."},
        ],
        "safety_label": "Serious AEs",
        "hazard_ratio_label": None,
        "event": {"label": "Iron-deficiency anaemia", "cost_key": "complication_cost"},
        "treatment_model": "chronic_ongoing", "route_default": "oral", "care_settings": ["HOME"],
        "search_terms": ['"{drug}" heavy menstrual bleeding blood loss reduction alkaline hematin', '"{drug}" menorrhagia hemoglobin trial'],
        "comorbidity_rules": [
            {"id": "anemia", "label": "Anaemia", "note": "Common; monitor haemoglobin/ferritin."},
        ],
    },
}


# Alias index (built once) → canonical registry key
_ALIAS_INDEX: Dict[str, str] = {}
for _key, _entry in INDICATION_REGISTRY.items():
    _ALIAS_INDEX[_key] = _key
    _ALIAS_INDEX[_entry["indication"].lower()] = _key
    for _alias in _entry.get("aliases", []):
        _ALIAS_INDEX[_alias.lower()] = _key


def resolve_indication(indication: Optional[str]) -> Optional[Dict[str, Any]]:
    """Resolve a free-text indication to its registry entry, or None.
    Matching is exact-key, alias, then substring — never a fuzzy guess that
    could mis-route a drug (anti-hallucination: unknown → None, caller flags)."""
    if not indication:
        return None
    key = indication.strip().lower()
    if key in _ALIAS_INDEX:
        return INDICATION_REGISTRY[_ALIAS_INDEX[key]]
    # Substring match against canonical names + aliases (longest alias wins)
    best = None
    best_len = 0
    for alias, canonical in _ALIAS_INDEX.items():
        if alias in key and len(alias) > best_len:
            best, best_len = canonical, len(alias)
    return INDICATION_REGISTRY[best] if best else None


def get_category(indication: Optional[str]) -> str:
    """Category for an indication; falls back to keyword routing then 'CardioMetabolic'."""
    entry = resolve_indication(indication)
    if entry:
        return entry["category"]
    ind = (indication or "").lower()
    if any(k in ind for k in ("weight", "obesity", "diabetes", "metabolic")):
        return "Metabolic"
    if any(k in ind for k in ("stroke", "cerebro", "infarction", "ischemic")):
        return "CVS"
    if any(k in ind for k in ("heart", "cardio", "vascular", "mace", "cholesterol", "lipid", "hypertension")):
        return "CVD"
    if any(k in ind for k in ("menopause", "vasomotor", "osteoporosis", "endometriosis", "fibroid", "menstrual", "women")):
        return "Women's Health"
    return "CardioMetabolic"


def build_endpoints_summary(entry: Dict[str, Any], primary_value, secondary_values: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Produce the UI `endpoints_summary` array from resolved values.
    Missing values render as 'Data unavailable' — never fabricated."""
    secondary_values = secondary_values or {}
    pe = entry["primary_endpoint"]

    def _fmt(val, unit):
        if val is None:
            return "Data unavailable"
        return f"{val} {unit}".strip()

    rows = [{
        "name": pe["label"], "key": pe["key"], "unit": pe["unit"],
        "value": _fmt(primary_value, pe["unit"]),
        "is_primary": True, "available": primary_value is not None,
    }]
    for se in entry.get("secondary_endpoints", []):
        v = secondary_values.get(se["key"])
        rows.append({
            "name": se["label"], "key": se["key"], "unit": se["unit"],
            "value": _fmt(v, se["unit"]),
            "is_primary": False, "available": v is not None,
        })
    return rows
