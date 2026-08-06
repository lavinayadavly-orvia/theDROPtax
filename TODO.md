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

**The standing rule** — no assumptions, no leap of faith, no US-to-India copy
paste, unfamiliar terms researched rather than confidently assumed.

Last reviewed: **2026-08-05**

---

## Now — the critical path

| | Item | Note |
|---|---|---|
| `[ ]` | **Rebuild the engines against what the instruments actually say** | A day of reading found eight things the code has wrong. See [documents/INDIA_PHARMA_MECHANICS.md](documents/INDIA_PHARMA_MECHANICS.md) §14. This is now ahead of wiring, because wiring the current logic would ship the errors. |
| `[ ]` | **Wire the brain into `/analyze`** | Everything below exists, is tested, and is invisible. A user typing a drug still gets the old behaviour. |
| `[ ]` | **Literature agent writes endpoints back** | Clinical endpoints in the DB are still **1 of 218**. |
| `[ ]` | **UI** | Deferred. One page per drug, sections appearing only where the fetch plan says they apply. |

---

## What the reading changed — rebuild list

Each of these is live in the code today and wrong.

| | Item | Correction |
|---|---|---|
| `[ ]` | Threat model | Risk is **NPPA margin capping under DPCO para 19**, which reaches *any* drug. Trigger is the gap between price-to-stockist and MRP, not a high MRP |
| `[ ]` | `price_controlled: False` on 177 of 218 | Means *no ceiling fixed yet*, not pricing freedom |
| `[ ]` | `MANY_BRANDS = 5` | An invented constant. DPCO para 6 uses ≥1% market share, but that is the **regulator's** test for setting a ceiling and needs data only NPPA holds. We are describing competition, not computing a ceiling — triangulate it instead (below) |
| `[ ]` | Brand count as competition | Rosuvastatin carries **127 brands from 105 companies**; our list holds 3. Count measures nothing — triangulate from annual reports, launch press releases, consulting and IQVIA summaries, and price spread |
| `[ ]` | Chain-margin exposure called uncomputable | PTS is not public, but **MSO contracted rate against retail price is a proxy we can compute today** — aceclofenac ₹0.53 contracted against its branded pack. Flags fat-margin molecules without needing PTS |
| `[ ]` | One price per molecule | At least three — MSO contracted, public counter, branded retail — plus MRP on the pack |
| `[ ]` | IPD "covered, bundled in the claim" | Under PM-JAY the package is **inclusive of drugs**, so the hospital absorbs it. A disincentive, not coverage |
| `[ ]` | Efficacy read against the trial's own target | India sets its own — LAI 2024 LDL-C <50 very-high-risk, ≤30 extreme |
| `[ ]` | Coverage shares 85/20/0 | NHA 2022-23: OOP **43.4%**, social security **9.9%**, private insurance **9.2%** (shares of total health spend, so a floor for medicines) |

---

## Data we hold, and how far to trust it

| | Item | State |
|---|---|---|
| `[~]` | Prices | **213 of 218 are estimates.** 156 rest on an assumed once-daily dose. Bands survive it; individual figures do not |
| `[~]` | Clinical endpoints | 1 of 218 |
| `[x]` | NPPA ceiling prices | 1,012 formulations, gazette-cited |
| `[x]` | NLEM 2022 | 239 medicines. **Schedule I of DPCO *is* NLEM**, so this is the right test for "scheduled" |
| `[x]` | CDSCO new drug approvals | 472, 452 dated, 2000–2026, with India-approved indication. 58/218 link, 39 only as combinations |
| `[x]` | CDSCO biologics permissions | 486 (125 manufacture, 361 import), 82 marked out of scope |
| `[x]` | CGHS restricted medicines | 407, of which **81 need Standing Technical Committee clearance**. Inclisiran and evolocumab both STC |
| `[x]` | MSO rate contracts | 525 rates, each with its contract window. **Supplied copy** — mso-gmsd.in nav is broken |
| `[x]` | Indian brands and makers | On all 218 rows. Counts are **lower bounds** |
| `[x]` | Verified label facts | DailyMed, 50 innovators, verbatim quotes |
| `[ ]` | Event costs | ₹18L `major_event_cost` is **a placeholder**. PM-JAY rate tables unreachable |
| `[ ]` | Multi-brand pricing | Inclisiran has 4 Indian brands; the workbook holds 1 |
| `[!]` | 9 CDSCO lists unreadable | Image tables, no text layer. Neither pypdf nor pdfplumber. Needs OCR |
| `[!]` | CGHS site | Times out on every path including its home page |
| `[!]` | PM-JAY rate tables | HTML shells at every URL. The HBP manual downloads fine |
| `[!]` | Jan Aushadhi | SPA serving an app shell for every path including its own API |
| `[?]` | 93-row price review worksheet | Generated and waiting on Rajan |

