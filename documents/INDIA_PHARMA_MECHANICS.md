# How the Indian pharmaceutical market actually works

Read from primary instruments on 2026-08-05, because the platform's model of
this market was wrong in ways that produced working code and false answers. The
worst of them: Drugs@FDA reported tenecteplase as exclusive to Genentech, so the
classifier printed *"No generic competition — the originator sets the price"* for
a molecule Emcure sells here as Elaxim.

Everything below is sourced. Where a figure comes from secondary reporting it
says so, and where the source itself is stale it says that too.

---

## 1. The money flow

Manufacturer → C&F agent → stockist → distributor → retailer → patient.

Roughly **3,000 C&F agents, 65,000 stockists and 800,000 retail pharmacies**
(secondary; trade estimates). Price has a different name at each step, and the
Order treats them as legally distinct:

| Term | Definition | Source |
|---|---|---|
| **PTS** — price to stockist | Price at the **first point of sale**, manufacturer to stockist | TMR order 2019 |
| **PTR** — price to retailer | *"the price of a drug at which it is sold to a retailer which includes duties and does not include local taxes"* | DPCO 2013, definitions |
| **Retail price** | Fixed by Government for a new drug under para 5 | DPCO 2013 |
| **MRP** | *"the ceiling price or the retail price plus local taxes and duties as applicable, at which the drug shall be sold to the ultimate consumer"* | DPCO 2013, definitions |

**MRP is a ceiling, not a price.** NPPA: *"The printed MRP plus local taxes is
the maximum payable amount. However, a medicine can be sold below this price."*
So a scraped retail price and an MRP are different numbers and must not be
compared.

How much discounting actually happens is a separate question, and our own data
answers it: across **443 listings where both were captured, the median discount
off MRP is 1%** (range 0–100%). An earlier draft of this document said 15–25%
— that figure was unsourced and is wrong for our sample.

A retailer breaking a pack may charge **pro-rata plus 5%** on loose quantity.

---

## 2. Two price-control routes, on two different bases

### Scheduled formulations — DPCO 2013 para 4

The ceiling is built from **market share**, not from MRP:

> Average Price to Retailer P(s) = (sum of prices to retailer of all brands and
> generic versions **having market share ≥ 1%** of total market turnover on
> moving annual turnover) ÷ (number of such brands)

Then **para 5**: retail price of a new drug is fixed *"by adding sixteen percent
margin to retailer on the price to retailer."*

```
Ceiling  = mean PTR across brands with ≥1% share
Retail   = PTR × 1.16
MRP      = retail + local taxes
```

The 16% is consistent across both orders — para 19 of DPCO 1995, para 5 of
DPCO 2013.

**Annual escalation:** scheduled formulations may be revised **once a year in
April, by WPI**, without prior approval (para 16).

### Non-scheduled — DPCO 2013 para 20, and para 19

Para 20 caps the MRP increase at **ten percent in any twelve months**; excess
must be rolled back and the overcharge deposited **with interest**.

Para 19 is the one that matters commercially:

> **"Fixation of ceiling price of a drug under certain circumstances.** —
> Notwithstanding anything contained in this order, the Government may, in case
> of extra-ordinary circumstances, if it considers necessary so to do in public
> interest, fix the ceiling price or retail price of **any Drug** for such
> period as it may deem fit."

Any drug. Scheduled or not. Enforcement sits under the **Essential Commodities
Act 1955**, and contravention carries **three months to seven years
imprisonment** — which is why this is not a theoretical power.

---

## 3. Trade Margin Rationalisation — the live instrument

NPPA invoked para 19 on **26 February 2019** against **42 non-scheduled
anti-cancer drugs**, and did not fix a ceiling. It capped the **margin**:

```
Retail price = PTS × (1 + TM),   TM ≤ 30%
```

PTS frozen at June 2018. Result: MRP of **526 brands** cut by roughly 50%,
about **₹984 crore** a year. Reused on oxygen concentrators at a 70% cap during
COVID, so the instrument is general rather than an oncology one-off.

**PTS sits upstream of PTR**, so TMR caps a wider span of the chain than the
scheduled route. The manufacturer keeps what it makes up to PTS; what is capped
is everything the distribution chain adds after.

### Why the margin was the target

Retailer margin on branded medicines runs **25–30%**. On the *same company's*
branded-generic version of the same molecule it has been measured at
**201–1016%** (peer-reviewed, PubMed 21572645). Unbranded generics reportedly
reach 50%+ at retail.

That gap is the engine of the market. A chemist earns several times more
dispensing a branded generic than a scheduled brand, which is where
counter-level substitution power comes from.

