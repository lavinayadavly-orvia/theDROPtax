# The DROP Tax — TDL

The running list. Reviewed at the end of every session: what got done, what is
still open, what got added.

**Markers** — `[ ]` not started · `[~]` partial · `[x]` done · `[!]` blocked ·
`[?]` needs a decision from Rajan

**Rules for this file**
- An item is `[x]` only when it is verified, not when it is written.
- Anything built on an assumption says so on the same line.
- Nothing is deleted when it is done — it moves to *Done*, so the record stays.
- New items get added under *Added this session* with the date, then filed.

Last reviewed: **2026-08-05**

---

## Now — the critical path

| | Item | Note |
|---|---|---|
| `[ ]` | **Wire the brain into `/analyze`** | Everything below exists, is tested, and is invisible. A user typing a drug still gets the old behaviour. This is the single blocker on seeing any of it. |
| `[ ]` | **Literature agent writes endpoints back** | Clinical endpoints in the DB are still **1 of 218**. The agent retrieves and reads; nothing persists. |
| `[ ]` | **UI** | Deferred. One page per drug, sections appearing only where the fetch plan says they apply. |

---

## Data we hold, and how far to trust it

| | Item | State |
|---|---|---|
| `[~]` | Prices | **213 of 218 are estimates.** 156 rest on an assumed once-daily dose — a drug taken three times a day costs 3×. Bands are wide enough that the cost gate survives this; individual figures are not trustworthy. |
| `[~]` | Clinical endpoints | 1 of 218. |
| `[x]` | NPPA ceiling prices | 1,012 formulations, 292 molecules, each with gazette number and date. |
| `[x]` | NLEM 2022 | 239 medicines, care levels P/S/T. 218/218 catalogue rows carry a verdict. 41 price-controlled. |
| `[x]` | Verified label facts | DailyMed, 50 innovators. Source, date and verbatim quote on every field. |
| `[ ]` | Coverage shares | IPD/OPD/HOME 85/20/0 is **invented**. Needs real payer policy sources. |
| `[ ]` | Event costs | `major_event_cost` ₹18L is **a placeholder**. PMJAY package rates are the source. |
| `[ ]` | India regulatory | No CDSCO approval dates, no Indian manufacturer counts. openFDA covers US only and must not be read as India. |
| `[ ]` | Multi-brand pricing | Inclisiran has 4 Indian brands; the workbook holds 1. |
| `[!]` | Jan Aushadhi | Blocked — the site is an SPA serving an app shell for every path, including its own API. Needs another route. |
| `[?]` | 93-row price review worksheet | Generated and waiting on Rajan. Confirmed rows never resurface. |

---

## The brain

| | Item | Note |
|---|---|---|
| `[x]` | Therapy area registry | 37 indications across CVD / CVS / Metabolic / Women's Health. Endpoints, direction, normalisation per indication. |
| `[x]` | Indications structured | 438 across 218 rows. 123 multi-indication. 331 mapped, **107 unmapped and marked** — not forced. |
| `[x]` | Orienting facts | openFDA, live, any drug: first approval, exclusivity, distinct sponsors. All fields `us_*`. |
| `[x]` | Cost gate + classifier | Money sections gated on burden as a share of income, and on whether payment recurs. |
| `[x]` | Applicability engine | Route → feasible settings → coverage by setting. |
| `[x]` | Value engine | Registry-normalised event probability. No oncology maths. |
| `[x]` | Literature agent | Europe PMC. Design, journal, authors, population, funding — each with the sentence it came from. |
| `[~]` | Appraisal engine | Built, 34 tests, **partly obsolete**. Exposure and follow-up machinery is no longer fed and should be stripped. |
| `[ ]` | Registry gaps | 107 unmapped indications. Most frequent: Post-MI ×5, diabetic nephropathy ×3, CV-risk reduction ×3, HRT ×3, BPH ×2, DUB ×2. |
| `[ ]` | Evidence criteria → code | Criteria are defined (below). Not implemented. |
| `[ ]` | Competitive & threat agent | Not started. |

---

## Decisions taken — not to be re-litigated

Recorded so they do not get rebuilt from scratch.

- **The PRD is reference, not authority.** Where it and the conversation differ, the conversation wins.
- **The unit is (drug × indication)**, never the molecule alone.
- **Cost decides whether money questions exist.** Indication decides which evidence applies. Independent axes.
- **No composite scores.** Verdicts in words, per claim and per purpose: *supports · supports with caveat · does not support · cannot be assessed*.
- **"Weak" and "unchecked" must never render the same.** A retrieval failure is ours, not the study's.
- **Orphan indications are out of scope.** The six rare-indication rows in the catalogue all behave as ordinary generics.
- **Sponsor funding is not a caveat on registrational trials** — nobody else runs them. It carries signal only where an independent alternative was possible.
- **Impact factor measures weight in the field, not validity.** Recorded under position; kept out of any validity judgement.
- **Literature is the smaller piece.** Design, journal, authors, ethnicity is the target — not patient-years.
- **Verify from source, never from memory.**

---

## Housekeeping

| | Item |
|---|---|
| `[?]` | **Rotate the leaked MongoDB credential.** It was committed in 5 files before being moved to a gitignored `.env`. Removal from the working tree does not un-leak it. |
| `[ ]` | Strip the exposure/follow-up machinery from `appraisal.py`. |
| `[ ]` | `server.py` is ~3,000 lines — routing, business logic, LLM and PDF in one file. |
| `[ ]` | Docs still describe the pre-brain platform: `ARCHITECTURE.md`, `DEMO_GUIDE.md`, `ONBOARDING_GUIDE.md`. |

---

## Done

- Full oncology removal — zero references in source, zero oncology indications in the database
- Credentials moved out of source into a gitignored `.env`
- Therapy area registry, value engine, applicability engine
- NPPA ceiling prices, NLEM 2022
- Price workbook, cross-retailer outlier detection, human review worksheet + ingest
- Verified facts from DailyMed
- Appraisal engine (calibration cases pass)
- Literature & RWE agent
- Indications structured; `(drug × indication)` established as the unit
- Orienting facts from openFDA
- Cost gate and classifier

### Bugs found and fixed
- Assumed once-daily dosing served as an exact price (156 of 161 priced drugs)
- NLEM status skipped duplicate-named rows — `update_one` where `update_many` was needed
- `portal HTN` resolved to systemic hypertension — substring alias match, would have applied blood-pressure endpoints to variceal bleed prophylaxis
- Inclisiran warned it might be "taken three times daily" — it is dosed twice a year
- Tenecteplase offered assistance and cash-flow — a single dose in an admission is bundled into the claim
- Auto-applied generic PAP halved every out-of-pocket drug
- Fabricated adverse-event rates, competitor prices, and ₹1,000,000 default prices
- Five scraping defects, each producing confident output rather than an error

---

## Added this session

*(2026-08-05 — nothing yet; new items land here before being filed above)*
