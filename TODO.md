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

## Decisions taken

All taken **2026-08-04/05**. A decision without its reasoning is unreadable a
month later, so each carries why it was taken, what it deliberately left for
later, and the condition that should reopen it. **Revisit if** is the important
line — if that condition arrives, the decision is stale regardless of how
settled it looks.

### The PRD is reference, not authority
**Why** — v1.4.0 carried unverified India pricing attributed to an "Audited Backend DB" we do not have, an uncited ApoB figure, a "0% EMI financing plan" with no sponsor, and an anti-estimation rule binding only SG and UAE while exempting India. Reconciling the build to it would have reintroduced fabrications already removed.
**Left for later** — updating the PRD to match the build. Maintaining two sources of truth costs more than it returns while it is a working document.
**Revisit if** — it becomes an investor or contractual artefact, or anyone else starts building from it.

### The unit is (drug × indication)
**Why** — 112 of 218 rows named several indications inside one free-text string, 438 in total. Ramipril for hypertension and ramipril for high cardiovascular risk rest on different trials and answer different questions at the same price.
**Left for later** — per-indication *pricing*. Sildenafil 20 mg for PAH and 50 mg for ED are different products at different prices; we hold no formulation-level price data.
**Revisit if** — structural, so not the decision itself. But per-indication pricing stays open and is not solved by this.

### Cost decides whether money questions exist; indication decides which evidence applies
**Why** — 139 of the 161 priced molecules sit under ₹1,000/month. At ₹7 a tablet there is no payer conversation, no assistance question and nothing to negotiate, for any indication. Showing a coverage matrix there is noise. The two axes were fused before this, which is how a ₹7 tablet got a cash-flow projection.
**Left for later** — tighter bands. They are deliberately order-of-magnitude because 156 of the prices rest on an assumed once-daily dose, so a 2–3× error must not move a drug across a boundary.
**Revisit if** — prices become verified (bands can then tighten), or a market with a different income distribution is added.

### No composite scores — verdicts in words
Per claim and per purpose: *supports · supports with caveat · does not support · cannot be assessed*.
**Why** — the scoring engine hardcoded RCT 9.5 and observational 6.0, which is the exact blanket hierarchy it existed to avoid. 8.6 against 7.62 implies a precision that regex-scraped abstracts cannot support. Validated instruments for this exist (GRADE, RoB 2, ROBINS-I) and we did not build one.
**Left for later** — implementing the verdict vocabulary in code. The criteria were defined the same day; the session ended first.
**Revisit if** — a validated instrument is adopted wholesale. That is a scoring system with standing, unlike ours.

### "Weak" and "unchecked" must never render the same
**Why** — a paper with no limitations section is a finding. A paper whose full text we could not retrieve is a gap in us. Conflating them lets our own retrieval failures masquerade as judgements about the science.
**Left for later** — nothing. Structural.

### Orphan indications are out of scope
**Why** — six catalogue rows touch a rare indication (five PAH drugs plus calcitriol). openFDA shows all six genericised with many makers: sildenafil 8 ANDAs, tadalafil 31, bosentan 5, ambrisentan 8, macitentan 12, calcitriol 11. PAH is an orphan indication; none of these drugs carry orphan economics.
**Left for later** — sourcing orphan status at all. Orphanet needs an API key, EMA publishes a file, and the FDA OOPD database returns its search form rather than results for the URL we tried.
**Revisit if** — the catalogue expands beyond CVD / Metabolic / Women's Health. The classifier still detects "generic, few makers" for any drug typed, so the trap case is not invisible.

### Sponsor funding is not a caveat on registrational trials
**Why** — a Phase III registrational programme costs hundreds of millions and exists to support an approval; nobody else runs one. The rule as first written downgraded any manufacturer-funded study, which would have fired on **every pivotal trial ever published** — a caveat that triggers on everything discriminates nothing. ALLHAT (NHLBI, 42,000 patients) marks the boundary: public money funds comparative effectiveness, not registration. Sponsor funding also *raises* durability — the dataset is audited by a regulator, the SAP is locked before unblinding, and overstating carries legal exposure.
**Left for later** — the base-level signal, which does survive: a molecule years past approval whose entire literature is still sponsor-funded means independent groups have not taken it up. Not built.
**Revisit if** — nothing invalidates it. Watch that the base-level case does not get dropped along with the per-paper one.

### Impact factor measures weight in the field, not validity
**Why** — it is what everyone chases, and all three audiences act on journal tier: medical affairs on whether a KOL will respect the citation, commercial on whether it moves the narrative, market access on whether a committee will weigh it. Kept out of the validity judgement because NEJM publishes surrogate-endpoint trials — a paper can be top-tier and still not support a hard-outcome claim.
**Left for later** — sourcing it. JCR is licensed; Scimago SJR and CiteScore are free and track it closely. Undecided which we quote.
**Revisit if** — JCR access is obtained.

### Literature is the smaller piece; the target is design, journal, authors, ethnicity
**Why** — requiring patient numbers and follow-up left 2 of 25 live papers usable, because abstracts routinely omit them. The four targets are mostly metadata and reach 14–24 of 25.
**Left for later** — full text and registry records. Limitations, conflicts of interest, study arms and analysis method cannot come from an abstract, and the criteria call for all four.
**Revisit if** — full-text access becomes available. The criteria are already written for it.

### Verify from source, never from memory
**Why** — recall was confidently wrong repeatedly on this project: an FDA approval year stated from memory and corrected by DailyMed, a ₹1 sentinel price, and a rabeprazole brand matched to zoledronic acid at ₹30 against a real ₹20,492. The failure mode is never a crash — it is clean, plausible output that happens to be false.
**Left for later** — nothing. Structural.

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