**So the exposure for an expensive drug is not its MRP — it is a large visible
gap between PTS and MRP.** A costly drug with a thin chain margin is safer than
a cheaper one with a fat margin.

---

## 4. Public procurement is not insurance

**PM-JAY** packages are all-inclusive. From the HBP 2.2 manual:

> *"All the packages are inclusive of everything including drugs, diagnostics,
> consultations, procedures, treatment modalities."*

So under PM-JAY an expensive drug generates **no separate revenue** — it is a
cost the hospital absorbs inside a fixed package rate. That is a structural
disincentive to use it, and it is not "coverage" in the insurance sense at all.

1,669 procedures (1,080 surgical, 588 medical). ₹5 lakh per family per year.
Unspecified packages are capped at **₹1 lakh** within that limit. HBP 2.2 raised
some rates 20–400%; ICU-with-ventilator by 100%.

**CGHS** runs a separate formulary and rate list, with medicines issued through
**empanelled local chemists** — a distinct channel again, for central government
employees. The formulary and rate documents could not be retrieved: cghs.gov.in
timed out on every path tried, including its own home page.

The PM-JAY **rate table** is likewise unretrieved. The HBP 2.2 *manual* above
downloads fine; the package-and-rate files on nha.gov.in and pmjay.gov.in return
HTML shells or time out. The structural rule — packages are inclusive of drugs —
is the part that governs the model, and that is sourced. The per-package
dispute is that ₹18L `major_event_cost` still has nothing behind it.

---

## 5. Clinical practice does not follow Western guidelines

**Lipid Association of India, Consensus Statement IV (Feb 2024)** sets targets
below ESC/EAS and ACC/AHA, explicitly because ASCVD in Indians is earlier and
more aggressive: **<50 mg/dL** LDL-C for very high risk, **≤30 mg/dL** for
extreme risk, and **10–15 mg/dL** where events occur despite <30.

The phenotype behind it: South Asians carry more visceral and hepatic fat at
lower BMI — the "thin-fat" pattern — with earlier onset of both type 2 diabetes
and ASCVD, at BMI thresholds where Western risk models do not flag them.
ICMR-INDIAB found significant metabolic risk well below standard BMI cut-offs.

So an efficacy claim for a lipid or metabolic drug has to be read against the
Indian target, not the trial's own. A drug that reaches an ESC goal may not
reach the LAI one.

---

## 6. Regulatory, beyond price

**NDCT Rules 2019** — *"orphan drug means a drug intended to treat a condition
which affects not more than five lakh persons in India."* A prevalence
threshold in law, not a designation registry, so orphan status here is
determinable from epidemiology.

Phase IV is a standing condition of approval — the applicant undertakes in
writing to conduct one — relaxable for life-threatening disease, unmet need, or
rare disease. Local trial waiver runs under Chapter X for drugs approved in
specified countries.

**UCPMP 2024**, notified 12 March 2024 and mandatory: no gifts, monetary
benefits or hospitality to healthcare professionals or their families;
self-declared adherence; disclosure of CME and conference spend; random and
risk-based audits. Enforcement is public — the Apex Committee order against
AbbVie Healthcare India, 23 December 2024, is on the DoP site. Conduct is
therefore a checkable competitive signal, not a rumour.

**PvPI**, run by the Indian Pharmacopoeia Commission since 2011, with **567 ADR
monitoring centres**. India is the 9th largest contributor of individual case
safety reports to the WHO database. So Indian safety signal exists and has a
national collection route.

**CTRI** — registration mandatory since 2009, prospective-only since April
2018. Cardiology and endocrinology are among the most registered areas. One
documented caveat: CDSCO and CTRI records **do not always match** (Frontiers in
Medicine, 2024), so neither is a complete account of what was studied.

---

## 7. The system patients actually pay in

National Health Accounts 2022-23:

| Share of total health expenditure | 2013-14 | 2022-23 |
|---|---|---|
| Out of pocket | 64.2% | **43.4%** |
| Social security (PM-JAY, CGHS, etc.) | 6.0% | **9.9%** |
| Private health insurance | 3.4% | **9.2%** |

Government health expenditure is **1.43% of GDP**. These are shares of *total
health* expenditure, not of medicines specifically — drugs typically sit at a
higher out-of-pocket share than the total, so 43.4% is a floor for our purposes,
not the medicine figure.

This replaces the invented IPD/OPD/HOME coverage shares of 85/20/0.

---

## 8. Schedule I is NLEM, by reference

