# Methodology Comparison: This Repo vs. Yale Budget Lab

A step-by-step comparison of the tariff-to-inflation pipeline in this repository with the Yale Budget Lab's [tariff-impact-tracker](https://github.com/Budget-Lab-Yale/tariff-impact-tracker) and their [retrospective analysis](https://budgetlab.yale.edu/research/one-year-tariff-analysis-what-we-got-right-what-changed-and-what-we-learned) (April 2, 2026).

---

## Notation

| Symbol | Definition |
|---|---|
| $i$ | BEA commodity index (IO level, ~71 summary industries) |
| $k$ | PCE category index (27 core goods categories) |
| $m_i$ | Direct import share of commodity $i$: imports / total supply |
| $L_{ij}$ | Leontief total requirements matrix entry: total amount of commodity $i$ required (directly and indirectly) per dollar of commodity $j$ output |
| $\tilde{m}_j = \sum_i m_i \cdot L_{ij}$ | Total import content of commodity $j$ (direct + all upstream tiers) |
| $\Delta\tau_i$ | Change in effective tariff rate on commodity $i$: current period minus baseline |
| $\hat{p}_j = \sum_i (m_i \cdot \Delta\tau_i) \cdot L_{ij}$ | Predicted producer price effect on commodity $j$ (this repo) |
| $B_{ik}$ | PCE bridge weight: value of commodity $i$ in PCE category $k$ |
| $\hat{P}_k$ | Predicted consumer price effect on PCE category $k$ (bridged from $\hat{p}_j$) |
| $s_k$ | Import content share of PCE category $k$: bridge-weighted average of $\tilde{m}_j$ (Yale) |
| $e_k$ | PCE expenditure share of category $k$ |

Yale's code uses $R_{c,j}$ for the Leontief matrix and $c$ for commodity — these are equivalent to $L_{ij}$ and $i$ above.

---

## 1. Input-Output Framework

### 1a. Import Shares

