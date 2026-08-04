# Product Requirements Document (PRD)

## 1. Document Control & Overview

* **Document Title:** Commercial & Clinical Intelligence Platform ("Brain Engine")
* **Product Version:** 1.0.0
* **Target Markets:** India (IN), Singapore (SG), United Arab Emirates (UAE)
* **Core Operating Principle:** Comprehension First. Complete transparency and citation over clinical judgment; local context precedence; zero-hallucination execution.

---

## 2. Product Vision & Target User Persona

### 2.1 Vision Statement
To build an AI-native commercialization and clinical intelligence engine that acts as the single source of truth for pharmaceutical assets. The platform unifies static regulatory labels, dynamic real-world evidence (RWE), localized payer coverage, out-of-pocket economics, and competitive threat landscapes into an executive dashboard.

### 2.2 User Personas
* **Brand & Commercial Leads:** Access localized market dynamics, reimbursement coverage, out-of-pocket economics, and threat scans.
* **Medical Affairs Executives:** Extract and synthesize clinical efficacy, baseline label parameters, and emerging high-impact literature.
* **Market Access & Regulatory Teams:** Track regional circular updates, payer formulary listings, and patient assistance programs (PAP).

---

## 3. System Architecture & Intelligence Engine

The platform operates on a **Graph-Augmented Agentic RAG Architecture** that connects structured user interface widgets to specialized back-end data workers.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             USER QUERY LAYER                                │
│       "Retrieve full commercial & clinical profile for Inclisiran"           │
└────────────────────────────────────────┬────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                   INTENT ROUTER & QUERY DECOMPOSER                          │
│        Routes asset query across specialized domain sub-agents              │
└───────┬──────────────────────┬──────────────────────┬───────────────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│ Clinical &   │       │ Post-Market  │       │ Market       │
│ Label Agent  │       │ Evidence     │       │ Access Agent │
│              │       │ Agent        │       │              │
└───────┬──────┘       └───────┬──────┘       └───────┬──────┘
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 DYNAMIC PHARMA KNOWLEDGE GRAPH + VECTOR STORE                │
│ (Prescribing Info | Regulatory DBs | Official Payer Lists | Literature Index)│
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 SYNTHESIS ENGINE & HALLUCINATION GUARD                      │
│     Lineage Engine + Appraisal Evaluator + Local Fallback Resolver          │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       EXECUTIVE DASHBOARD (FRONT-END)                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Domain Sub-Agents
1. **Label & Baseline Agent:** Ingests immutable ground-truth data from regulatory submissions (FDA, CDSCO, HSA, MoHAP).
2. **Literature & Evolving RWE Agent:** Periodically indexes PubMed, MEDLINE, Embase, Cochrane, and top cardiology journals (*NEJM*, *Lancet*, *JACC*, *Circulation*).
3. **Market Access Agent:** Monitors pricing databases, payer formularies, and local circulars.
4. **Competitive & Threat Agent:** Tracks generic/biosimilar entry risks, patent expiry timelines, and alternative therapeutic classes (e.g., monoclonal antibodies vs. siRNA vs. oral PCSK9 inhibitors).

---

## 4. Literature Selection & Evidence Appraisal Logic

### 4.1 Label Information Density (LID) & RWE Prioritization
To determine which data source occupies primary visual hierarchy:

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                    LABEL INFORMATION DENSITY (LID)                      │
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
              ┌───────────────────────┴───────────────────────┐
              ▼                                               ▼
     HIGH LID (Mature Label)                         LOW LID (Sparse Label)
  (Comprehensive RCTs/Endpoints)                 (Accelerated Approval, Small N)
              │                                               │
              ▼                                               ▼
   [Label Data = Primary UI]                       [RWE Data = Primary UI]
  (RWE as Supplementary Validation)              (Label as Baseline Context)
```

### 4.2 The 5-Point Study Appraisal Score
When ranking competing papers for an asset metric, the engine evaluates each candidate against five dimensions:

1. **Shape (Study Design):** Phase III RCT > Active-Comparator PSM Observational > Retrospective Cohort > Single-Center Study.
2. **Size (Sample Power):** Evaluated based on total population ($N$) and exposure time in patient-years.
3. **Form (Endpoints):** Hard Clinical Endpoints (MACE, Mortality) > Biomarker Endpoints (LDL-C %, ApoB %).
4. **Data Credibility:** Presence of propensity-score matching, audit checks, and publication in high-impact journals.
5. **Population Relevance:** Alignment with the active region toggle (ethno-geographic sample match).

---

## 5. Regionalization & Fallback Logic

The UI contains **no Global toggle**. Selection relies strictly on the regional setting (**India**, **Singapore**, **UAE**).

```
                      REGION SELECTION (e.g., UAE)
                                   │
                                   ▼
          ┌─────────────────────────────────────────────────┐
          │ TIER 1: Direct Local Cohort / Registry Exists?  │
          └────────────────────────┬────────────────────────┘
                                   │
                  ┌────────────────┴────────────────┐
                 YES                                NO
                  │                                 │
                  ▼                                 ▼
         [Display Local Study]     ┌──────────────────────────────────┐
                                   │ TIER 2: Closest Ethnic Proxy     │
                                   │         Cohort Exists?           │
                                   └────────────────┬─────────────────┘
                                                    │
                                   ┌────────────────┴────────────────┐
                                  YES                                NO
                                   │                                 │
                                   ▼                                 ▼
                     [Display Ethnic Proxy Study]    [Display Global Trial Data]
                                   │                                 │
                                   └────────────────┬────────────────┘
                                                    │
                                                    ▼
                                      [Render Regional Warning Badge]