DPCO 2013's First Schedule *is* the National List of Essential Medicines,
incorporated by reference (the 2016 consolidation carries NLEM 2015; NLEM 2022
was notified in by amendment). Symbols P, S and T in the Schedule denote
essentiality at primary, secondary and tertiary levels — the same care levels
we already hold.

So testing "is this scheduled" by NLEM membership is structurally the right
test, and our 239-medicine NLEM 2022 load is the right instrument for it. What
was wrong was not the test but the conclusion drawn from failing it: not
scheduled means no ceiling has been fixed, not that price is free.

---

## 9. Brand counts are two orders of magnitude off

The Competition Commission of India's market study on the pharmaceutical sector
settles the competition question with numbers, and they demolish the approach I
was taking. Two of its examples are in our therapy areas:

| Formulation | Brands | Companies |
|---|---|---|
| Rosuvastatin 10 mg | **127** | 105 |
| Glimepiride + metformin 500 mg | **137** | 120 |
| Amoxicillin + clavulanic acid 125/500 mg | 292 | 217 |

That last one sells **₹40 to ₹336 for a pack of six — an 8.4x spread on an
identical formulation**. Our catalogue lists three "key brands" for
rosuvastatin. Counting them was never going to measure anything.

CCI also documents **brand proliferation within a single company** — 15
companies market two different brands of the same glimepiride + metformin
formulation. So even company count overstates independence, exactly as
Vymada/Azmarda showed.

Generics are about **97% of Indian drug consumption by value**.

### The trade controls the shelf

CCI's finding, from its own enforcement cases: *"the entire supply chain of
drugs is 'self-regulated' by the trade associations, resulting in market
distortions"* — the apex association and its local affiliates *"play a
gatekeeper role at various levels of the distribution chain, making
pharmaceutical markets impervious to the incentives of competition."*
Appointment of a stockist has required a **No-Objection Certificate** from the
association.

Which answers the question I could not: **the chemist decides**, and margin
decides the chemist. Where a prescribed brand is absent, substitution goes to
the higher-margin brand, and companies raise that margin with schemes — "buy
10 get 2 free" — rather than by changing MRP. AIOCD has sought 10% for
wholesalers and 20% for retailers as a formal position.

India runs **over 600,000 medical representatives**, and roughly **60% of
promotional budget** goes to field force. Demand is created by feet, not by
price.

---

## 10. Indian clinical guidance is its own body of work

Not adaptations of Western guidelines — separate documents by Indian societies,
with Indian thresholds:

- **Lipid Association of India** — Consensus Statement IV, Feb 2024
- **Indian Society of Hypertension** — Consensus Guideline 2025, 63 experts
- **API / CSI / ICP / HSI** — joint Indian hypertension guidelines since 2001
- **RSSDI** — Clinical Practice Recommendations 2022, 150+ experts
- **NHM Standard Treatment Guidelines** — the public-system reference

So "what does the guideline say" has an Indian answer that can differ from the
ESC or ADA one, and a medical affairs user here will be asked about the Indian
one.

---

## 11. Prescription control and labelling

**Schedule H1** covers antibiotics and other restricted molecules: the Rx
symbol in **red** in the upper left, a **red-bordered box warning**, and the
pharmacist must **retain the prescription** and maintain a sales register.
Package inserts are governed by Schedule D(II) Section 6 of the Drugs and
Cosmetics Rules — a different structure from an FDA label, so Indian
prescribing information is its own document and not a translation.

---

## 12. Private insurance mechanics

IRDAI Master Circular 2024: cashless **pre-authorisation within one hour**,
discharge approval **within three hours**, reimbursement claims settled within
**30 days**. Floors of a **36-month** pre-existing disease waiting period and a
**5-year moratorium** after which claims cannot be rejected. Group cover is
administered through a **TPA** or the insurer directly.

Exclusions are per-policy rather than standardised, so whether a specific drug
is covered cannot be answered generally — only against a named policy. That is
a real limit on what the platform can claim about private coverage.

---

## 13. Public procurement is a third price, and it is the floor

Central government buys through the **Medical Stores Organisation** (DGHS,
MoHFW): seven Government Medical Store Depots — Mumbai, Kolkata, Chennai,
Hyderabad, Guwahati, Karnal, New Delhi — with quality-control laboratories
attached at three, testing **before acceptance**. Purchasing runs on an annual
**indent cycle** against **rate contracts**, tendered through the Central Public
Procurement portal, with a **debarment register** for firms, laboratories and
products.

Only **8 rate contracts were active** when read, so MSO's own coverage is
narrow. Its site navigation is broken — every menu item resolves to
`/portal/undefined` — so the rate contract and debarred lists could not be
opened.

The states are the better window. **TNMSC** publishes a drug list with prices:

