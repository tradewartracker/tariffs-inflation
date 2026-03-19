# tariffs-inflation

Estimates the pass-through of import tariffs into U.S. consumer prices (PCE inflation) using BEA input-output tables, Census import data, and the Leontief inverse.

Two parallel pipelines are provided:

- **Summary pipeline** (71 industries) — Uses BEA summary IO tables fetched via the API. Annual data available for 1997–2023. See [tariff_pce_methodology.md](tariff_pce_methodology.md).
- **Detail pipeline** (402 commodities) — Uses BEA benchmark-year detail IO tables downloaded as Excel files. Available for 2017 only. The detailed methodology document is [tariff_pce_detail_methodology.md](tariff_pce_detail_methodology.md). This approach Resolves aggregation bias present at the summary level and more closely mimics the work of [Yale Budget Lab](https://budgetlab.yale.edu/research/methodological-appendix-tracking-economic-effects-tariffs) and [Barbiero & Stein of the Boston Fed](https://www.bostonfed.org/publications/current-policy-perspectives/2025/the-impact-of-tariffs-on-inflation.aspx). 

---

## How it works

Both pipelines translate a change in tariff rates into a predicted price level effect on personal consumption expenditures (PCE) through three main stages:

1. **Tariff rates** — Effective tariff rates (duties / import value) are computed at the 6-digit NAICS level from Census monthly import data, then mapped to BEA IO industries (summary) or commodities (detail). A baseline rate (annual average for a chosen year) is compared against a chosen current month to produce `Δτ` per industry/commodity.

2. **Input-output propagation** — A Leontief inverse captures both first-round and higher-order cost pass-through. The summary pipeline constructs it from BEA Use Table 259; the detail pipeline uses BEA's pre-computed 402×402 Commodity-by-Commodity Total Requirements matrix.

3. **PCE bridge** — Total import content per industry/commodity is mapped to PCE categories via the BEA PCE Bridge. The result is a predicted price change for each PCE category, aggregated to a headline or core PCE impact.

---

## Files

### Summary pipeline (71 industries)

| File | Purpose |
|---|---|
| `pipeline.py` | Pure functions implementing each step of the summary methodology. |
| `concordance.py` | Maps 6-digit NAICS codes to BEA summary IO industry codes. |
| `parse-bea-io-final.ipynb` | End-to-end notebook running the summary pipeline with scatter plots and counterfactuals. |
| `tariff_pce_methodology.md` | Detailed methodology documentation (summary pipeline). |

### Detail pipeline (402 commodities)

| File | Purpose |
|---|---|
| `pipeline_detail.py` | Pure functions implementing each step of the detail methodology. |
| `concordance_detail.py` | Maps 6-digit NAICS codes to BEA 402-commodity detail codes via longest-prefix matching. |
| `download_detail_data.py` | One-time download of BEA detail IO Excel files into `data/io_detail/`. |
| `parse-bea-io-detail.ipynb` | End-to-end notebook running the detail pipeline with scatter plots and counterfactuals. |
| `tariff_pce_detail_methodology.md` | Detailed methodology documentation (detail pipeline). |
| `detail_data_sources.md` | Reference for all detail-level data files and download URLs. |

### Shared

| File | Purpose |
|---|---|
| `config.py` | All user-facing parameters (years, file paths, BEA API key, markup assumption). **Start here.** |
| `compute_tariff_rates.py` | Loads Census import parquet data and computes effective tariff rates by NAICS code. |
| `make-imports-naics-dataset.ipynb` | Prepares the Census import data into the parquet format expected by both pipelines. |

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

- `IO_YEAR` — which BEA summary IO tables to use (e.g. `2022`)
- `TARIFF_BASELINE_YEAR` — the pre-tariff baseline year for average rates
- `TARIFF_CURRENT_MONTH` — the month whose tariff rates represent the "current" policy (e.g. `"2025-12"`)
- `MARKUP_ASSUMPTION` — `"constant_dollar"` (conservative, recommended) or `"constant_percent"`
- `INFLATION_MEASURE` — `"core_pce"`, `"headline_pce"`, or `"core_goods_pce"`

### 4a. Run the summary pipeline

Open `parse-bea-io-final.ipynb` or import and call the step functions from `pipeline.py`. Each function is documented with its corresponding section in `tariff_pce_methodology.md`.

### 4b. Run the detail pipeline

First download the BEA detail IO Excel files (one-time, ~20 MB):

```
python download_detail_data.py
```

Then open `parse-bea-io-detail.ipynb` or import and call the step functions from `pipeline_detail.py`. The detail pipeline uses the same tariff data and config parameters as the summary pipeline but operates at the 402-commodity level.

---

## Data

- **Census import data** — Monthly imports and duties by 6-digit NAICS code. Downloaded and processed via `make-imports-naics-dataset.ipynb`, stored as a parquet file in `data/imports/`.
- **BEA summary IO tables** — Fetched at runtime from the BEA API (Tables 259 and 262). Annual data for 1997–2023.
- **BEA detail IO tables** — Downloaded once via `download_detail_data.py` into `data/io_detail/`. Benchmark year 2017 only. Includes Supply table, pre-computed Leontief inverse, and detail PCE bridge.
- **BEA PCE Bridge** — Summary bridge fetched at runtime from the BEA website; detail bridge included in the detail data download.
- **NAICS → BEA concordance** — For summary: `data/concordance/naics_to_bea_summary.csv`. For detail: `data/stuff/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx`.