---

## The brain

| | Item | Note |
|---|---|---|
| `[x]` | Therapy area registry | 37 indications, endpoints, direction, normalisation |
| `[x]` | Indications structured | 438 across 218 rows. 331 mapped, 107 unmapped and marked |
| `[x]` | Brand resolver | 474 brands indexed. "Vymada" → Sacubitril + Valsartan. Ambiguity returned, never guessed |
| `[x]` | Orienting facts | openFDA, live, any drug. **Demoted to a pipeline signal** |
| `[x]` | India market signal | Brands, makers and CDSCO permissions. Flags where the US reading would contradict it |
| `[x]` | India approval matching | Drug-name field only, salts and units normalised, combinations counted separately |
| `[x]` | Cost gate + classifier | Gated on burden as a share of income, and on whether payment recurs |
| `[x]` | Oncology scope filter | Molecule-first, so leuprolide and denosumab survive |
| `[x]` | Applicability engine | Route → feasible settings → coverage by setting |
| `[x]` | Value engine | Registry-normalised event probability |
| `[x]` | Literature agent | Europe PMC. Design, journal, authors, population, funding — each with its sentence |
| `[x]` | Author standing | Papers-on-topic, institution kind, industry employment, ORCID coverage |
| `[~]` | Appraisal engine | 34 tests, **partly obsolete**. Exposure/follow-up machinery no longer fed |
| `[ ]` | Registry gaps | 107 unmapped indications: Post-MI ×5, diabetic nephropathy ×3, CV-risk reduction ×3, HRT ×3 |
| `[ ]` | Evidence criteria → code | Criteria defined, not implemented |
| `[ ]` | Competitive & threat agent | Not started — and the threat is NPPA, not a competitor |
| `[ ]` | CGHS price resolution | MSO rate contract, else NPPA ceiling. Both legs now held; not wired |
| `[ ]` | Trade press ingestion | Tiered (below). No ingestion for any tier |

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
**Nor at base level.** A literature that is entirely sponsor-funded does not mean independent groups declined to look. It usually means they could not afford to. Academic groups have the design expertise and lack the resources, and a tricky indication needs the expensive design — adjudicated endpoints, long follow-up, hard-to-recruit populations. The sponsor is frequently the only party able to fund it. Treating sponsor-dominance as a warning would penalise exactly the indications where sound evidence is hardest and costliest to produce.
**What survives** — one plain statement of fact, not a caveat and not a score: *this claim has not been checked by a party with a different incentive.* True, worth showing, and carrying no implication about anyone's motives or the molecule's worth.
**Left for later** — showing that statement where it applies. Not built.
**Revisit if** — nothing. Two attempts at making funding a quality signal both failed the same way: they fired where nothing was wrong.

### Impact factor measures weight in the field, not validity
**Why** — it is what everyone chases, and all three audiences act on journal tier: medical affairs on whether a KOL will respect the citation, commercial on whether it moves the narrative, market access on whether a committee will weigh it. Kept out of the validity judgement because NEJM publishes surrogate-endpoint trials — a paper can be top-tier and still not support a hard-outcome claim.
**Left for later** — sourcing it. JCR is licensed; Scimago SJR and CiteScore are free and track it closely. Undecided which we quote.
**Revisit if** — JCR access is obtained.

### Literature is the smaller piece; the target is design, journal, authors, ethnicity
**Why** — requiring patient numbers and follow-up left 2 of 25 live papers usable, because abstracts routinely omit them. The four targets are mostly metadata and reach 14–24 of 25.
**Left for later** — full text and registry records. Limitations, conflicts of interest, study arms and analysis method cannot come from an abstract, and the criteria call for all four.
**Revisit if** — full-text access becomes available. The criteria are already written for it.

### News sources are tiered, and a tier can only be promoted upward
**Why** — CDSCO's own publication lags badly. Inclisiran was cleared by a Subject Expert Committee in July 2023 and appears in none of the registers we hold: it is an siRNA so not in the r-DNA stream, and it entered by import permission so not in the new-drug lists. The trade press carried it within days. So news is not optional — it is the only thing covering the gap between a decision and its publication. But business press is noise at the level of regulatory detail, and Rajan's condition for admitting it was that the brain handles it responsibly rather than restating it.
**The rule** — Tier 1 is the CDSCO registers and establishes the fact. Tier 2 is regulatory trade press (Medical Dialogues, Pharmabiz, ET Pharma, RAPS) and establishes *"reported by X on date D"*, checkable and specific. Tier 3 is general business press (Moneycontrol, Business Standard, CNBC-TV18, The Hindu, ToI, ThePrint) and establishes **a lead only** — a reason to go looking, never a fact however plausible. A claim is promoted when a higher tier carries it, and the original citation stays as the earlier sighting.
**Left for later** — building any of it. No ingestion exists for any tier of news.
**Revisit if** — CDSCO starts publishing promptly, which would demote all three tiers to corroboration. Watch also for Tier 3 quietly being read as Tier 2: the failure mode is a business-press paraphrase of an SEC minute being rendered as the minute.

