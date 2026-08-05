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
That is why 1mg and PharmEasy can discount 15–25% lawfully — and why a scraped
retail price and an MRP are different numbers that must not be compared.

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
employees.

---

## 5. What this corrects in the build

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

---

## 6. Still not established

- Whether retail listings reliably carry the marketing company, and whether one
  brand prices consistently across the four retail sites we scrape. Until that
  is checked, price spread is contaminated by site rather than by competition.
- Brand → owner mapping. Vymada and Azmarda are one Novartis asset marketed by
  Novartis and Cipla respectively; the catalogue records marketers, not owners,
  and in 106 of 218 rows the brand and marketer lists are different lengths, so
  they cannot be paired positionally.
- How a hospital formulary is actually set, and by whom.
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
