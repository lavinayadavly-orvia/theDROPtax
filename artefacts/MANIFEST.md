# DROP Tax — data artefacts

Exported 2026-08-06T10:03:55+00:00 from the `droptax` database.

Curated for the DROP Tax platform and reusable on their own. Every file carries its caveats below, and they are repeated inside the JSON files. Carried across without them, each of these becomes a confident false statement — which is how several of them entered this codebase.

**Scope: CardioMetabolic and Women's Health. No oncology.**

**A molecule has at least four prices in India** — Jan Aushadhi, the MSO contract, a public counter, and branded retail, with MRP a ceiling above all of them. Any single figure needs to say which one it is.

| File | Rows | What it is |
|---|---|---|
| `therapy_area_registry.json` | 37 | Indications with endpoints, benefit direction and normalisation |
| `drug_catalogue.json` / `.csv` | 218 | Molecules with every derived field |
| `indications.csv` | 438 | One row per (drug × indication) |
| `nppa_ceiling_prices.csv` | 1,012 | Statutory ceilings, gazette-cited |
| `nlem_2022.csv` | 239 | Essential medicines with care levels |
| `cdsco_new_drug_approvals.csv` | 472 | India approvals, indication and date |
| `cdsco_biologics_permissions.csv` | 486 | Who may make or import, by firm |
| `cghs_restricted_medicines.csv` | 407 | Who must approve a restricted medicine, and on what cost trigger |
| `mso_rate_contract.csv` | 525 | What central government pays, with contract windows |
| `janaushadhi_product_mrp.csv` | 2,439 | PMBJP prices — the floor a patient can pay |
| `verified_label_facts.json` | **1** | DailyMed facts with verbatim quotes. Inclisiran only |

## How far to trust each file

### `drug_catalogue.csv`
- 213 of 218 prices are ESTIMATES. 156 are a per-unit retail price scaled to a month on an ASSUMED once-daily dose — a drug taken three times a day costs three times the figure shown. price_is_estimated and price_note carry this per row; do not use the number without them.
- Clinical endpoints are present for 1 molecule of 218.
- key_brands is a curated list of brands worth knowing, not every brand on the market. Counts derived from it are FLOORS.

### `indications.csv`
- Split from free text on ';' only — commas never separate, because several rows carry commas inside parentheses.
- 107 of 438 do not resolve to the therapy-area registry. They are kept and marked unmapped rather than forced to the nearest entry.

### `nppa_ceiling_prices.csv`
- Statutory ceilings under DPCO 2013, each with its gazette notification number and date. A retailer may sell below the ceiling, never above.

### `nlem_2022.csv`
- NLEM membership gates statutory price control. Absence from the list is equally informative — the manufacturer prices freely.

### `cdsco_new_drug_approvals.csv`
- Covers small molecules. Thin before roughly 2009, and nine of the forty source lists are image tables with no text layer that could not be read.
- ABSENCE IS NOT NON-APPROVAL. Inclisiran, sacubitril and tenecteplase are all marketed in India and none appear here — they entered by import permission or Subject Expert Committee clearance, which is a different register.

### `cdsco_biologics_permissions.csv`
- r-DNA origin only: recombinant proteins and biosimilars. CT-21 is permission to manufacture and market, CT-18 to import and market.
- out_of_scope marks oncology rows — the register is roughly a quarter oncology and this platform covers CardioMetabolic and Women's Health.
- Better evidence than a curated brand list, but NOT more complete: the consolidated file lists one manufacturer for tenecteplase where a monthly file from the same register names another.

### `verified_label_facts.json`
- ONE MOLECULE, NOT FIFTY. verify_from_dailymed.py checked 50 innovators; only inclisiran was ever persisted. Every field it does hold carries source_name, source_url, retrieved date and a verbatim quote.

### `cghs_restricted_medicines.csv`
- Restricted does NOT mean excluded — it means the medicine needs authorisation. STC is the Standing Technical Committee, a board that must clear the patient's file; non-STC is approved locally by the Additional Director or CMO of the Medical Store Depot.
- The route is chosen by COST: above roughly Rs10,000 per administration, Rs50,000 a month, or a cancer cycle above Rs15,00,000.
- The lists move. An STC drug approved in more than 20 separate cases within six months transitions to the non-STC online list; immunotherapy is the standing exception.

### `mso_rate_contract.csv`
- What central government actually pays. Every row carries its own contract window — a rate is only the rate between its dates.
- Loaded from a supplied copy: mso-gmsd.in resolves every menu item to /portal/undefined, so it could not be fetched from source.
- VMS is the code's own label in the contract and is deliberately NOT expanded, because it has not been read anywhere.

### `janaushadhi_product_mrp.csv`
- PMBJP prices — for a molecule listed here this is close to the least a patient can pay in India, and the reference every other price should be read against.
- Zero MRP means UNDER PROCESS, not free. The site says so itself.

### `therapy_area_registry.json`
- Per-indication endpoints with benefit direction and a normalisation spec. direction matters: LDL-C, HbA1c, blood pressure and menstrual blood loss are lower-better; functional independence and BMD are higher-better.

## Two rules that apply to all of it

1. **Absence is not a negative finding.** A molecule missing from a register is not evidence it is unapproved, unpriced or uncontested — the registers are incomplete in documented ways.
2. **An estimate is not a measurement.** Where a field is flagged estimated, the assumption behind it is named in the same row. Strip the flag and you have manufactured a fact.
