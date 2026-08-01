# theDROPtax

A market-access intelligence platform for **CardioMetabolic** and **Women's Health**
therapies. It reframes the payer conversation from *drug price* to *total cost of care*
by translating clinical endpoints into the downstream clinical events they avoid.

Two principles govern the platform:

1. **Relevance over uniformity.** The metrics and modules shown are chosen for the drug
   and indication entered. A one-time IV thrombolytic is not given a 12-period cash-flow
   chart or a patient-assistance programme.
2. **No hallucination.** If a value cannot be resolved from a real source it is reported
   as *"Data unavailable — manual input required"* and flagged. It is never invented.

---

## Therapy areas

Endpoints are defined **per indication** in the Therapy Area Registry
([`backend/core/therapy_areas.py`](backend/core/therapy_areas.py), mirrored in
[`frontend/src/lib/therapyAreas.js`](frontend/src/lib/therapyAreas.js)) — the single
place to extend the platform.

| Area | Indications | Primary endpoint |
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

Each endpoint carries a benefit **direction**, so lower-better measures (LDL-C, HbA1c,
MBL) and higher-better ones (responder rates, mRS) both normalise correctly into a
downstream event probability.

## The value engine

```
Total downstream cost = (Event Probability × Event Cost)
                      + (Productivity Loss × Monthly Income)
                      + (Adverse-Event Management Cost)
```

`Event Probability` is derived from the indication's primary endpoint via the registry —
no formula is hard-wired to any one therapy area.

## Site-of-care coverage

The **same drug** prices and reimburses differently depending on where it is given:

| Setting | Coverage (India) | Price basis |
| :--- | :--- | :--- |
| **IPD** (admitted / day-care) | Covered — bundled in the hospitalisation claim | Institutional / tender |
| **OPD** (follow-up visit) | Conditional — payer day-care list dependent | Institutional or retail |
| **HOME** (self-administered) | Excluded — self-pay | Retail MRP (higher) |

The resulting **coverage gap** — combined with real Patient Support Programme data — is
what determines whether financial assistance is recommended at all.

---

## Architecture

```
backend/    FastAPI service — value engine, applicability resolver, registry
frontend/   React SPA (craco) — dashboard, TPP benchmarker, war room
documents/  Deployment and onboarding notes
```

## Running locally

**1. Configure the backend** (never commit credentials — `.env` is gitignored):

```bash
printf 'MONGO_URL=<your-connection-string>\nDB_NAME=droptax\n' > backend/.env
```

**2. Load the data** from the drug workbook:

```bash
cd backend && python3 seed_regions.py && python3 seed_from_workbook.py /path/to/workbook.xlsx
```

**3. Start both processes:**

```bash
cd backend && python3 -m uvicorn server:app --port 8000 --reload
cd frontend && npm start
```

The app runs at **http://localhost:3000**.

## Tests

```bash
cd backend && python3 -m pytest tests/
```

## Deployment

The frontend deploys to Cloudflare Pages; `_worker.js` proxies `/api/*` to the backend.
Set **`BACKEND_URL`** in Cloudflare Pages → Settings → Environment variables — the proxy
returns a 503 with a clear message if it is not configured.
