# DROP Tax — data artefacts

Exported 2026-08-05T12:35:13+00:00 from the `droptax` database.

Curated for the DROP Tax platform and reusable on their own. Every file carries its caveats below, and they are repeated inside the JSON files. Carried across without them, each of these becomes a confident false statement — which is how several of them entered this codebase.

**Scope: CardioMetabolic and Women's Health. No oncology.**

| File | Rows | What it is |
|---|---|---|
| `therapy_area_registry.json` | 37 | Indications with endpoints, benefit direction and normalisation |
| `drug_catalogue.json` / `.csv` | 218 | Molecules with every derived field |
| `indications.csv` | 438 | One row per (drug × indication) |
| `nppa_ceiling_prices.csv` | 1,012 | Statutory ceilings, gazette-cited |
| `nlem_2022.csv` | 239 | Essential medicines with care levels |
| `cdsco_new_drug_approvals.csv` | 472 | India approvals, indication and date |
| `cdsco_biologics_permissions.csv` | 486 | Who may make or import, by firm |
| `verified_label_facts.json` | **1** | DailyMed facts with verbatim quotes. Only inclisiran — 50 innovators were checked, one was persisted |

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
- out_of_scope marks oncology rows — the register is roughly a quarter oncology by volume and this platform covers CardioMetabolic and Women's Health. Rows are marked, not deleted.
- Better evidence than a curated brand list, but NOT more complete: the consolidated file lists one manufacturer for tenecteplase where a monthly file from the same register names another.

### `verified_label_facts.json`
- Every field carries source_name, source_url, retrieved date and a verbatim quote. Facts without a quote were not verified and are absent.

### `therapy_area_registry.json`
- Per-indication endpoints with benefit direction and a normalisation spec. direction matters: LDL-C, HbA1c, blood pressure and menstrual blood loss are lower-better; functional independence and BMD are higher-better.

## Two rules that apply to all of it

1. **Absence is not a negative finding.** A molecule missing from a register is not evidence it is unapproved, unpriced or uncontested — the registers are incomplete in documented ways.
2. **An estimate is not a measurement.** Where a field is flagged estimated, the assumption behind it is named in the same row. Strip the flag and you have manufactured a fact.
