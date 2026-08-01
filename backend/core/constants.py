"""
Constants for the DROP Tax Commercial Suite
Regional configurations, pricing data, and market availability
"""

# Regional Constants for Liability Engine
REGIONAL_CONSTANTS = {
    "IN": {
        "daily_wage": 2500,  # ₹2,500 - Average daily wage for productivity calculation
        "hospitalization_cost": 150000,  # ₹1,50,000 - Adverse-event management / hospitalization cost
        "currency_symbol": "₹",
        "currency": "INR",
        "regulator": "CDSCO",
        "regulator_name": "Central Drugs Standard Control Organisation",
        "monthly_salary": 30000,
        "major_event_cost": 1800000,   # cost of a major acute clinical event (MI/stroke/fracture/HF hosp)
        "complication_cost": 150000,   # cost of managing a chronic-disease complication
        "retail_mrp_multiplier": 1.35  # home/retail MRP vs institutional/tender price
    },
    "SG": {
        "daily_wage": 250,  # S$250
        "hospitalization_cost": 15000,  # S$15,000
        "currency_symbol": "S$",
        "currency": "SGD",
        "regulator": "HSA",
        "regulator_name": "Health Sciences Authority",
        "monthly_salary": 5000,
        "major_event_cost": 85000,
        "complication_cost": 15000,
        "retail_mrp_multiplier": 1.20
    },
    "AE": {
        "daily_wage": 500,  # AED 500
        "hospitalization_cost": 45000,  # AED 45,000
        "currency_symbol": "AED",
        "currency": "AED",
        "regulator": "DOH",
        "regulator_name": "Department of Health Abu Dhabi",
        "monthly_salary": 15000,
        "major_event_cost": 250000,
        "complication_cost": 45000,
        "retail_mrp_multiplier": 1.25
    }
}

# ──────────────────────────────────────────────────────────────────────────
# Site-of-care coverage rules (THE market-access nuance)
# The SAME drug reimburses & prices differently by where it is administered:
#   IPD  = inpatient / day-care admission  → bundled inside the hospitalization
#          benefit (typically covered)
#   OPD  = outpatient follow-up            → covered only if on the payer's
#          OPD / day-care drug list (often excluded, esp. India)
#   HOME = self-administered / retail      → self-pay at full MRP (usually
#          excluded), frequently far more expensive than the tender price
# `covered_share` is the fraction typically borne by the payer (0..1);
# the remainder is the patient's out-of-pocket exposure before PAP.
# ──────────────────────────────────────────────────────────────────────────
SETTING_COVERAGE_RULES = {
    "IN": {  # India: strict outpatient-drug exclusions
        "IPD":  {"coverage": "covered",     "covered_share": 0.85, "price_basis": "institutional_tender",
                 "note": "Bundled within the in-patient hospitalization sum-insured."},
        "OPD":  {"coverage": "conditional", "covered_share": 0.20, "price_basis": "institutional_or_retail",
                 "note": "Covered only if on the payer's day-care / OPD drug list; usually limited."},
        "HOME": {"coverage": "excluded",    "covered_share": 0.0,  "price_basis": "retail_mrp",
                 "note": "Self-administered retail purchase at full MRP; not reimbursed."},
    },
    "SG": {  # Singapore: MediShield / MediSave give broader outpatient support
        "IPD":  {"coverage": "covered",     "covered_share": 0.90, "price_basis": "institutional_tender",
                 "note": "Covered under inpatient MediShield Life limits."},
        "OPD":  {"coverage": "conditional", "covered_share": 0.50, "price_basis": "institutional_or_retail",
                 "note": "Subsidised outpatient / chronic-disease programme where eligible."},
        "HOME": {"coverage": "conditional", "covered_share": 0.30, "price_basis": "retail_mrp",
                 "note": "Partial MediSave/CHAS support for eligible chronic medications."},
    },
    "AE": {  # UAE: mandatory insurance with outpatient pharmacy benefits
        "IPD":  {"coverage": "covered",     "covered_share": 0.90, "price_basis": "institutional_tender",
                 "note": "Covered under inpatient insurance benefit."},
        "OPD":  {"coverage": "conditional", "covered_share": 0.60, "price_basis": "institutional_or_retail",
                 "note": "Outpatient pharmacy benefit subject to plan formulary and co-pay."},
        "HOME": {"coverage": "conditional", "covered_share": 0.40, "price_basis": "retail_mrp",
                 "note": "Retail dispensing with plan co-pay where the drug is on formulary."},
    },
}

