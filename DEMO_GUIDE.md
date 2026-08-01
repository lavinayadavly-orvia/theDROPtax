# DROP Tax Commercial Suite — Demo Guide

**Live Application:** http://localhost:3000

---

## 🎯 What is DROP Tax?

A "Bloomberg for Pharma" strategic operating system for **CardioMetabolic** and
**Women's Health** market access. It shifts the conversation from "Drug Price" to
"Total Cost of Care" by translating clinical endpoints into the **downstream clinical
events avoided**.

Two principles govern the whole platform:

1. **Relevance over uniformity.** The metrics and modules shown are chosen for the drug
   and indication entered. A one-time IV thrombolytic is not given a 12-period
   cash-flow chart or a patient-assistance programme.
2. **No hallucination.** If a value cannot be resolved from a real source, the platform
   shows *"Data unavailable — manual input required"* and flags it. It never invents a
   number to fill a gap.

---

## 🧭 Therapy Areas & Endpoints

Endpoints are defined **per indication** in the Therapy Area Registry
(`backend/core/therapy_areas.py`, mirrored in `frontend/src/lib/therapyAreas.js`) —
the single place to extend the platform with a new indication.

| Therapy Area | Indications | Primary endpoint (drives the model) |
| :--- | :--- | :--- |
| **CVD** | Cardiovascular Risk Reduction | 3-pt MACE Risk Reduction (HR) |
| | Heart Failure | CV-death / HF-hospitalisation (HR) |
| | Hypercholesterolemia / Dyslipidemia | LDL-C Reduction (%) |
| | Hypertension | Systolic BP Reduction (mmHg) |
| **CVS** | Acute Ischemic Stroke | Functional Independence, mRS 0–2 (%) |
| | Acute Myocardial Infarction | Reperfusion / TIMI-3 Flow (%) |
| **Metabolic** | Chronic Weight Management (Obesity) | Mean Body-Weight Reduction (%) |
| | Type 2 Diabetes | HbA1c Reduction (%) |
| **Women's Health** | Vasomotor Symptoms (Menopause) | VMS Frequency Reduction (%) |
| | Osteoporosis | Vertebral-Fracture Risk Reduction (HR) |
| | Endometriosis | Dysmenorrhoea Responder Rate (%) |
| | Uterine Fibroids | Menstrual Blood-Loss Responder (%) |
| | Heavy Menstrual Bleeding (Menorrhagia) | MBL Reduction, alkaline-hematin (%) |

Each endpoint carries a **benefit direction** — LDL-C, HbA1c and MBL are *lower-better*;
functional independence and responder rates are *higher-better* — so the engine
normalises any endpoint correctly into a downstream event probability.

---

## 📊 Demo Walkthrough

### 1. **The White Room** (Entry Point)
- **Design**: Stark white, minimalist interface
- **Function**: High-end drug search with auto-suggest
- **Seeded drugs**: Semaglutide, Tirzepatide, Sacubitril/Valsartan (Vymada),
  Tenecteplase, Fezolinetant, Romosozumab
- **Action**: Type any drug name to begin. Multi-indication drugs prompt for the
  indication, because the indication determines which endpoints apply.

### 2. **Executive Dashboard** (Command Center)

```
Total downstream cost = (Event Probability × Event Cost)
                      + (Productivity Loss × Monthly Income)
                      + (Adverse-Event Management Cost)
```

`Event Probability` is derived from the indication's **primary endpoint** via the
registry — there is no formula tied to any single therapy area.

**Example (Sacubitril/Valsartan, Heart Failure, India):**
- Primary endpoint: CV-death / HF-hospitalisation **HR 0.80** (PARADIGM-HF)
- → 20% relative risk reduction → event probability ≈ 0.20
- Event cost = regional cost of a heart-failure hospitalisation
- Adverse-event cost derived from the comparator's serious-AE rate

If the primary endpoint is missing, the dashboard shows **"Data unavailable"** and the
recommendation reads `INSUFFICIENT_DATA` — it does not guess.

### 3. **Site-of-Care Coverage** (the differentiator)

The **same drug** prices and reimburses differently depending on where it is given:

| Setting | Coverage (India) | Price basis |
| :--- | :--- | :--- |
| **IPD** (admitted / day-care) | Covered — bundled in the hospitalisation claim | Institutional / tender |
| **OPD** (follow-up visit) | Conditional — only if on the payer's day-care list | Institutional or retail |
| **HOME** (self-administered) | Excluded — self-pay | Retail MRP (higher) |

The **coverage gap** between a covered setting and the patient's real-world setting is
what determines whether financial assistance is recommended at all.

### 4. **Applicability** — what the platform decides for you

| Drug | Model | Cash flow | Adherence | PAP |
| :--- | :--- | :--- | :--- | :--- |
| **Tenecteplase** (IV bolus, stroke) | Acute single dose, IPD-only | ❌ | ❌ | ❌ — covered inpatient |
| **Vymada** (oral, heart failure) | Chronic, home | ✅ | ✅ | ❌ — low OOP burden |
| **High-cost SC specialty** (home) | Chronic, home | ✅ | ✅ | ✅ — coverage gap |

Modules mount from `applicability.modules`; irrelevant tabs are hidden rather than
shown with meaningless numbers.

### 5. **Deal Architect** (only when relevant)
Payer segment routing and patient-assistance modelling — surfaced only when a genuine
out-of-pocket coverage gap exists at the expected site of care.

### 6. **Compare My TPP**
Head-to-head benchmarking. The clinical-endpoint input fields are **generated from the
registry** for the selected indication, so a diabetes asset is compared on HbA1c and a
stroke asset on functional independence.

### 7. **Executive Export**
Boardroom-ready value dossier (PDF) incorporating the live regional analysis.

---

## 🔍 Data Quality & Issue Reporting

Every analysis returns a `data_quality` envelope:

```json
{ "status": "complete | partial | unavailable",
  "missing_fields": ["..."],
  "issues": [{ "field": "...", "severity": "warning", "message": "..." }] }
```

The **Data Quality panel** lists exactly what could not be resolved and why, so a
missing value is never mistaken for a computed one. Unknown route, coverage, or
chronicity resolves to `unknown` with a conservative (not-covered) default and an
explicit issue — never a favourable assumption.

---

## 🌍 Regional Support

| Region | Regulator | Currency | Outpatient coverage |
| :--- | :--- | :--- | :--- |
| India (IN) | CDSCO | ₹ INR | Strict — OPD conditional, home excluded |
| Singapore (SG) | HSA | S$ SGD | Broader — MediShield / CHAS support |
| UAE (AE) | DOH / MOHAP | AED | Broader — plan formulary with co-pay |

---

## ✅ Summary

DROP Tax reframes market access from list-price comparison to **total cost of care**,
while behaving like a domain expert: it structures the request around the therapy area,
shows only what applies to the asset in front of it, prices by site of care, and is
explicit about what it does not know.
