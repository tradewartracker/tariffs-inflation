# Tariff Pass-Through to PCE Prices: Detail (402-Commodity) Methodology

## Overview

This document describes the **detail pipeline**, which uses BEA's 402-commodity benchmark-year IO tables to compute the predicted effect of tariff changes on PCE prices. The methodology is identical in algebra to the summary pipeline (see [tariff_pce_methodology.md](tariff_pce_methodology.md)) but operates at roughly 6× higher commodity resolution. The summary pipeline uses 71 summary-level industries accessible via the BEA API; the detail pipeline uses 402 commodity codes available only as Excel downloads from BEA's static file archives.

The primary motivation for the detail pipeline is to resolve **aggregation bias** in the summary tables. The aggregate core goods predicted effect is correspondingly affected: the detail pipeline yields **2.2%** compared to the summary pipeline's **2.4%**.

The approach follows the same literature: Minton and Somale (2025, Federal Reserve FEDS Note), Barbiero and Stein (2025, Boston Fed), and The Budget Lab at Yale. TBL and the Boston Fed both use detail-level IO tables.

---

## Step 1 — Direct Import Share per Commodity

$$m_i = \frac{\text{MCIF}_i}{\text{T013}_i}$$

For each of the 402 BEA detail commodities $i$, we compute the share of total domestic supply that comes from imports. Both values are drawn from the **Supply table** (`Supply_2017_DET.xlsx`), where `MCIF` is imports valued at cost-insurance-freight and `T013` is total commodity supply (domestic production plus imports). This captures the **direct** exposure of each commodity to import tariffs.

At the detail level, this produces a richer picture than the summary tables. For example, motor vehicles splits into:

| Commodity | Code | Direct import share |
|---|---|---|
| Automobile manufacturing | 336111 | 66.9% |
| Light truck and utility vehicle manufacturing | 336112 | 37.4% |
| Heavy duty truck manufacturing | 336120 | 34.1% |

At the summary level, these are averaged into a single 33.8% figure for `3361MV`.

**Data source:** `Supply_2017_DET.xlsx` from `AllTablesSUP.zip`, sheet `2017`. Contains ~403 commodity rows.

---

## Steps 2–3 — Pre-Computed Leontief Inverse

$$L = (I - B \cdot D)^{-1}$$

Unlike the summary pipeline, which constructs $A$ from the Use table and inverts $(I - A)$, the detail pipeline uses BEA's **pre-computed** Commodity-by-Commodity Total Requirements matrix. This is the proper Leontief inverse that accounts for the Make/Use framework — BEA constructs the market share matrix $D$ from the Make table and the commodity input coefficients $B$ from the Use table, then inverts $(I - B \cdot D)$ to produce $L$.

No matrix inversion is performed in the pipeline. The Leontief matrix $L$ is read directly from `CxC_TR_2017_PRO_DET.xlsx` as a $402 \times 402$ matrix at producer prices. Each element $L_{ij}$ gives the total output of commodity $i$ required — directly and through all upstream supply chain stages — to deliver one dollar of final output of commodity $j$.

Diagnostics: diagonal elements range from 1.000 to 1.745 (mean 1.08), confirming each commodity requires at least itself. All off-diagonal elements are non-negative.

**Data source:** `CxC_TR_2017_PRO_DET.xlsx` from `AllTablesSUP.zip`, sheet `2017`. 402 × 402 matrix.

---

## Step 4 — Total Import Content per Dollar of Output

$$\tilde{m}_j = \sum_i m_i \cdot L_{ij}$$

This is the vector $m^\prime L$. For each commodity $j$, it aggregates the import content embedded at every stage of its supply chain. Compared to the direct import share $m_j$, the total import content $\tilde{m}_j$ is always weakly larger, as it includes all upstream import linkages.

At the detail level, the mean direct import share across 402 commodities is 15.4%, and the mean total import content is 28.0%, implying a supply-chain amplification factor of 1.8×. This is comparable to the 2.2× amplification at the summary level (which reflects fewer, more heterogeneous industry bundles).

---

## Step 5 — Predicted Tariff Effect per Commodity