This repo: [`pipeline.py:step1_import_shares()`](code/pipeline.py#L22) | Yale: [`import_price_index.R` §2](https://github.com/Budget-Lab-Yale/tariff-impact-tracker/blob/main/R/import_price_index.R)

| | This Repo | Yale Tracker |
|---|---|---|
| **Source** | BEA Supply Table (TableID 262) | BEA Import Matrix (static Excel, 2024) |
| **Formula** | $m_i = \text{imports}_i / \text{total supply}_i$ | $m_i = \text{imports}_i / \text{total use}_i$ |
| **Denominator** | Total supply (output + imports) | Total use of products (from Use Table) |
| **Year** | Configurable (`IO_YEAR`, default 2024) | Fixed at 2024 |
| **Retrieval** | BEA API at runtime | Pre-downloaded Excel file |

The denominators differ slightly — total supply vs. total use — but for most commodities these are close to identical. Both represent the total availability of the commodity in the domestic economy.

### 1b. Leontief Inverse

This repo: [`pipeline.py:step2_3_leontief()`](code/pipeline.py#L62) | Yale: [`import_price_index.R` §2b](https://github.com/Budget-Lab-Yale/tariff-impact-tracker/blob/main/R/import_price_index.R)

| | This Repo | Yale Tracker |
|---|---|---|
| **Method** | Either (a) compute $(I-A)^{-1}$ from Use Table 259, or (b) fetch BEA's pre-computed Total Requirements (TableID 59) | Read BEA's pre-computed Commodity-by-Commodity Total Requirements from Excel |
| **Default** | `LEONTIEF_SOURCE = "bea"` (pre-computed) | Pre-computed (Excel file) |
| **Granularity** | 71 industries (summary) or 402 commodities (detail pipeline) | ~73 commodities (summary level) |
| **Validation** | Cross-checks computed L against BEA's published L and reports discrepancies | None documented |

Both approaches ultimately use the same BEA Leontief inverse at the summary level. The construction is equivalent.

### 1c. Total Import Content

This repo: [`pipeline.py:step4_total_import_content()`](code/pipeline.py#L195) | Yale: [`import_price_index.R` §2b](https://github.com/Budget-Lab-Yale/tariff-impact-tracker/blob/main/R/import_price_index.R)

| | This Repo | Yale Tracker |
|---|---|---|
| **Formula** | $\tilde{m}_j = \sum_i m_i \cdot L_{ij}$ | Same: $\tilde{m}_j = \sum_i m_i \cdot L_{ij}$ (Yale writes this as $\sum_c R_{c,j} \times m_c$) |
| **Interpretation** | Total import content embedded in one dollar of commodity $j$'s output, via all upstream tiers | Same |

Same computation: the Leontief inverse propagates direct import shares through all tiers of the supply chain.

---

## 2. Tariff Rates

This repo: [`pipeline.py:step5_delta_tariff()`](code/pipeline.py#L256) + [`compute_tariff_rates.py`](code/compute_tariff_rates.py) | Yale: [`employment_index.R` §2](https://github.com/Budget-Lab-Yale/tariff-impact-tracker/blob/main/R/employment_index.R)

| | This Repo | Yale Tracker |
|---|---|---|
| **Source** | Census monthly import data (parquet), NAICS6 | USITC Customs and Duties (monthly Excel), NAICS commodity level |
| **Effective rate** | duties / imports at NAICS6 level | duties / customs value at NAICS commodity level |
| **Baseline** | Annual average over all 12 months of baseline year (default 2024); computed as sum(duties)/sum(imports) across months | 2022–2024 average effective rate |
| **Current period** | Single month (default `2025-12`) | Varies; most recent available Census month |
| **Concordance** | NAICS6 → BEA summary codes via `concordance.py` or external CSV crosswalk | NAICS → BEA via `naics_to_bea_crosswalk.csv` |

Both compute effective tariff rates per commodity using actual duties collected (not statutory rates). The concordance mapping is similar but implemented independently.

**How the commodity-level tariff rates are used differs.** 

- This repository keeps $\Delta\tau_i$ as a per-commodity vector throughout the pipeline — it enters the Leontief multiplication element-wise (Section 3). 

- Yale computes commodity-level rates but then **collapses them to a single scalar** before the price effects calculation in Section 3. Specifically, they compute `tariff_increase_core` $= \overline{\Delta\tau} = \sum_i v_i \cdot \Delta\tau_i$, a customs-value-weighted average across all core goods commodities (where $v_i$ are customs-value weights).

---

## 3. Tariff Effect Propagation

This repo: [`pipeline.py:step6_pce_effect()`](code/pipeline.py#L319) lines 360–362 | Yale: [`report_setup.R`](https://github.com/Budget-Lab-Yale/tariff-impact-tracker/blob/main/R/report_setup.R) line 886

Both repos use the Leontief inverse to propagate import shares through the supply chain — but they differ in **where commodity-specific tariff rates enter the calculation**.

### This Repo: Tariff Rates Inside the Leontief

$$\hat{p}_j = \sum_i (m_i \cdot \Delta\tau_i) \cdot L_{ij}$$

Each commodity $i$ carries its own tariff change $\Delta\tau_i$ *before* multiplication by the Leontief inverse. The predicted price effect on industry $j$ reflects the specific tariff rates faced by each of its upstream inputs: steel, electronics, rubber, chemicals, etc. The result is a **per-commodity predicted price effect** that varies across industries based on their supply-chain-specific tariff exposure.

### Yale Tracker: Tariff Rates Outside the Leontief

Yale's tracker computes total import content via the Leontief (same as above):

$$\tilde{m}_j = \sum_i m_i \cdot L_{ij}$$

And then uses these as static weights for a price index. For the predicted price effect it multiplies a **single scalar** $\Delta\tau$ by a single scalar import share:

```
expected_core = tariff_increase_core * IMPORT_SHARE_CORE_GOODS
```

Here `tariff_increase_core` $= \overline{\Delta\tau} = \sum_i v_i \cdot \Delta\tau_i$ is a customs-value-weighted average of commodity-level tariff rates across core goods (see Section 2), and `IMPORT_SHARE_CORE_GOODS` $= \bar{s} = \sum_k e_k \cdot s_k$ is an expenditure-weighted average of per-category Leontief-derived import content (computed in `import_price_index.R`). Both are derived from commodity-level data. One difference relative to this repository is that both of these values are **collapsed to scalars** before multiplication:

$$\hat{p}^{\text{Yale}} = \overline{\Delta\tau} \cdot \bar{s}$$

And all cross-commodity variation in tariff rates is averaged away.

### Why the Distinction Matters

If tariff rates were uniform across commodities, the two approaches would be identical — $\Delta\tau$ factors out. But 2025 tariff rates varied enormously: near-zero on pharmaceuticals, ~5% on some electronics, 25% on steel and autos, with different rates by country of origin. So, Averaging import shares and tariff rates separately — rather than computing their product at the commodity level — introduces an upward bias in the predicted price effect. 

Yale's tracker *does* use commodity-level tariff rates through the Leontief in one place: the **employment index**, where the exposure of industry $j$ is $\sum_i \Delta\tau_i \cdot L_{ij} \cdot m_i$ — the same structure as this repo's $\hat{p}_j$.  But this commodity-level propagation is **not** used in their price passthrough calculation, which remains aggregate.

| | This Repo | Yale Tracker |
|---|---|---|
| **Tariff rates in Leontief** | Per-commodity $\Delta\tau_i$ inside the sum: $\hat{p}_j = \sum_i (m_i \cdot \Delta\tau_i) \cdot L_{ij}$ | Collapsed to scalar outside the sum: $\hat{p}^{\text{Yale}} = \overline{\Delta\tau} \cdot \bar{s}$ |
| **Output** | Per-commodity predicted price effect $\hat{p}_j$, bridged to per-category $\hat{P}_k$ | Single aggregate predicted price effect $\hat{p}^{\text{Yale}}$ |
| **Sensitivity to tariff composition** | Yes — different tariff mixes produce different predictions | No — only the average rate matters |

---

## 4. PCE Bridge Aggregation

This repo: [`pipeline.py:step6_pce_effect()`](code/pipeline.py#L319) lines 364–381 | Yale: [`import_price_index.R` §3](https://github.com/Budget-Lab-Yale/tariff-impact-tracker/blob/main/R/import_price_index.R)

| | This Repo | Yale Tracker |
|---|---|---|
| **Bridge source** | BEA `PCEBridge_Summary.xlsx` (fetched at runtime, configurable year) | BEA `PCEBridge_Summary.xlsx` (static Excel, 2024) |
| **Numerator weight** | Producers' value (constant dollar) or purchasers' value (constant percent) | Not used for per-category prediction — used only to map import content to PCE categories |
| **Denominator** | Purchasers' value per PCE category | Total purchasers' value (for expenditure-weighted averaging) |
| **Output** | Per-category predicted tariff effect: $\hat{P}_k = \frac{\sum_i \hat{p}_i \cdot B_{ik}}{\sum_i B_{ik}}$ (using producers' value for $B_{ik}$ numerator, purchasers' value denominator) | Per-category import content share: $s_k = \frac{\sum_i \tilde{m}_i \cdot |B_{ik}|}{\sum_i |B_{ik}|}$ (purchasers' value for $B_{ik}$) |
| **Number of categories** | 27 core goods (food and energy excluded in [`config.py`](code/config.py#L148)) | 32 total PCE goods defined, of which 5 are food/energy; core goods subset = 27 (same categories) |

Both repos work with the same 27 core goods PCE categories. Yale defines all 32 goods categories (including food and energy) and filters at runtime via an `is_food_energy` flag; this repo defines the 27 core goods directly. A few items are classified differently between durable and nondurable (e.g., recreational books, luggage), but the overall core goods set is the same.

This repo produces a **predicted price effect** for each PCE category — a number in percentage points. Yale produces an **import content weight** for each category — used to weight a price index, not as a prediction to compare against data.

Note a subtle difference in the bridge weighting: this repo (under constant dollar markup) uses producers' value for $B_{ik}$ in the numerator and purchasers' value in the denominator, so distribution margins dilute the tariff effect. Yale uses purchasers' value for $B_{ik}$ in both numerator and denominator for $s_k$, which is equivalent to a constant-percent markup assumption for the purpose of computing import content shares.

---

## 5. Comparison to Actual Data

This is where the methodologies diverge most sharply.

### This Repo: Cross-Category Scatter

Source: [`pipeline.py:step7_excess_inflation()`](code/pipeline.py#L826) + [`parse-bea-io-final.ipynb`](code/parse-bea-io-final.ipynb) cells 12–13 | Output: [`data-output/tariff_vs_excess_contribution_2024-12_to_2025-12.csv`](data-output/tariff_vs_excess_contribution_2024-12_to_2025-12.csv)

1. For each of the 27 core goods PCE categories, compute:
   - **X-axis**: predicted tariff effect $\hat{P}_k$ from the IO pipeline (Sections 1–4)
   - **Y-axis**: excess inflation = actual growth over the current window minus mean growth over a pre-tariff baseline window (e.g., 2015–2019 trend)
2. Plot all 27 categories in a scatter, weighted by PCE expenditure share.
3. Fit a WLS regression. Under the hypothesis that the IO model is correct, the slope should be ~1 and R² should be positive.
4. **Result**: The WLS slope is **-0.49** — not just zero, but negative. Categories with higher predicted tariff exposure actually tended to see *less* excess inflation than the model predicts. The relationship runs in the wrong direction.

### Yale Tracker: Aggregate Predicted Effect vs. Import-Weighted Price Index

Source: [`import_price_index.R`](https://github.com/Budget-Lab-Yale/tariff-impact-tracker/blob/main/R/import_price_index.R) + [`report_setup.R`](https://github.com/Budget-Lab-Yale/tariff-impact-tracker/blob/main/R/report_setup.R) lines 880–960

**Predicted side.** Sections 1–4 above culminate in a single aggregate predicted price effect:

$$\hat{p}^{\text{Yale}} = \overline{\Delta\tau} \cdot \bar{s}$$

where $\overline{\Delta\tau} = \sum_i v_i \cdot \Delta\tau_i$ (customs-value-weighted average tariff change, Section 2) and $\bar{s} = \sum_k e_k \cdot s_k$ (expenditure-weighted average import content, Section 4). This is one number — no per-commodity tariff variation survives to this point.

**Observed side.** Yale constructs an import-content-weighted price index to measure how much prices actually moved in import-heavy categories:

1. Use $s_k$ (per-category import content share, from Section 4) as a weight on observed BEA price indices $P_{k,t}$ (from Haver), combined with expenditure $e_k$: $I_t = \sum_k (s_k \cdot e_k) \cdot P_{k,t} / \sum_k (s_k \cdot e_k)$. Categories with higher import content get more weight. This index does not use tariff rates — it uses only the import-content structure from the IO tables and observed prices.

2. Estimate a pre-2025 trend for $I_t$ (local projection or log-linear) and measure how far the index has risen above it.

**Comparison.** Implied passthrough = deviation of $I_t$ from trend / $\hat{p}^{\text{Yale}}$. Result: 40–76% depending on the trend method. They interpret this as partial but meaningful tariff passthrough.

An important contrast with this repo: $\hat{P}_k$ carries commodity-specific $\Delta\tau_i$ propagated through the Leontif matrix $L_{ij}$ and is compared against **actual** inflation **category by category**. Yale's $\hat{p}^{\text{Yale}}$ is a single scalar compared against a single import-content-weighted "price" index, $I_t$. Yale never produces per-category predicted price effects to compare against per-category actual inflation.

---

## 6. Summary of Shared vs. Different Elements

| Pipeline Step | Shared? | Notes |
|---|---|---|
| Import shares from BEA | Essentially the same | Minor denominator difference (supply vs. use) |
| Leontief inverse | Same | Both use BEA's pre-computed total requirements |
| Tariff rates from Census | Same concept | Different source files (Census parquet vs. USITC Excel), same calculation |
| NAICS → BEA concordance | Similar | Independent implementations, same mapping goal |
| Tariff-weighted Leontief propagation | **Different** | This repo computes $\hat{p}_j = \sum_i (m_i \cdot \Delta\tau_i) \cdot L_{ij}$; Yale collapses to $\hat{p}^{\text{Yale}} = \overline{\Delta\tau} \cdot \bar{s}$ |
| PCE bridge | Same source | This repo produces per-category predictions; Yale produces per-category weights |
| Comparison to data | **Fundamentally different** | Cross-category scatter vs. aggregate index ratio |

---

## References

- Minton, R. and M. Somale (2025). "Detecting Tariff Effects on Consumer Prices in Real Time." FEDS Notes, Federal Reserve.
- The Budget Lab at Yale (2026). "One Year of Tariff Analysis: What We Got Right, What Changed, and What We Learned." April 2, 2026.
- The Budget Lab at Yale (2026). "Tracking the Economic Effects of Tariffs." [tariff-impact-tracker repo](https://github.com/Budget-Lab-Yale/tariff-impact-tracker).
- Barbiero, O. and S. Stein (2025). "The Impact of Tariffs on Inflation." Boston Fed Current Policy Perspectives.
- Sangani, K. (2024). "Pass-Through in Levels and the Incidence of Commodity Shocks." SSRN Working Paper 4574233.