# Payer Segment Definitions
PAYER_SEGMENTS = {
    "IN": {
        "oop": {
            "name": "Out-of-Pocket (OOP)",
            "description": "Full list price, eligible for PAP schemes",
            "copay_percent": 1.0,
            "annual_cap": None,
            "pap_eligible": True
        },
        "private_insurance": {
            "name": "Private Insurance",
            "description": "Co-pay model with annual cap",
            "copay_percent": 0.20,
            "annual_cap": 500000,
            "pap_eligible": False,
            "pap_advice": "Patient Assistance for Co-Pay"
        },
        "cghs": {
            "name": "CGHS (Govt Scheme)",
            "description": "Zero cost to patient, govt rate applies",
            "copay_percent": 0.0,
            "govt_rate_discount": 0.40,
            "annual_cap": None,
            "pap_eligible": False
        },
        "echs": {
            "name": "ECHS (Ex-Servicemen)",
            "description": "Zero cost to patient, govt rate applies",
            "copay_percent": 0.0,
            "govt_rate_discount": 0.40,
            "annual_cap": None,
            "pap_eligible": False
        },
        "ayushman_bharat": {
            "name": "Ayushman Bharat (PMJAY)",
            "description": "Govt scheme for economically weaker sections",
            "copay_percent": 0.0,
            "govt_rate_discount": 0.50,
            "annual_cap": 500000,
            "pap_eligible": False
        }
    },
    "SG": {
        "oop": {
            "name": "Out-of-Pocket",
            "description": "Full list price",
            "copay_percent": 1.0,
            "annual_cap": None,
            "pap_eligible": True
        },
        "medishield_life": {
            "name": "MediShield Life",
            "description": "National health insurance with co-pay",
            "copay_percent": 0.10,
            "annual_cap": 150000,
            "pap_eligible": False
        },
        "private_insurance": {
            "name": "Private Insurance",
            "description": "Integrated Shield Plan",
            "copay_percent": 0.05,
            "annual_cap": None,
            "pap_eligible": False
        }
    },
    "AE": {
        "oop": {
            "name": "Out-of-Pocket",
            "description": "Full list price",
            "copay_percent": 1.0,
            "annual_cap": None,
            "pap_eligible": True
        },
        "private_insurance": {
            "name": "Private Insurance",
            "description": "Health insurance with co-pay",
            "copay_percent": 0.20,
            "annual_cap": 500000,
            "pap_eligible": False
        },
        "thiqa": {
            "name": "Thiqa (Govt - UAE Nationals)",
            "description": "Full coverage for UAE nationals",
            "copay_percent": 0.0,
            "annual_cap": None,
            "pap_eligible": False
        }
    }
}

# PAP Schemes by region (Buy-X-Get-Y patterns)
PAP_SCHEMES = {
    "IN": [
        {"name": "Buy 1 Get 1 Free", "code": "b1g1", "paid_periods": 1, "free_periods": 1, "effective_discount": 0.50},
        {"name": "Buy 2 Get 1 Free", "code": "b2g1", "paid_periods": 2, "free_periods": 1, "effective_discount": 0.33},
        {"name": "Buy 3 Get 1 Free", "code": "b3g1", "paid_periods": 3, "free_periods": 1, "effective_discount": 0.25},
        {"name": "Cost Cap at 10 Periods", "code": "cap10", "paid_periods": 10, "free_periods": 2, "effective_discount": 0.17},
    ],
    "SG": [
        {"name": "Buy 2 Get 1 Free", "code": "b2g1", "paid_periods": 2, "free_periods": 1, "effective_discount": 0.33},
        {"name": "Buy 3 Get 1 Free", "code": "b3g1", "paid_periods": 3, "free_periods": 1, "effective_discount": 0.25},
    ],
    "AE": [
        {"name": "Buy 2 Get 1 Free", "code": "b2g1", "paid_periods": 2, "free_periods": 1, "effective_discount": 0.33},
    ]
}

# Regional Drug Pricing (ACTUAL prices, not conversions)
REGIONAL_DRUG_PRICES = {
    "semaglutide": {"IN": 25000, "SG": 450, "AE": 1200, "US": 1000},
    "wegovy": {"IN": 25000, "SG": 450, "AE": 1200, "US": 1000},
    "tirzepatide": {"IN": 35000, "SG": 550, "AE": 1500, "US": 1100},
    "zepbound": {"IN": 35000, "SG": 550, "AE": 1500, "US": 1100},
    "mounjaro": {"IN": 35000, "SG": 550, "AE": 1500, "US": 1100},
    "entresto": {"IN": 4500, "SG": 180, "AE": 450, "US": 650},
    "tenecteplase": {"IN": 80000, "SG": 2000, "AE": 5000, "US": 6000},
    "metalyse": {"IN": 80000, "SG": 2000, "AE": 5000, "US": 6000},
    "fezolinetant": {"IN": 6000, "SG": 250, "AE": 650, "US": 550},
    "veozah": {"IN": 6000, "SG": 250, "AE": 650, "US": 550},
    "romosozumab": {"IN": 18000, "SG": 600, "AE": 1600, "US": 2000},
    "evenity": {"IN": 18000, "SG": 600, "AE": 1600, "US": 2000},
}

