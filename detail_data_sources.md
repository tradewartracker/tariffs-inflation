# 402-Commodity Detail IO: Data Sources

## Required Files

### 1. Supply Table (Detail, 2017)

| | |
|---|---|
| **File** | `Supply_2017_DET.xlsx` |
| **What it provides** | Import shares per commodity: m_i = imports (MCIF) / total supply (T013) |
| **Dimensions** | ~402 commodities × ~418 columns (industries + aggregates) |
| **Sheet used** | `2017` |
| **Source** | Bundled in `AllTablesSUP.zip` |
| **Download** | https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesSUP.zip (20 MB) |
| **Also available directly** | https://apps.bea.gov/industry/xls/io-annual/Use_SUT_Framework_2017_DET.xlsx — but only the Supply file serves via direct URL; the rest require the zip |

### 2. Commodity-by-Commodity Total Requirements (Detail, 2017)

| | |
|---|---|
| **File** | `CxC_TR_2017_PRO_DET.xlsx` |
| **What it provides** | Pre-computed Leontief inverse L at producer prices (402×402 matrix) |
| **Dimensions** | 409 rows × 404 columns (402 commodities + code/description columns) |
| **Sheet used** | `2017` |
| **Source** | Bundled in `AllTablesSUP.zip` (same zip as above) |
| **Download** | https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesSUP.zip |
| **Notes** | This is BEA's official (I − A)^{-1} at the detail level. Diagonal elements > 1; off-diagonal ≥ 0. Also contains a `NAICS Codes` sheet with the BEA→NAICS concordance. |

### 3. PCE Bridge (Detail)

| | |
|---|---|
| **File** | `PCEBridge_Detail.xlsx` |
| **What it provides** | Maps 402 BEA commodity codes to ~211 NIPA PCE categories, with producers' value, transport costs, wholesale/retail margins, and purchasers' value |
| **Dimensions** | ~711 rows per year |
| **Sheets** | `2007`, `2012`, `2017` (plus `Data Layout`, `NAICS Codes`, `PCE Categories`) |
| **Download** | https://apps.bea.gov/industry/release/xlsx/PCEBridge_Detail.xlsx |
| **Notes** | Commodity codes are 6-character BEA detail codes (e.g., `336111` for automobile manufacturing). Same column structure as the summary bridge already used by the pipeline. |

### 4. NAICS → BEA Concordance

| | |
|---|---|
| **File** | `BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx` |
| **What it provides** | Maps NAICS codes (at varying digit levels: 3–6) to BEA codes at every aggregation level: Sector → Summary → U.Summary → Detail |
| **Location** | Already in the repo at `data/stuff/BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx` |
| **Key columns** | Col 6 (`Detail` BEA code), Col 7 (Detail description), Col 11 (`Related 2017 NAICS Codes`), Col 12 (NAICS description) |
| **Dimensions** | ~510 rows |
| **Notes** | NAICS codes appear at mixed digit levels (e.g., `1112` for vegetable farming, `11115` for corn farming, `3361` for motor vehicles). The concordance builder will need longest-prefix matching to map 6-digit Census NAICS codes to the appropriate BEA detail commodity. |

---

## Already in Use (Unchanged)

| File | Location | Role |
|---|---|---|
| `TOTALnaics-data-2025-12.parquet` | `data/imports/` | Census import/duty data at NAICS6 level — feeds tariff rate computation |
| `PCEBridge_Summary.xlsx` | Fetched from BEA API at runtime | Summary-level PCE bridge (existing pipeline) |

---

## Zip Contents Reference

### `AllTablesSUP.zip` — Supply-Use Framework Tables

| File | Level | Years |
|---|---|---|
| `Supply_2017_DET.xlsx` | **Detail (402)** | 2017 only |
| `Use_SUT_Framework_2017_DET.xlsx` | **Detail (402)** | 2017 only |
| `CxC_TR_2017_PRO_DET.xlsx` | **Detail (402)** | 2017 only |
| `IxC_TR_2017_PRO_DET.xlsx` | Detail (402) | 2017 only |
| `IxI_TR_2017_PRO_DET.xlsx` | Detail (402) | 2017 only |
| `Supply_Tables_1997-2023_Summary.xlsx` | Summary (71) | 1997–2023 |
| `Use_Tables_Supply-Use_Framework_1997-2023_Summary.xlsx` | Summary (71) | 1997–2023 |
| `CxC_TR_1997-2023_Summary.xlsx` | Summary (71) | 1997–2023 |
| + 6 more sector-level files | Sector (~15) | 1997–2023 |

### `AllTablesIO.zip` — After-Redefinitions Tables (for future B&S formulation)

| File | Level | Years |
|---|---|---|
| `IOMake_After_Redefinitions_2017_Detail .xlsx` | **Detail (402)** | 2017 only |
| `IOUse_After_Redefinitions_PRO_2017_Detail.xlsx` | **Detail (402)** | 2017 only |
| `IOUse_After_Redefinitions_PUR_2017_Detail.xlsx` | **Detail (402)** | 2017 only |
| `IOMake_Before_Redefinitions_2017_Detail.xlsx` | Detail (402) | 2017 only |
| `IOUse_Before_Redefinitions_PRO_2017_Detail.xlsx` | Detail (402) | 2017 only |
| `CxI_DR_2017_Detail.xlsx` | Detail (402) | 2017 only |
| + summary/sector files | Summary/Sector | 1997–2023 |

**Download**: https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesIO.zip (16 MB)

---

## Year Availability

| Level | Available years | Source |
|---|---|---|
| Detail (402 commodities) | **2017 only** (benchmark year) | Excel downloads |
| Summary (71 industries) | 1997–2023 (annual) | BEA API or Excel |
| Sector (~15 sectors) | 1997–2023 (annual) | BEA API or Excel |

The Boston Fed uses 2017 detail as the base and interpolates forward using annual summary trends. For this implementation, we use 2017 detail tables directly.
