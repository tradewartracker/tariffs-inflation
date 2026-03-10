# tariffs-inflation

Estimates the pass-through of import tariffs into U.S. consumer prices (PCE inflation) using BEA input-output tables, Census import data, and the Leontief inverse.

For a full description of the methodology see [tariff_pce_methodology.md](tariff_pce_methodology.md).

---

## How it works

The pipeline translates a change in tariff rates into a predicted price level effect on personal consumption expenditures (PCE) through three main stages:

1. **Tariff rates** — Effective tariff rates (duties / import value) are computed at the 6-digit NAICS level from Census monthly import data, then mapped to BEA IO industries. A baseline rate (annual average for a chosen year) is compared against a chosen current month to produce `Δτ` per industry.

2. **Input-output propagation** — Using BEA Supply (Table 262) and Use (Table 259) tables, a Leontief inverse is constructed. Direct import shares are propagated through the full supply chain to capture both first-round and higher-order cost pass-through.

3. **PCE bridge** — Total import content per industry is mapped to PCE categories via the BEA PCE Bridge workbook. The result is a predicted price change for each PCE category, aggregated to a headline or core PCE impact.

---

## Files

| File | Purpose |
|---|---|
| `config.py` | All user-facing parameters (years, file paths, BEA API key, markup assumption). **Start here.** |
| `pipeline.py` | Pure functions implementing each step of the methodology. |
| `compute_tariff_rates.py` | Loads Census import parquet data and computes effective tariff rates by NAICS code. |
| `concordance.py` | Maps 6-digit NAICS codes to BEA IO industry codes. |
| `make-imports-naics-dataset.ipynb` | Prepares the Census import data into the parquet format expected by the pipeline. |
| `parse-bea-io.ipynb` | Exploratory notebook for inspecting BEA IO tables. |
| `naics-bea-concordance-test.ipynb` | Tests and validates the NAICS → BEA concordance mapping. |
| `tariff_pce_methodology.md` | Detailed methodology documentation. |

---

## Quickstart

### 1. Prerequisites

```
pip install pandas numpy requests openpyxl pyarrow
```

A [BEA API key](https://apps.bea.gov/API/signup/) is required. Set it as an environment variable to avoid committing credentials:

```powershell
$env:BEA_KEY = "your-key-here"
```

### 2. Prepare import data

Run `make-imports-naics-dataset.ipynb` to download and build the Census import parquet file. The output should be placed at the path specified by `IMPORTS_FILE` in `config.py` (default: `data/imports/TOTALnaics-data-YYYY-MM.parquet`).

### 3. Configure

Edit `config.py` to set:

- `IO_YEAR` — which BEA IO tables to use (e.g. `2024`)
- `TARIFF_BASELINE_YEAR` — the pre-tariff baseline year for average rates
- `TARIFF_CURRENT_MONTH` — the month whose tariff rates represent the "current" policy (e.g. `"2025-12"`)
- `MARKUP_ASSUMPTION` — `"constant_dollar"` (conservative, recommended) or `"constant_percent"`
- `INFLATION_MEASURE` — `"core_pce"`, `"headline_pce"`, or `"core_goods_pce"`

### 4. Run the pipeline

Import and call the step functions from `pipeline.py` in a notebook or script. Each function is documented with its corresponding section in the methodology file.

---

## Data

- **Census import data** — Monthly imports and duties by 6-digit NAICS code. Downloaded and processed via `make-imports-naics-dataset.ipynb`, stored as a parquet file in `data/imports/`.
- **BEA IO tables** — Fetched at runtime from the BEA API (Tables 259 and 262).
- **BEA PCE Bridge** — Fetched at runtime from the BEA website.