$$\hat{p}_j = \sum_i (m_i \cdot \Delta\tau_i) \cdot L_{ij}$$

The tariff propagation algebra is identical to the summary pipeline. We weight the direct import shares by the **change** in the tariff rate $\Delta\tau_i$ for each commodity before propagating through the Leontief inverse. This gives the predicted price increase per dollar of output for commodity $j$ attributable to the tariff change.

### NAICS → Detail Concordance

The concordance step differs from the summary pipeline. Census tariff data is at the 6-digit NAICS level, and these must be mapped to BEA's 402-commodity detail codes. We parse BEA's official `BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx`, which lists NAICS codes at varying digit levels (3 to 6 digits) alongside their BEA detail commodity assignments.

The matching uses **longest-prefix logic**: for each 6-digit NAICS code in the tariff data, we try prefixes from length 6 down to 2, returning the BEA detail code whose NAICS prefix is the longest match. This handles the fact that BEA's concordance maps at mixed levels of specificity (e.g., `3361` for motor vehicle manufacturing, `33611` for automobile and light truck manufacturing).

Coverage: 374 of 388 NAICS6 codes (84–85% of total import value) map successfully to BEA detail commodities, covering 235 distinct BEA detail codes. Unmapped codes are primarily services and non-merchandise imports.

Effective tariff rates are constructed identically to the summary pipeline: total duties divided by total imports at the NAICS6 level, aggregated to BEA detail commodity codes using import-weighted averages. The baseline is the annual average effective rate over the chosen year (all twelve months pooled); the current rate is a single month.

---

## Step 6 — PCE Bridge Aggregation

The **detail PCE bridge** (`PCEBridge_Detail.xlsx`) maps 402 BEA commodity codes to approximately 212 PCE consumption categories, recording producers' value, transport costs, wholesale and retail margins, and purchasers' value for each commodity-category pair (~704 rows for the 2017 sheet).

The aggregation formula is identical to the summary pipeline:

### Case 1 — Constant Dollar Markup

$$\hat{P}_k = \frac{\sum_j \hat{p}_j \cdot PV_{jk}}{\sum_j PUV_{jk}}$$

where $PV$ = producers' value and $PUV$ = purchasers' value.

### Case 2 — Constant Percent Markup

$$\hat{P}_k = \frac{\sum_j \hat{p}_j \cdot PUV_{jk}}{\sum_j PUV_{jk}}$$

The key difference from the summary pipeline is the **granularity of the bridge**. At the summary level, the PCE bridge maps ~71 industries to ~150 entries; at the detail level, it maps ~402 commodities to ~704 entries across ~212 PCE categories. This means a single summary PCE category like "New motor vehicles" — which at the summary level receives a single predicted effect from the bundled `3361MV` industry — now receives contributions from multiple detail commodities:

| Detail PCE category | Commodity | Predicted effect | Producers' value ($M) |
|---|---|---|---|
| New domestic autos | 336111 | 1.0% | 14,955 |
| New foreign autos | 336111 | 1.0% | 5,233 |
| New light trucks | 336112 | 2.4% | 136,403 |

These detail categories are then aggregated to the summary "New motor vehicles" category using purchasers'-value weighting, yielding a predicted effect of **2.0%** — compared to **5.0%** from the summary pipeline. The difference is entirely driven by the disaggregation: at the detail level, the tariff effects flowing through automobile assembly vs. light truck assembly are properly distinguished rather than averaged.

### Aggregation to Summary Categories

The detail PCE bridge produces ~212 categories, but the counterfactual inflation analysis (Step 7) and the NIPA price index data use the 27 summary-level core goods categories defined in `code/config.py`. We therefore aggregate the detail-level predicted effects to summary categories using a mapping (`DETAIL_TO_SUMMARY_PCE` in `code/pipeline_detail.py`), weighted by purchasers' value:

$$\hat{P}_K = \frac{\sum_{k \in K} \hat{P}_k \cdot PUV_k}{\sum_{k \in K} PUV_k}$$

where $K$ is the set of detail categories that roll up to summary category $K$.

---

## Worked Example: New Motor Vehicles

