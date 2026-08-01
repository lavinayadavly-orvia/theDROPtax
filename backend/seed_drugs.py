"""
Seed the canonical CardioMetabolic & Women's Health drug set.

Clinical data uses the generic, therapy-area-driven model:
  primary_endpoint_value / _key / _label / _unit   (the endpoint that drives the value engine)
  hazard_ratio, secondary_endpoints[]
  drug_severe_ae_rate / competitor_severe_ae_rate   (serious adverse-event rates)
  route + treatment_model                           (feed the applicability "Brain")

Credentials come from the environment — never hard-code them.
"""
import os
import asyncio
import motor.motor_asyncio

MONGO_URL = os.environ.get("MONGO_URL")
DB_NAME = os.environ.get("DB_NAME", "droptax")

DRUGS = [
    {
        "id": "semaglutide",
        "name": "Semaglutide",
        "category": "CVD",
        "indication": "Cardiovascular Risk Reduction",
        "mechanism_of_action": "GLP-1 Receptor Agonist",
        "route": "sc_injection",
        "treatment_model": "chronic_ongoing",
        "launch_date": "2021-06",
        "global_price_inr": 25000,
        "has_multiple_indications": True,
        "indications_available": [
            {"indication": "Cardiovascular Risk Reduction"},
            {"indication": "Chronic Weight Management"},
            {"indication": "Type 2 Diabetes"}
        ],
        # Primary endpoint: 3-pt MACE hazard ratio (SELECT trial, HR 0.80 = 20% RRR)
        "primary_endpoint_key": "mace_hr",
        "primary_endpoint_label": "3-pt MACE Risk Reduction",
        "primary_endpoint_unit": "HR",
        "primary_endpoint_value": 0.80,
        "primary_endpoint_method": "SELECT Trial (NCT03574597)",
        "primary_endpoint_is_estimated": False,
        "hazard_ratio": 0.80,
        "secondary_endpoints": [
            {"key": "cv_mortality_hr", "label": "CV Mortality HR", "unit": "HR", "value": 0.85},
        ],
        "clinical_confidence": 0.95,
        "competitor_name": "Standard of Care (Statins + Diet)",
        "competitor_price_inr": 3000,
        "drug_severe_ae_rate": 0.12,
        "competitor_severe_ae_rate": 0.08,
        "drug_adverse_events": ["Nausea", "Diarrhea", "Vomiting", "Constipation", "Abdominal Pain"],
        "competitor_adverse_events": ["Muscle Pain", "Headache", "Fatigue", "Liver Enzyme Elevation"],
        "epidemiology": {"addressable_population": 850000, "sources": "WHO Global Health Observatory 2024"},
        "data_sources": {
            "clinical": "SELECT Trial (NCT03574597) published in NEJM",
            "competitor": "Cardiovascular outcomes registries",
            "toxicity": "Wegovy FDA prescribing information",
            "clinical_tier": "tier_1", "competitor_tier": "tier_2", "toxicity_tier": "tier_1"
        },
        "data_quality": {"status": "complete", "missing_fields": [], "issues": []},
        "regional_availability": {
            "regional_status": "launched", "local_regulator": "CDSCO", "local_approval_date": "2023-08",
            "availability_text": "Commercially Available (Audited)", "availability_color": "green",
            "notes": "Available via Novo Nordisk India distribution network.", "is_available": True
        },
        "regulatory_status": "CDSCO Approved",
    },
    {
        "id": "tirzepatide",
        "name": "Tirzepatide",
        "category": "Metabolic",
        "indication": "Chronic Weight Management",
        "mechanism_of_action": "Dual GIP and GLP-1 Receptor Agonist",
        "route": "sc_injection",
        "treatment_model": "chronic_ongoing",
        "launch_date": "2022-05",
        "global_price_inr": 35000,
        "has_multiple_indications": True,
        "indications_available": [
            {"indication": "Chronic Weight Management"},
            {"indication": "Type 2 Diabetes"}
        ],
        # Primary endpoint: mean body-weight reduction % (SURMOUNT-1 ≈ 20.9%)
        "primary_endpoint_key": "weight_reduction",
        "primary_endpoint_label": "Mean Body-Weight Reduction",
        "primary_endpoint_unit": "%",
        "primary_endpoint_value": 20.9,
        "primary_endpoint_method": "SURMOUNT-1 Trial (NCT04184622)",
        "primary_endpoint_is_estimated": False,
        "hazard_ratio": None,
        "secondary_endpoints": [
            {"key": "responder_10", "label": "≥10% Weight-loss Responders", "unit": "%", "value": 83.0},
        ],
        "clinical_confidence": 0.98,
        "competitor_name": "Semaglutide (Wegovy)",
        "competitor_price_inr": 25000,
        "drug_severe_ae_rate": 0.15,
        "competitor_severe_ae_rate": 0.12,
        "drug_adverse_events": ["Nausea", "Diarrhea", "Decreased Appetite", "Vomiting", "Constipation"],
        "competitor_adverse_events": ["Nausea", "Diarrhea", "Vomiting", "Constipation"],
        "epidemiology": {"addressable_population": 1200000, "sources": "ICMR Metabolic Disease Survey 2025"},
        "data_sources": {
            "clinical": "SURMOUNT-1 Trial published in NEJM",
            "competitor": "Indirect treatment comparison (ITC) analysis",
            "toxicity": "Zepbound FDA prescribing information",
            "clinical_tier": "tier_1", "competitor_tier": "tier_2", "toxicity_tier": "tier_1"
        },
        "data_quality": {"status": "complete", "missing_fields": [], "issues": []},
        "regional_availability": {
            "regional_status": "limited", "local_regulator": "CDSCO", "local_approval_date": "2024-10",
            "availability_text": "Limited Availability (Import Only)", "availability_color": "amber",
            "notes": "CDSCO approved. Available primarily via specialized importer network.", "is_available": True
        },
        "regulatory_status": "CDSCO Approved",
    },
    {
        "id": "entresto",
        "name": "Sacubitril/Valsartan",
        "category": "CVD",
        "indication": "Heart Failure",
        "mechanism_of_action": "Neprilysin Inhibitor & Angiotensin Receptor Blocker",
        "route": "oral",
        "treatment_model": "chronic_ongoing",
        "launch_date": "2015-07",
        "global_price_inr": 4500,
        "has_multiple_indications": False,
        "indications_available": [{"indication": "Heart Failure"}],
        # Primary endpoint: CV-death/HF-hospitalisation HR (PARADIGM-HF, HR 0.80)
        "primary_endpoint_key": "hf_event_hr",
        "primary_endpoint_label": "CV-death / HF-hospitalisation HR",
        "primary_endpoint_unit": "HR",
        "primary_endpoint_value": 0.80,
        "primary_endpoint_method": "PARADIGM-HF Trial (NCT01035255)",
        "primary_endpoint_is_estimated": False,
        "hazard_ratio": 0.80,
        "secondary_endpoints": [
            {"key": "acm_hr", "label": "All-cause Mortality HR", "unit": "HR", "value": 0.84},
        ],
        "clinical_confidence": 0.96,
        "competitor_name": "Enalapril (Enalapril maleate)",
        "competitor_price_inr": 300,
        "drug_severe_ae_rate": 0.09,
        "competitor_severe_ae_rate": 0.11,
        "drug_adverse_events": ["Hypotension", "Hyperkalemia", "Renal Impairment", "Cough", "Angioedema"],
        "competitor_adverse_events": ["Cough", "Hypotension", "Hyperkalemia", "Renal dysfunction", "Angioedema"],
        "epidemiology": {"addressable_population": 2400000, "sources": "National Heart Failure Registry 2024"},
        "data_sources": {
            "clinical": "PARADIGM-HF Trial published in NEJM",
            "competitor": "Standard ACE inhibitor clinical literature",
            "toxicity": "Entresto prescribing information",
            "clinical_tier": "tier_1", "competitor_tier": "tier_1", "toxicity_tier": "tier_1"
        },
        "data_quality": {"status": "complete", "missing_fields": [], "issues": []},
        "regional_availability": {
            "regional_status": "launched", "local_regulator": "CDSCO", "local_approval_date": "2016-02",
            "availability_text": "Commercially Available (Audited)", "availability_color": "green",
            "notes": "Marketed as Vymada/Entresto. Widely distributed by Novartis India.", "is_available": True
        },
        "regulatory_status": "CDSCO Approved",
    },
    {
        "id": "tenecteplase",
        "name": "Tenecteplase",
        "category": "CVS",
        "indication": "Acute Ischemic Stroke",
        "mechanism_of_action": "Tissue Plasminogen Activator (t-PA)",
        "route": "iv_bolus",
        "treatment_model": "acute_single_dose",
        "launch_date": "2000-06",
        "global_price_inr": 80000,
        "has_multiple_indications": True,
        "indications_available": [
            {"indication": "Acute Ischemic Stroke"},
            {"indication": "Acute Myocardial Infarction"}
        ],
        # Primary endpoint: functional independence mRS 0-2 % (EXTEND-IA TNK ≈ 65%)
        "primary_endpoint_key": "functional_independence",
        "primary_endpoint_label": "Functional Independence (mRS 0–2)",
        "primary_endpoint_unit": "%",
        "primary_endpoint_value": 65.0,
        "primary_endpoint_method": "EXTEND-IA TNK Trial (NCT02388061)",
        "primary_endpoint_is_estimated": False,
        "hazard_ratio": None,
        "secondary_endpoints": [
            {"key": "recanalization", "label": "Recanalisation Rate", "unit": "%", "value": 22.0},
        ],
        "clinical_confidence": 0.92,
        "competitor_name": "Alteplase (Activase)",
        "competitor_price_inr": 65000,
        "drug_severe_ae_rate": 0.05,
        "competitor_severe_ae_rate": 0.08,
        "drug_adverse_events": ["Minor Bleeding", "Symptomatic Intracerebral Hemorrhage", "Hematoma", "Hypotension"],
        "competitor_adverse_events": ["Symptomatic Intracerebral Hemorrhage", "Major Bleeding", "Orolingual Angioedema"],
        "epidemiology": {"addressable_population": 450000, "sources": "Indian Stroke Association Consensus 2025"},
        "data_sources": {
            "clinical": "EXTEND-IA TNK Trial published in NEJM",
            "competitor": "Alteplase stroke registry data",
            "toxicity": "Metalyse prescribing guidelines",
            "clinical_tier": "tier_1", "competitor_tier": "tier_1", "toxicity_tier": "tier_1"
        },
        "data_quality": {"status": "complete", "missing_fields": [], "issues": []},
        "regional_availability": {
            "regional_status": "launched", "local_regulator": "CDSCO", "local_approval_date": "2021-12",
            "availability_text": "Commercially Available (Audited)", "availability_color": "green",
            "notes": "Marketed as Metalyse/Elaxim. Distributed widely to stroke centers.", "is_available": True
        },
        "regulatory_status": "CDSCO Approved",
    },
    {
        "id": "fezolinetant",
        "name": "Fezolinetant",
        "category": "Women's Health",
        "indication": "Vasomotor Symptoms",
        "mechanism_of_action": "Neurokinin 3 (NK3) Receptor Antagonist",
        "route": "oral",
        "treatment_model": "chronic_ongoing",
        "launch_date": "2023-05",
        "global_price_inr": 6000,
        "has_multiple_indications": False,
        "indications_available": [{"indication": "Vasomotor Symptoms"}],
        # Primary endpoint: VMS frequency reduction % (SKYLIGHT-1 ≈ 60%)
        "primary_endpoint_key": "vms_frequency",
        "primary_endpoint_label": "VMS Frequency Reduction",
        "primary_endpoint_unit": "%",
        "primary_endpoint_value": 60.0,
        "primary_endpoint_method": "SKYLIGHT-1 Trial (NCT04003155)",
        "primary_endpoint_is_estimated": False,
        "hazard_ratio": None,
        "secondary_endpoints": [
            {"key": "vms_severity", "label": "VMS Severity Reduction", "unit": "%", "value": 55.0},
        ],
        "clinical_confidence": 0.94,
        "competitor_name": "Hormone Replacement Therapy (Premarin)",
        "competitor_price_inr": 2500,
        "drug_severe_ae_rate": 0.04,
        "competitor_severe_ae_rate": 0.08,
        "drug_adverse_events": ["Abdominal Pain", "Diarrhea", "Insomnia", "Back Pain", "Hepatic Transaminase Elevation"],
        "competitor_adverse_events": ["Breast Tenderness", "Vaginal Bleeding", "Fluid Retention", "Headache", "Mood Swings"],
        "epidemiology": {"addressable_population": 6500000, "sources": "FOGSI (India) 2024"},
        "data_sources": {
            "clinical": "SKYLIGHT-1 Trial published in The Lancet",
            "competitor": "HRT efficacy meta-analyses",
            "toxicity": "Veozah FDA prescribing information",
            "clinical_tier": "tier_1", "competitor_tier": "tier_2", "toxicity_tier": "tier_1"
        },
        "data_quality": {"status": "complete", "missing_fields": [], "issues": []},
        "regional_availability": {
            "regional_status": "not_launched", "local_regulator": "CDSCO", "local_approval_date": None,
            "availability_text": "Pending Registration", "availability_color": "red",
            "notes": "Astellas is preparing CDSCO submission. Not commercially available yet.", "is_available": False
        },
        "regulatory_status": "CDSCO Pending",
    },
    {
        "id": "romosozumab",
        "name": "Romosozumab",
        "category": "Women's Health",
        "indication": "Osteoporosis",
        "mechanism_of_action": "Sclerostin Inhibitor Monoclonal Antibody",
        "route": "sc_injection",
        "treatment_model": "fixed_course",
        "launch_date": "2019-04",
        "global_price_inr": 18000,
        "has_multiple_indications": False,
        "indications_available": [{"indication": "Osteoporosis"}],
        # Primary endpoint: vertebral-fracture RRR HR (ARCH ≈ 0.52)
        "primary_endpoint_key": "vertebral_fracture_hr",
        "primary_endpoint_label": "Vertebral-Fracture Risk Reduction",
        "primary_endpoint_unit": "HR",
        "primary_endpoint_value": 0.52,
        "primary_endpoint_method": "ARCH Trial (NCT01631214)",
        "primary_endpoint_is_estimated": False,
        "hazard_ratio": 0.52,
        "secondary_endpoints": [
            {"key": "bmd_spine", "label": "BMD Change (Spine)", "unit": "%", "value": 13.7},
        ],
        "clinical_confidence": 0.95,
        "competitor_name": "Alendronate (Fosamax)",
        "competitor_price_inr": 800,
        "drug_severe_ae_rate": 0.07,
        "competitor_severe_ae_rate": 0.05,
        "drug_adverse_events": ["Joint Pain", "Headache", "Muscle Spasms", "Injection Site Reaction", "Hypocalcemia"],
        "competitor_adverse_events": ["Acid Reflux", "Esophageal Irritation", "Abdominal Pain", "Bone/Muscle Pain"],
        "epidemiology": {"addressable_population": 1800000, "sources": "IOF Osteoporosis Report India 2024"},
        "data_sources": {
            "clinical": "ARCH Trial published in NEJM",
            "competitor": "Standard bisphosphonate treatment cohorts",
            "toxicity": "Evenity FDA prescribing information",
            "clinical_tier": "tier_1", "competitor_tier": "tier_1", "toxicity_tier": "tier_1"
        },
        "data_quality": {"status": "complete", "missing_fields": [], "issues": []},
        "regional_availability": {
            "regional_status": "launched", "local_regulator": "CDSCO", "local_approval_date": "2021-06",
            "availability_text": "Commercially Available (Audited)", "availability_color": "green",
            "notes": "Marketed as Evenity. Distributed via Amgen India network.", "is_available": True
        },
        "regulatory_status": "CDSCO Approved",
    },
]


async def seed():
    if not MONGO_URL:
        raise SystemExit("MONGO_URL is not set — export it before seeding (do not hard-code credentials).")
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    await db.drugs.delete_many({})
    result = await db.drugs.insert_many(DRUGS)
    print(f"✅ Inserted {len(result.inserted_ids)} CardioMetabolic & Women's Health drugs into '{DB_NAME}'.drugs")

    count = await db.drugs.count_documents({})
    print(f"✅ Verified: {count} drugs in MongoDB")
    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