| TNMSC | per tablet |
|---|---|
| Amlodipine 10 mg | ₹0.90 |
| Atorvastatin 80 mg | ₹3.15 |
| Amiodarone 200 mg | ₹5.31 |
| Aceclofenac 100 mg | ₹0.72 |

Against our catalogue's retail figures — ramipril ₹7.00 a tablet, enalapril
₹3.50 — public procurement sits far below branded retail for the same
molecules. **So there are at least three prices for one drug: the public
procurement price, the branded retail price, and the MRP printed on the pack.**
The platform models one.

TNMSC also publishes a **blacklist**, as MSO does. Supplier debarment is public
in both, which makes it a checkable quality and continuity signal — a molecule
whose only Indian maker is debarred is a supply risk, and that is knowable.

---

## 14. What this corrects in the build

| Was | Actually |
|---|---|
| US exclusivity read as Indian competition | Different market entirely — no patent linkage, branded generics are the default |
| `price_controlled: False` treated as pricing freedom | Means *no ceiling fixed yet*. Para 19 exposure is permanent |
| "10% annual cap" applied generally | 10% is **non-scheduled** (para 20). Scheduled moves by **WPI** in April |
| `MANY_BRANDS = 5`, a constant I invented | DPCO para 6 defines absence of competition as **fewer than five manufacturers with ≥1% market share** — right number, wrong basis |
| Price treated as one number | PTS, PTR, retail price and MRP are legally distinct and differ by known factors |
| Share data "not obtainable" | Not purchasable by us, but NPPA legislates on it and the ceiling prices we hold encode it |
| IPD "covered, bundled in the claim" | Under PM-JAY it is a fixed all-inclusive package the hospital must fit the drug inside |
| Threat model = generic entry | Threat model = **NPPA margin capping under para 19** |
| Brand count as the competition signal | Rosuvastatin has **127 brands from 105 companies**; our list holds 3. Spread, not count |
| Demand assumed to follow the prescription | The chemist substitutes to the higher-margin brand; 600,000 MRs create the demand |
| "The guideline" meaning ESC or ADA | India has its own — LAI, InSH, RSSDI, CSI/API — with different thresholds |

---

## 6. Still not established

- Whether one brand prices consistently across retail sites. The marketer
  question is **answered**: our scraper does capture it, on 209 of 650 listings
  (32%), so brand-to-marketer is partially derivable already.
- Brand → owner mapping. Vymada and Azmarda are one Novartis asset marketed by
  Novartis and Cipla respectively; the catalogue records marketers, not owners,
  and in 106 of 218 rows the brand and marketer lists are different lengths, so
  they cannot be paired positionally.
- How a hospital formulary is actually set, and by whom. (Partially answered
  for retail — the chemist decides and margin decides the chemist — but
  institutional formularies remain unread.)
- How Jan Aushadhi interacts with branded generics at the counter. The PMBI site
  serves an app shell for every path including its own API, so it remains
  unread.

---

## Sources

- DPCO 2013, consolidated with amendments — paras 4, 5, 6, 19, 20 and
  definitions. [nppa.gov.in](https://nppa.gov.in/en/drugspricescontrolorder2013)
- NPPA FAQs — [nppa.gov.in/en/faqs](https://nppa.gov.in/en/faqs). **Stale in
  places**: still describes DPCO 1995 and "74 bulk drugs under price control",
  superseded by NLEM-based scheduling under DPCO 2013.
- TMR on 42 anti-cancer drugs — [PIB PRID 1744388](https://www.pib.gov.in/PressReleasePage.aspx?PRID=1744388),
  [PIB PRID 1566632](https://www.pib.gov.in/Pressreleaseshare.aspx?PRID=1566632&reg=3&lang=2),
  [Mondaq](https://www.mondaq.com/india/healthcare/791012/india-puts-42-non-scheduled-cancer-drugs-under-price-control)
- Oxygen concentrator margin cap — [Medical Dialogues](https://medicaldialogues.in/news/industry/medical-devices/covid-relief-to-patients-nppa-caps-trade-margin-on-oxygen-concentrators-at-70-percent-78298)
- PM-JAY Health Benefit Package 2.2 manual — [hem.nha.gov.in/HBP.pdf](https://hem.nha.gov.in/HBP.pdf),
  [NHA](https://nha.gov.in/PackagesAndRates)
- CGHS medicines and rate lists — [cghs.gov.in](https://cghs.gov.in/index1.php?lang=1&level=3&sublinkid=5952&lid=3886)
- Branded vs branded-generic retailer margins — [PubMed 21572645](https://pubmed.ncbi.nlm.nih.gov/21572645/)