To make the methodology concrete, we trace through the full chain for the "New motor vehicles" PCE category using 2017 BEA detail data and Census tariff data comparing December 2025 to the 2024 annual baseline.

### The aggregation problem

At the summary level, new motor vehicles maps to a single BEA industry — `3361MV` (Motor vehicles, bodies and trailers, and parts). This industry has a direct import share of 33.8% and total import content (after Leontief) of 80.4%. A tariff increase of 12.5 pp on this industry produces a predicted consumer price effect of **5.0%**.

At the detail level, the same economic activity is decomposed into three separate commodities, each with its own import share, supply-chain linkages, and tariff exposure:

### Step 1 — Direct import shares

| Commodity | Code | Direct import share |
|---|---|---|
| Automobile manufacturing | 336111 | 66.9% |
| Light truck and utility vehicle mfg | 336112 | 37.4% |
| Heavy duty truck manufacturing | 336120 | 34.1% |

Automobile manufacturing has a very high direct import share (66.9%) because a large fraction of automobiles sold in the U.S. are manufactured abroad and imported as finished vehicles. Light trucks are predominantly manufactured domestically, yielding a lower 37.4%.

### Steps 2–3 — Total import content after Leontief

| Commodity | Code | Direct | Total | Amplification |
|---|---|---|---|---|
| Automobile manufacturing | 336111 | 66.9% | 96.8% | 1.45× |
| Light truck and utility vehicle mfg | 336112 | 37.4% | 67.3% | 1.80× |
| Heavy duty truck manufacturing | 336120 | 34.1% | 67.9% | 1.99× |

The Leontief inverse captures upstream import content — steel, aluminum, electronics, rubber, and chemicals that go into domestically assembled vehicles. The amplification is smaller for automobile manufacturing (1.45×) because the direct import share is already very high (most of the import content is the finished vehicle itself); for light and heavy trucks, the amplification is larger because more of their import content comes indirectly through domestically produced components.

### Step 4 — Predicted producer-level effects

| Commodity | Code | Producer effect |
|---|---|---|
| Automobile manufacturing | 336111 | 3.5% |
| Light truck and utility vehicle mfg | 336112 | 3.6% |
| Heavy duty truck manufacturing | 336120 | 9.8% |

Despite having no direct tariff (no NAICS6 codes map to 336111 or 336112 through the concordance), automobile and light truck manufacturing still face a 3.5–3.6% predicted producer price increase entirely through **upstream tariffed inputs** propagated via the Leontief inverse. Heavy trucks face a direct tariff increase of 15.7 pp and consequently show a larger 9.8% producer effect.

### Step 5 — PCE bridge aggregation

The detail PCE bridge routes these commodities to sub-categories of "New motor vehicles":

| Detail PCE category | Source commodity | Predicted effect | Prod. value ($M) | Purch. value ($M) | Margin |
|---|---|---|---|---|---|
| New domestic autos | 336111 | 1.0% | 14,955 | 51,958 | 71.2% |
| New foreign autos | 336111 | 1.0% | 5,233 | 18,343 | 71.5% |
| New light trucks | 336112 | 2.4% | 136,403 | 210,429 | 35.2% |

Under the constant dollar markup assumption, the 3.5% producer-level effect for automobiles is diluted to 1.0% at the consumer level because dealer margins account for over 70% of what consumers pay. Light trucks have lower margins (35.2%), so the 3.6% producer effect is diluted less, to 2.4%.

