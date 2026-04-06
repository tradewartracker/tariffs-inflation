# Methodology Comparison: This Repo vs. Yale Budget Lab

A step-by-step comparison of the tariff-to-inflation pipeline in this repository with the Yale Budget Lab's [tariff-impact-tracker](https://github.com/Budget-Lab-Yale/tariff-impact-tracker) and their [retrospective analysis](https://budgetlab.yale.edu/research/one-year-tariff-analysis-what-we-got-right-what-changed-and-what-we-learned) (April 2, 2026).

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
| **Formula** | $\tilde{m}_j = \sum_i m_i \cdot L_{ij}$ (i.e., $m'L$) | $\text{total\_import}_c = \sum_j R_{c,j} \times m_j$ (i.e., $Rm$) |
| **Interpretation** | Total import content embedded in one dollar of industry $j$'s output, via all upstream tiers | Same — total import content of commodity $c$ including supply-chain linkages |

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

Both compute $\Delta\tau = \tau_\text{current} - \tau_\text{baseline}$ per commodity, using actual duties collected (not statutory rates). The concordance mapping is similar but implemented independently.

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

But then uses these as static weights for a price index. For the passthrough denominator — the predicted effect against which actual prices are compared — it multiplies a **single aggregate** $\Delta\tau$ by a **single aggregate** import share:

```
expected_core = tariff_increase * IMPORT_SHARE_CORE_GOODS
```

This is equivalent to: $\hat{p} = \Delta\tau \cdot \sum_i m_i \cdot L_{ij}$, i.e., the tariff rate is factored *outside* the sum. All commodities are treated as facing the same tariff rate.

### Why the Distinction Matters

If tariff rates were uniform across commodities, the two approaches would be identical — $\Delta\tau$ factors out. But 2025 tariff rates varied enormously: near-zero on pharmaceuticals, ~5% on some electronics, 25% on steel and autos, with different rates by country of origin. With this much cross-commodity variation, putting $\Delta\tau_i$ inside vs. outside the Leontief sum produces meaningfully different per-industry predictions. An industry that sources heavily from high-tariff inputs (steel-intensive manufacturing) gets a different prediction than one sourcing from low-tariff inputs (pharma ingredients), even if both have similar total import content.

### A Partial Exception

Yale's tracker *does* use commodity-level tariff rates through the Leontief in one place: the **employment index**, where $w_j = \sum_c \tau_c \cdot R_{c,j} \cdot s_c$ — the same structure as this repo's price prediction. And their retrospective article (April 2026) states that the State of Tariffs report now runs "commodity-level ETR shocks through an input-output matrix," following Barbiero & Stein. But this commodity-level propagation is **not** used in their price passthrough calculation, which remains aggregate.

| | This Repo | Yale Tracker |
|---|---|---|
| **Tariff rates in Leontief** | Per-commodity $\Delta\tau_i$ inside the sum | Single aggregate $\Delta\tau$ outside the sum |
| **Output** | Per-industry predicted price effect $\hat{p}_j$ | Per-industry import content weight $\tilde{m}_j$ (tariff-invariant) |
| **Sensitivity to tariff composition** | Yes — different tariff mixes produce different predictions | No — only the average rate matters |

---

## 4. PCE Bridge Aggregation

This repo: [`pipeline.py:step6_pce_effect()`](code/pipeline.py#L319) lines 364–381 | Yale: [`import_price_index.R` §3](https://github.com/Budget-Lab-Yale/tariff-impact-tracker/blob/main/R/import_price_index.R)

| | This Repo | Yale Tracker |
|---|---|---|
| **Bridge source** | BEA `PCEBridge_Summary.xlsx` (fetched at runtime, configurable year) | BEA `PCEBridge_Summary.xlsx` (static Excel, 2024) |
| **Numerator weight** | Producers' value (constant dollar) or purchasers' value (constant percent) | Not used for per-category prediction — used only to map import content to PCE categories |
| **Denominator** | Purchasers' value per PCE category | Total purchasers' value (for expenditure-weighted averaging) |
| **Output** | Per-category predicted tariff effect: $\hat{P}_k = \frac{\sum_j \hat{p}_j \cdot PV_{jk}}{\sum_j PUV_{jk}}$ | Per-category import content share: $s_k = \frac{\sum_j \tilde{m}_j \cdot |PUV_{jk}|}{\sum_j |PUV_{jk}|}$ |
| **Number of categories** | 27 core goods (food and energy excluded in [`config.py`](code/config.py#L148)) | 32 total PCE goods defined, of which 5 are food/energy; core goods subset = 27 (same categories) |

Both repos work with the same 27 core goods PCE categories. Yale defines all 32 goods categories (including food and energy) and filters at runtime via an `is_food_energy` flag; this repo defines the 27 core goods directly. A few items are classified differently between durable and nondurable (e.g., recreational books, luggage), but the overall core goods set is the same.

This repo produces a **predicted price effect** for each PCE category — a number in percentage points. Yale produces an **import content weight** for each category — used to weight a price index, not as a prediction to compare against data.

Note a subtle difference in the bridge weighting: this repo (under constant dollar markup) uses producers' value $PV$ in the numerator and purchasers' value $PUV$ in the denominator, so distribution margins dilute the tariff effect. Yale uses purchasers' value in both numerator and denominator for $s_k$, which is equivalent to a constant-percent markup assumption for the purpose of computing import content shares.

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

### Yale Tracker: Aggregate Imported Price Index

Source: [`import_price_index.R`](https://github.com/Budget-Lab-Yale/tariff-impact-tracker/blob/main/R/import_price_index.R) + [`report_setup.R`](https://github.com/Budget-Lab-Yale/tariff-impact-tracker/blob/main/R/report_setup.R) lines 880–960

1. **Per-category import content share $s_k$** — from Section 1c (Leontief) + Section 4 (PCE bridge). Total import content $\tilde{m}_j$ from the Leontief is mapped to each PCE category $k$ via the bridge: $s_k = \sum_j \tilde{m}_j \cdot |PUV_{jk}| / \sum_j |PUV_{jk}|$ (purchasers'-value-weighted). This is a static weight — it does not depend on tariff rates. It measures how import-exposed category $k$ is.

2. **Import-content-weighted price index** — $s_k$ is combined with nominal PCE expenditure $E_{k,t}$ (from Haver) and BEA price indices $P_{k,t}$ (from Haver) to construct a time-varying weighted index: $I_t = \sum_k w_{k,t} \cdot P_{k,t}$, where $w_{k,t} \propto s_k \cdot E_{k,t}$. Categories with higher import content get more weight. This index is *not* derived from the tariff rate pipeline — it uses only the import-content structure from the IO tables and observed prices from BEA/Haver.

3. **Deviation from trend** — estimate a pre-2025 trend for $I_t$ (local projection or log-linear) and measure how far the index has risen above it.

4. **Expected price effect** — from Section 2, a **single aggregate** $\Delta\tau$ (latest effective tariff rate minus 2022–2024 baseline, for core goods or durables as a broad category) multiplied by a **single aggregate** import share $S$ (expenditure-weighted average of $s_k$ across categories): `expected = Δτ × S`. No per-commodity tariff variation enters here.

5. **Implied passthrough** = deviation from step 3 / expected effect from step 4.

6. **Result**: Passthrough ranges from 40–76% depending on the trend method. They interpret this as partial but meaningful tariff passthrough.

The key contrast: in this repo, $\hat{P}_k$ on the x-axis of the scatter carries commodity-specific tariff rates propagated through the Leontief (Section 3) — it is a per-category *prediction*. In Yale's tracker, $s_k$ is a tariff-invariant import-content weight, and tariff rates enter only as a single aggregate number in the denominator of the passthrough ratio. Yale never produces a per-category predicted price effect to compare against per-category actual inflation.

---

## 6. What Yale Does NOT Do

Yale's tracker does not produce per-category predicted price effects and compare them to per-category observed price changes. The closest they come is reporting import-weighted vs. unweighted aggregate indices and noting that the import-weighted one rose more. But this is a weaker test than the cross-category regression in this repo, because:

1. It collapses 27+ categories into a single number.
2. It cannot identify whether the *right* categories are moving.
3. It is sensitive to a few large categories (motor vehicles, electronics) that dominate the import-weighted index.

Their retrospective article (April 2026) attributes the gap between prediction and reality to "incomplete passthrough" (40–76%). But incomplete passthrough is a **level** adjustment — it scales all predictions down proportionally. It cannot explain why the cross-category correlation is negative. If passthrough were 50% uniformly, the scatter plot slope would be 0.5, not -0.49.

---

## 7. Summary of Shared vs. Different Elements

| Pipeline Step | Shared? | Notes |
|---|---|---|
| Import shares from BEA | Essentially the same | Minor denominator difference (supply vs. use) |
| Leontief inverse | Same | Both use BEA's pre-computed total requirements |
| Tariff rates from Census | Same concept | Different source files (Census parquet vs. USITC Excel), same calculation |
| NAICS → BEA concordance | Similar | Independent implementations, same mapping goal |
| Tariff-weighted Leontief propagation | **Different** | This repo does it; Yale does not propagate $\Delta\tau_i$ through the Leontief |
| PCE bridge | Same source | This repo produces per-category predictions; Yale produces per-category weights |
| Comparison to data | **Fundamentally different** | Cross-category scatter vs. aggregate index ratio |
| What gets tested | **Fundamentally different** | Pattern (relative ranking) vs. level (aggregate magnitude) |

---

## 8. Reconciling the Results

Yale's finding of 40–76% aggregate passthrough and this repo's finding of no cross-category correlation are **not contradictory**. They are measuring different things:

- **Yale**: "Import-heavy goods as a group saw prices rise roughly 40–76% as much as the model predicted." This is consistent with general inflationary pressure during the tariff period that happened to affect import-heavy goods somewhat more, without the specific category-level pattern matching IO predictions.

- **This repo**: "The specific categories the IO model predicts should be hardest-hit are not the categories that actually saw the most inflation." This is a test of whether the tariff → cost → price mechanism is operating at the product level, and it finds no evidence that it is.

The gap between these findings raises the question: if the IO model doesn't get the category-level pattern right, what is driving the aggregate deviation in import-weighted prices? Possible explanations include:

1. **Non-tariff supply shocks** correlated with import exposure (e.g., shipping disruptions, input shortages) that affect import-heavy categories without following the IO-predicted pattern.
2. **Demand shifts** during the tariff period that happen to concentrate in goods-heavy (and therefore import-heavy) categories.
3. **Anticipatory pricing** — firms raising prices broadly in import-exposed sectors regardless of their specific tariff exposure, as a hedge or expectation effect.
4. **Aggregation masking** — a few large categories (motor vehicles, electronics) dominating the import-weighted index and driving the aggregate result.

None of these are the IO mechanism working as theorized. The IO model's specific prediction is that cost pressure follows the supply chain: a tariff on steel should raise prices of steel-intensive goods more than non-steel-intensive goods, proportional to each good's total steel import content. This repo tests that prediction and does not find support for it.

---

## References

- Minton, R. and M. Somale (2025). "Detecting Tariff Effects on Consumer Prices in Real Time." FEDS Notes, Federal Reserve.
- The Budget Lab at Yale (2026). "One Year of Tariff Analysis: What We Got Right, What Changed, and What We Learned." April 2, 2026.
- The Budget Lab at Yale (2026). "Tracking the Economic Effects of Tariffs." [tariff-impact-tracker repo](https://github.com/Budget-Lab-Yale/tariff-impact-tracker).
- Barbiero, O. and S. Stein (2025). "The Impact of Tariffs on Inflation." Boston Fed Current Policy Perspectives.
- Sangani, K. (2024). "Pass-Through in Levels and the Incidence of Commodity Shocks." SSRN Working Paper 4574233.