```

### 5.1 Warning Badge UI Specifications
* **Tier 2 (Ethnic Proxy):** `⚠️ Regional Proxy Data: Direct local studies for UAE are unavailable. Displaying GCC Middle Eastern Cohort Study (N=3,200).`
* **Tier 3 (Global Fallback):** `⚠️ Global Evidence Fallback: No regional or ethnic subgroup studies identified for India. Displaying pivotal trial ORION-10 (N=1,561).`

---

## 6. Pricing, Coverage & Access Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PRICING & REIMBURSEMENT ENGINE                        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
     ┌─────────────────────────────────┼─────────────────────────────────┐
     │                                 │                                 │
     ▼                                 ▼                                 ▼
┌─────────────────────────┐  ┌─────────────────────────┐  ┌─────────────────────────┐
│   Public / Scheme       │  │   Private TPA           │  │   Out-Of-Pocket (OOP)   │
│   Coverage              │  │   Prior Auth            │  │   & Financing           │
└─────────────────────────┘  └─────────────────────────┘  └─────────────────────────┘
```

### 6.1 Data Ingestion Mechanics by Region

| Region | Primary Data Ingestion Mechanism | Source Policy | Fallback Behavior |
| :--- | :--- | :--- | :--- |
| **India (IN)** | Audited Backend Database + Live Web Update Monitoring | Manual verified database for MRP, CGHS, and PAPs; web scrapers track new circulars | If unverified, display `Manual Input Required` |
| **Singapore (SG)** | Live Direct Scraping of MOH Databases | MOH Standard Drug List (SDL), Medication Assistance Fund (MAF), and Cancer Drug List (CDL) | If missing from registry, display `Data Unavailable in Official Registry` |
| **UAE** | Live Direct Scraping of Regulatory Portals | MOHAP Registered Drug Price Lists, DOH Abu Dhabi, and DHA Dubai circulars | If missing from registry, display `Data Unavailable in Official Registry` |

### 6.2 Pricing Calculation Formula
$$	ext{Effective Patient Cost} = rac{	ext{List Price} - 	ext{Subsidy/Reimbursement Amount} - 	ext{PAP Discount}}{	ext{Dosing Frequency Factor}}$$

---

## 7. Functional UI Widget Mapping

Based on the executive dashboard layout, data fields populate as follows:

| UI Widget Element | Core Data Field | Example Data Point (Inclisiran) | Source & Lineage Attribution |
| :--- | :--- | :--- | :--- |
| **Asset Header** | Brand & Generic Name | **Inclisiran (Sybrava / Leqvio)** | CDSCO / HSA / MOHAP Approvals |
| **Asset Header** | Indication & Status | ASCVD & FH with high LDL-C despite statin | FDA 2021 Label / CDSCO Jan 2024 |
| **Cost Sidebar** | Effective Patient Cost | **₹20,000 / dose** (Full OOP post-PAP) | Audited Backend DB (India PAP) |
| **Cost Sidebar** | List Price | **₹120,000 / dose** (₹360,000 Yr 1) | Novartis List Price (India) |
| **Overview Card 1** | Cost per Dose | **₹120,000** (Payable at administration) | Commercial Directory |
| **Overview Card 2** | Primary Efficacy | **49% to 52% LDL-C Reduction** | Pooled Phase III Meta-Analysis |
| **Overview Card 3** | Safety Profile | Injection-Site Reactions (4.7%–8.2%) | Regulatory Label |
| **Directory Card** | Formulation & Strength | Subcutaneous Injection / **284 mg** | Prescribing Information |
| **Evidence Card** | Clinical Endpoints | ApoB Reduction: **~41%**; MACE HR: **Pending** | Meta-Analysis / ORION-4 |
| **Threat Card** | Active Market Threats | Stable landscape; patent protected | Patent & Biosimilar Registry Scan |

---

## 8. Non-Functional Requirements & Guardrails

1. **Zero Hallucination Guarantee:** The model is strictly prohibited from generating, estimating, or hardcoding pricing or safety figures for SG and UAE. If no exact match is found, it renders a null state (`Data Unavailable in Official Registry`).
2. **Lineage Traceability:** Every data point rendered on the dashboard must contain an interactive tooltip/citation tag linking to its exact source chunk (e.g., `[Source: MOH SG CDL Database]`, `[Source: JACC Meta-Analysis 2026]`).
3. **Data Refresh Cadence:**
   * Literature & RWE Scrapers: Weekly batch ingestion.
   * Pricing & Payer Registries: Weekly automated checks (IN, SG, UAE).
4. **Latency SLAs:** UI widget population must complete within $< 1.8 \text{ seconds}$ from cache, and $< 4.5 \text{ seconds}$ when executing real-time web verification routines.