Aggregating these detail categories to the summary "New motor vehicles" category (weighted by purchasers' value):

$$\hat{P}_{\text{new vehicles}} = \frac{0.010 \times 51{,}958 + 0.010 \times 18{,}343 + 0.024 \times 210{,}429}{51{,}958 + 18{,}343 + 210{,}429} = \mathbf{2.0\%}$$

This is less than half the summary pipeline's 5.0% estimate, demonstrating the impact of disaggregation.

---

## Data Sources

| Input | Source | File |
|---|---|---|
| Import shares per commodity | BEA Supply Table (detail, 2017) | `Supply_2017_DET.xlsx` |
| Leontief inverse (402×402) | BEA CxC Total Requirements (detail, 2017) | `CxC_TR_2017_PRO_DET.xlsx` |
| PCE bridge (commodity → PCE) | BEA PCE Bridge (detail, 2017) | `PCEBridge_Detail.xlsx` |
| NAICS → BEA detail concordance | BEA official concordance | `BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx` |
| Tariff rate changes | Census imports & duties | NAICS6 → BEA detail concordance; Δτ = current month minus baseline annual average |

All detail IO files are from the 2017 benchmark year — the only year for which BEA publishes detail-level tables. They are downloaded once via `code/download_detail_data.py` from:
- `https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesSUP.zip` (Supply table and CxC Total Requirements)
- `https://apps.bea.gov/industry/release/xlsx/PCEBridge_Detail.xlsx`

---

## Key Assumptions

1. **Full pass-through**: Import prices rise by the full tariff amount at the port of entry.
2. **Constant dollar markups**: Retailers and wholesalers maintain constant dollar (not percent) markups, so margins do not amplify the tariff effect.
3. **Fixed import content**: First-order approximation; does not capture substitution away from tariffed imports.
4. **No retaliation**: Only US-imposed tariffs are included; retaliatory tariffs are not modeled.
5. **2017 IO structure**: The detail tables reflect 2017 production patterns and input requirements. Industry structure may have shifted since then (e.g., electric vehicle production, semiconductor reshoring). The summary pipeline uses more recent tables (2022) but at lower resolution.

---

## Step 7 — Counterfactual Inflation

Step 7 is identical to the summary pipeline and is documented in [tariff_pce_methodology.md](tariff_pce_methodology.md) §7. After aggregating the detail-level PCE effects to the 27 summary core goods categories, the same counterfactual inflation functions are used.

The only methodological difference is that the **PCE spending weights** used for the aggregate core goods effect come from the 2017 detail bridge (reflecting 2017 spending patterns) rather than the 2022 summary bridge. For constructing the core goods share of total PCE — needed for the headline PCE counterfactual — the summary bridge from the BEA API is used, as it includes services categories not present in the detail bridge.

---

## Detail vs. Summary Pipeline: Comparison

| Dimension | Summary pipeline | Detail pipeline |
|---|---|---|
| IO resolution | 71 industries | 402 commodities |
| IO year | 2022 (or any 1997–2023) | 2017 only (benchmark) |
| Data access | BEA API (runtime) | Excel downloads (cached) |
| Leontief construction | Computed: $(I - A)^{-1}$ from Use table | Pre-computed by BEA: $(I - BD)^{-1}$ |
| PCE bridge entries | ~150 rows | ~704 rows, ~212 categories |
| Concordance | NAICS6 → 71 industries | NAICS6 → 402 commodities (longest-prefix) |
| Core goods effect | 2.4% | 2.2% |
| Motor vehicles total import content | 80.4% (single industry) | 67–97% (3 separate commodities) |
| Motor vehicles predicted PCE effect | 5.0% | 2.0% |

The aggregate core goods effect is similar between the two pipelines (within 0.3 pp), but category-level estimates diverge substantially for industries with heterogeneous sub-commodities. The detail pipeline is preferred for category-level analysis; the summary pipeline is preferred for time-series analysis (annual tables from 1997–2023) and for its simpler data requirements.

---

## References

Minton, Robert, and Mariano Somale (2025). "Detecting Tariff Effects on Consumer Prices in Real Time," *FEDS Notes*. Board of Governors of the Federal Reserve System, May 09, 2025.

Barbiero, Omar, and Samuel Stein (2025). "The Direct Effect of Recent Tariff Increases on US Prices," *Current Policy Perspectives*. Federal Reserve Bank of Boston.

The Budget Lab at Yale (2026). "Tracking the Economic Effects of Tariffs," February 18, 2026. https://budgetlab.yale.edu/research/tracking-economic-effects-tariffs

The Budget Lab at Yale (2026). "Methodological Appendix for Tracking the Economic Effects of Tariffs," February 17, 2026. https://budgetlab.yale.edu/research/methodological-appendix-tracking-economic-effects-tariffs