# Default regional pricing by indication (for unknown drugs)
DEFAULT_REGIONAL_PRICES_BY_INDICATION = {
    "cardiovascular risk reduction": {"IN": 25000, "SG": 450, "AE": 1200, "US": 1000},
    "heart failure": {"IN": 4500, "SG": 180, "AE": 450, "US": 650},
    "acute ischemic stroke": {"IN": 80000, "SG": 2000, "AE": 5000, "US": 6000},
    "chronic weight management": {"IN": 35000, "SG": 550, "AE": 1500, "US": 1100},
    "type 2 diabetes": {"IN": 8000, "SG": 220, "AE": 600, "US": 800},
    "vasomotor symptoms": {"IN": 6000, "SG": 250, "AE": 650, "US": 550},
    "osteoporosis": {"IN": 18000, "SG": 600, "AE": 1600, "US": 2000},
    "default": {"IN": 15000, "SG": 400, "AE": 1000, "US": 900},
}


# Superstar Drug Metadata (Fallback for when Web Sweeper fails)
LOCAL_DRUG_METADATA = {
    "semaglutide": {
        "indication": "Cardiovascular Risk Reduction",
        "mechanism_of_action": "GLP-1 Receptor Agonist",
        "launch_date": "2021",
        "indications_available": [
            {"indication": "Cardiovascular Risk Reduction"},
            {"indication": "Chronic Weight Management"},
            {"indication": "Type 2 Diabetes"}
        ]
    },
    "wegovy": {
        "indication": "Chronic Weight Management",
        "mechanism_of_action": "GLP-1 Receptor Agonist",
        "launch_date": "2021",
        "indications_available": [
            {"indication": "Cardiovascular Risk Reduction"},
            {"indication": "Chronic Weight Management"},
            {"indication": "Type 2 Diabetes"}
        ]
    },
    "tirzepatide": {
        "indication": "Chronic Weight Management",
        "mechanism_of_action": "Dual GIP and GLP-1 Receptor Agonist",
        "launch_date": "2022",
        "indications_available": [
            {"indication": "Chronic Weight Management"},
            {"indication": "Type 2 Diabetes"}
        ]
    },
    "zepbound": {
        "indication": "Chronic Weight Management",
        "mechanism_of_action": "Dual GIP and GLP-1 Receptor Agonist",
        "launch_date": "2023",
        "indications_available": [
            {"indication": "Chronic Weight Management"},
            {"indication": "Type 2 Diabetes"}
        ]
    },
    "mounjaro": {
        "indication": "Type 2 Diabetes",
        "mechanism_of_action": "Dual GIP and GLP-1 Receptor Agonist",
        "launch_date": "2022",
        "indications_available": [
            {"indication": "Chronic Weight Management"},
            {"indication": "Type 2 Diabetes"}
        ]
    },
    "entresto": {
        "indication": "Heart Failure",
        "mechanism_of_action": "Neprilysin Inhibitor & Angiotensin Receptor Blocker",
        "launch_date": "2015",
        "indications_available": [
            {"indication": "Heart Failure"}
        ]
    },
    "tenecteplase": {
        "indication": "Acute Ischemic Stroke",
        "mechanism_of_action": "Tissue Plasminogen Activator (t-PA)",
        "launch_date": "2000",
        "indications_available": [
            {"indication": "Acute Ischemic Stroke"},
            {"indication": "Acute Myocardial Infarction"}
        ]
    },
    "metalyse": {
        "indication": "Acute Ischemic Stroke",
        "mechanism_of_action": "Tissue Plasminogen Activator (t-PA)",
        "launch_date": "2000",
        "indications_available": [
            {"indication": "Acute Ischemic Stroke"},
            {"indication": "Acute Myocardial Infarction"}
        ]
    },
    "fezolinetant": {
        "indication": "Vasomotor Symptoms",
        "mechanism_of_action": "Neurokinin 3 (NK3) Receptor Antagonist",
        "launch_date": "2023",
        "indications_available": [
            {"indication": "Vasomotor Symptoms"}
        ]
    },
    "veozah": {
        "indication": "Vasomotor Symptoms",
        "mechanism_of_action": "Neurokinin 3 (NK3) Receptor Antagonist",
        "launch_date": "2023",
        "indications_available": [
            {"indication": "Vasomotor Symptoms"}
        ]
    },
    "romosozumab": {
        "indication": "Osteoporosis",
        "mechanism_of_action": "Sclerostin Inhibitor Monoclonal Antibody",
        "launch_date": "2019",
        "indications_available": [
            {"indication": "Osteoporosis"}
        ]
    },
    "evenity": {
        "indication": "Osteoporosis",
        "mechanism_of_action": "Sclerostin Inhibitor Monoclonal Antibody",
        "launch_date": "2019",
        "indications_available": [
            {"indication": "Osteoporosis"}
        ]
    }
}