### Verify from source, never from memory
**Why** — recall was confidently wrong repeatedly on this project: an FDA approval year stated from memory and corrected by DailyMed, a ₹1 sentinel price, and a rabeprazole brand matched to zoledronic acid at ₹30 against a real ₹20,492. The failure mode is never a crash — it is clean, plausible output that happens to be false.
**Left for later** — nothing. Structural.

---

---

## Housekeeping

| | Item |
|---|---|
| `[?]` | **Rotate the leaked MongoDB credential.** Committed in 5 files before being moved to a gitignored `.env`. Removal from the working tree does not un-leak it. |
| `[ ]` | Strip the exposure/follow-up machinery from `appraisal.py`. |
| `[ ]` | `server.py` is ~3,000 lines — routing, business logic, LLM and PDF in one file. |
| `[ ]` | Docs still describe the pre-brain platform: `ARCHITECTURE.md`, `DEMO_GUIDE.md`, `ONBOARDING_GUIDE.md`. |
| `[ ]` | Expand `core/scope.py` — the CGHS STC list is heavily oncology and several molecules slipped the filter (apalutamide, avelumab, capmatinib, asciminib). |

---

## Done

- Full oncology removal — zero references in source, zero oncology indications in the database
- Credentials moved out of source into a gitignored `.env`
- Therapy area registry, value engine, applicability engine
- NPPA ceiling prices, NLEM 2022
- Price workbook, cross-retailer outlier detection, human review worksheet + ingest
- Verified facts from DailyMed
- Appraisal engine (calibration cases pass)
- Literature & RWE agent, then author standing on top of it
- Indications structured; `(drug × indication)` established as the unit
- Orienting facts from openFDA, then demoted to a pipeline signal
- Cost gate and classifier
- Brand resolver
- CDSCO new-drug and biologics registers
- CGHS restricted medicines, MSO rate contracts
- Data artefacts exported with their caveats — `artefacts/`, 3 MB
- **Read the domain from primary instruments** — [documents/INDIA_PHARMA_MECHANICS.md](documents/INDIA_PHARMA_MECHANICS.md), 14 sections

### Bugs found and fixed
- Assumed once-daily dosing served as an exact price (156 of 161 priced drugs)
- NLEM status skipped duplicate-named rows — `update_one` where `update_many` was needed
- `portal HTN` resolved to systemic hypertension — would have applied blood-pressure endpoints to variceal bleed prophylaxis
- Inclisiran warned it might be "taken three times daily" — it is dosed twice a year
- Tenecteplase offered assistance and cash-flow — a single dose in an admission is bundled
- 513 of 733 CDSCO rows undated because only `dd.mm.yyyy` was matched; the older lists write "October-1985"
- Numbered indication bullets read as approval rows — 261 phantom rows
- Substring molecule matching gave ramipril a metoprolol/atorvastatin combination
- `\bpharmaceutical\b` failing against "Pharmaceuticals" — Novartis and Apollo classified as nothing
- Units surviving normalisation — "brexpiprazole mg"
- Auto-applied generic PAP halved every out-of-pocket drug
- Fabricated adverse-event rates, competitor prices, ₹1,000,000 default prices
- Five scraping defects, each producing confident output rather than an error

### Claims I made and then corrected
- "Retail platforms discount 15–25% off MRP" — our own 443 paired observations give a **median of 1%**
- "The scraper doesn't capture the marketer" — it does, on 209 of 650 listings
- "STC = Specialist Treatment Centre" — it is the **Standing Technical Committee**, and the mechanism is cost-triggered
- "Share data is not obtainable" — not purchasable by us, but NPPA legislates on it and the ceilings we hold encode it
- "Orphan status is unsourceable" — defined in law as a condition affecting **not more than five lakh persons in India**

---

## Added this session

**2026-08-06**

- `[x]` **Market share is not a blocker.** We are not forecasting and not assigning share. NPPA needs ≥1% share because it computes a statutory ceiling; we describe a competitive picture, which is triangulated from annual reports, press releases, filings, consulting and IQVIA summaries, and observed price spread. Removed from the gap list.
- `[ ]` **Compute the chain-margin proxy.** MSO contracted rate ÷ retail price, per molecule, on data already loaded. Not the TMR figure NPPA would use, but it answers the question that matters: which molecules carry a fat distribution margin and are therefore exposed under para 19.
