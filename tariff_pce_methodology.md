# Tariff Pass-Through to PCE Prices: Methodology

## Overview

We compute the predicted effect of **changes** in import tariffs on Personal Consumption Expenditure (PCE) prices across consumption categories. The approach follows Minton and Somale (2025, Federal Reserve FEDS Note) and combines BEA Input-Output tables, import data, and a PCE bridge table to propagate tariff cost shocks through the full supply chain to consumer prices.

Critically, the analysis uses the **change** in the effective tariff rate relative to a pre-tariff baseline — not the level of the tariff. Using the tariff level would only be appropriate starting from a zero-tariff baseline, which is never the case in practice. Many tariff rates have been in place for years and are already embedded in prices. The relevant question is how much prices change in response to a tariff **increase**.

---

## Step 1 — Direct Import Share per Commodity

$$m_i = \frac{\text{imports}_i}{\text{total supply}_i}$$

For each BEA commodity $i$, we compute the share of total domestic supply that comes from imports. Imports and total supply are drawn from BEA Supply Table (TableID 262). This captures the **direct** exposure of each commodity to import tariffs.

---

## Step 2 — Technical Coefficients Matrix

$$A_{ij} = \frac{\text{use of commodity } i \text{ by industry } j}{\text{gross output of industry } j}$$

From the BEA Use Table (TableID 259), we construct the $n \times n$ matrix $A$ where each element $A_{ij}$ is the dollar value of commodity $i$ required to produce one dollar of output in industry $j$. This describes the direct input requirements of each industry.

---

## Step 3 — Leontief Inverse

$$L = (I - A)^{-1}$$

We invert the matrix $(I - A)$ to obtain the Leontief inverse $L$. Each element $L_{ij}$ gives the **total** output of commodity $i$ required — directly and indirectly through all upstream supply chain stages — to deliver one dollar of final output of industry $j$. This is the key step that captures the full propagation of cost shocks through the economy.

---

## Step 4 — Total Import Content per Dollar of Output

$$\tilde{m}_j = \sum_i m_i \cdot L_{ij}$$

This is the vector $m^\prime L$. For each industry $j$, it aggregates the import content embedded at every stage of its supply chain. Compared to the direct import share $m_j$, the total import content $\tilde{m}_j$ is always weakly larger, as it includes all upstream import linkages.

---

## Step 5 — Predicted Tariff Effect per Industry

$$\hat{p}_j = \sum_i (m_i \cdot \Delta\tau_i) \cdot L_{ij}$$

We weight the direct import shares by the **change** in the tariff rate $\Delta\tau_i = \tau_i^{\text{current}} - \tau_i^{\text{base}}$ for each commodity before propagating through the Leontief inverse. This gives the predicted **price increase per dollar of output** for industry $j$ attributable to the tariff change, under the assumption of full pass-through and constant dollar markups.

Effective tariff rates are constructed as total duties divided by total imports at the NAICS6 level from Census data, then aggregated to BEA IO codes via a NAICS6 $\to$ BEA concordance. The baseline is the annual average effective rate over 2024 (summing duties and imports across all twelve months before dividing, so that larger trade months are naturally upweighted). The current rate is the effective rate for the target month. The difference $\Delta\tau_i$ is computed via an explicit merge on BEA code — not positional subtraction — to guard against row-order mismatches when coverage differs between periods.

---

## Step 6 — PCE Bridge Aggregation

The BEA PCE Bridge table maps each BEA commodity $j$ to one or more PCE consumption categories $k$, recording both the **producers' value** (the price at the factory gate, before distribution margins) and the **purchasers' value** (what consumers actually pay, inclusive of wholesale, retail, and transportation margins). The choice of which value to use in the numerator weighting reflects a key assumption about how retailers and wholesalers respond to the tariff shock.

### Case 1 — Constant Dollar Markup

$$\hat{P}_k = \frac{\sum_j \hat{p}_j \cdot PV_{jk}}{\sum_j PUV_{jk}}$$

where $PV$ = producers' value and $PUV$ = purchasers' value.

Under this assumption, retailers and wholesalers add a fixed dollar margin that does not respond to the tariff. If a good costs \$80 at producer prices with a \$20 retail margin, and a tariff raises the producer price by \$8 (10%), the consumer price rises by \$8 to \$108 — the \$20 margin is unchanged. The tariff effect as a share of the consumer price is \$8/\$100 = 8%, which is less than 10% because the fixed margin dilutes it. Weighting by **producers' value** in the numerator correctly captures only the tariff-exposed portion of consumer spending. This is the assumption used by Minton and Somale (2025) and is considered the conservative baseline.

### Case 2 — Constant Percent Markup

$$\hat{P}_k = \frac{\sum_j \hat{p}_j \cdot PUV_{jk}}{\sum_j PUV_{jk}} = \sum_j \hat{p}_j \cdot w_{jk}$$

where $w_{jk} = PUV_{jk} / \sum_j PUV_{jk}$ are expenditure shares. Under this assumption, retailers maintain a fixed percentage margin. If the retailer maintains a 25% markup, a 10% rise in producer price passes through fully as a 10% rise in consumer price — the margin scales up proportionally. Weighting by **purchasers' value** in the numerator is therefore appropriate, as the margins are carried along with the tariff shock. This assumption produces larger predicted price effects than the constant dollar case.

The difference between the two cases is largest for categories with high distribution margins, such as food, apparel, and furniture, where retail and wholesale margins can account for 30–50% of purchasers' value. Empirically, Sangani (2024) argues that dollar markup adjustment is the more common firm behavior, supporting the constant dollar assumption.

The result $\hat{P}_k$ is the **predicted percent increase in the price of PCE category $k$** attributable to the tariffs.

---

## Worked Example: New Motor Vehicles

To make the methodology concrete, we trace through the full chain for the "New motor vehicles" PCE category using 2022 BEA data and Census tariff data comparing December 2025 to the 2024 annual baseline.

**Setup:** The new motor vehicles PCE category maps to a single BEA commodity — `3361MV` (Motor vehicles, bodies and trailers, and parts). The **change** in the effective tariff rate on this commodity from the 2024 baseline to December 2025, constructed from Census duties/imports data aggregated via our NAICS6 → BEA concordance, is **12.5 percentage points**. This is the increase in the import-weighted average tariff actually collected at the border — lower than the statutory 25% increase because not all motor vehicle imports face the full rate due to exemptions, country-specific rates, and product mix.

**Step 1 — Direct import share: 33.8%**
Of the total domestic supply of motor vehicles, 33.8% comes directly from imports. Roughly one in three dollars of motor vehicle supply at the border is foreign-made.

**Step 2 & 3 — Total import content after Leontief: 80.4%**
After tracing all upstream supply chain inputs — steel, aluminum, electronics, rubber, chemicals that go into making cars domestically — the total import content rises from 33.8% to 80.4%. This is the Leontief amplification: even "domestic" cars are heavily import-dependent through their inputs. The gap between 33.8% and 80.4% represents the indirect import content embedded in domestically produced components.

**Step 4 — Predicted tariff effect at producer level: 9.3%**
The predicted price increase per dollar of motor vehicle output is 9.3%. This is not simply $80.4\% \times 12.5\%$ — it reflects the full Leontief propagation of tariff-weighted import shares across all upstream commodities, each with their own tariff rate and import share. Steel, rubber, and electronics inputs all face their own tariffs, and those costs propagate forward into the vehicle price.

**Step 5 — PCE bridge aggregation: 5.0%**
The final step converts the producer-level effect to a consumer-price effect. From the PCE bridge:

| | Value (\$M) |
|---|---|
| Producers' value | 201,291 |
| Purchasers' value | 375,081 |
| Margins (wholesale + retail + transport) | 173,790 |

Margins account for **46.3%** of what consumers pay. Under the constant dollar markup assumption, these margins do not respond to the tariff — retailers keep their dollar margin fixed. The tariff effect is therefore diluted when expressed as a share of the consumer price:

$$\hat{P}_{\text{new vehicles}} = \frac{0.0930 \times 201{,}291}{375{,}081} = \mathbf{5.0\%}$$

Intuitively: the producer-level effect is 9.3%, but consumers pay roughly twice what producers receive (purchasers' value is 1.86× producers' value), and the extra half — the distribution margins — doesn't move. So the predicted consumer price effect is roughly half the producer-level effect.

---

## Data Sources

| Input | Source | BEA Table |
|---|---|---|
| Imports by commodity | BEA Supply Table | TableID 262 |
| Total supply by commodity | BEA Supply Table | TableID 262 |
| Intermediate use matrix | BEA Use Table | TableID 259 |
| Gross output by industry | BEA Use Table (row T018) | TableID 259 |
| PCE bridge | BEA PCEBridge_Summary.xlsx | 1997–2024 |
| Tariff rate changes | Census imports & duties | NAICS6 → BEA concordance; $\Delta\tau$ = December 2025 minus 2024 annual average |

---

## Key Assumptions

1. **Full pass-through**: Import prices rise by the full tariff amount at the port of entry.
2. **Constant dollar markups**: Retailers and wholesalers maintain constant dollar (not percent) markups, so margins do not amplify the tariff effect.
3. **Fixed import content**: First-order approximation; does not capture substitution away from tariffed imports.
4. **No retaliation**: Only US-imposed tariffs are included; retaliatory tariffs are not modeled.

---

## Step 7 — Counterfactual Inflation: Tariff Contribution to Core and Core Goods PCE

Having computed the predicted tariff contribution $\hat{P}_k$ for each PCE category, we can construct a counterfactual inflation path — what inflation would have been absent the tariff increases. The logic is simple: actual observed inflation over a given window equals the no-tariff counterfactual plus the tariff contribution. Rearranging gives the counterfactual.

### 7.1 — Actual Inflation

We obtain realized PCE price indexes from BEA NIPA tables. The choice of table depends on the desired frequency and aggregation level:

- **Aggregate core PCE (monthly):** NIPA Table T20804 publishes monthly price indexes by major type of product, including the series `PCE excluding food and energy`. This is available through the BEA API with one-month lag.
- **Individual PCE categories (quarterly):** NIPA Table T20404 publishes quarterly price indexes at the detailed product level (111 series). Category names in this table include BEA line numbers in parentheses (e.g., `New motor vehicles (55)`) and require a crosswalk to match our 27 core goods categories.

For a given baseline period $t_0$ and current period $t_1$, actual inflation for category $k$ is:

$$\pi_k^{\text{actual}} = \frac{P_k^{t_1} - P_k^{t_0}}{P_k^{t_0}}$$

The baseline period $t_0$ should be chosen as the last period **before** the tariff changes took effect. For the 2025 tariff episode, we use **2024Q4** as the baseline (quarterly) or **January 2025** (monthly), just prior to the February–March 2025 tariff announcements.

### 7.2 — Counterfactual Core PCE Inflation

For aggregate core PCE (goods + services), the predicted tariff contribution must account for the fact that services have near-zero direct tariff exposure. The tariff effect therefore enters core PCE only through the core goods component:

$$\hat{\Pi}^{\text{tariff}}_{\text{core PCE}} = \hat{P}_{\text{core goods}} \times s_{\text{core goods}}$$

where $s_{\text{core goods}} = \sum_{k \in \text{core goods}} \text{PCE}_k / \sum_{\text{all}} \text{PCE}_k$ is the share of core goods in total PCE spending (from the PCE bridge, ~17%). The counterfactual is then:

$$\pi^{\text{no tariff}}_{\text{core PCE}} = \pi^{\text{actual}}_{\text{core PCE}} - \hat{\Pi}^{\text{tariff}}_{\text{core PCE}}$$

### 7.3 — Counterfactual Core Goods Inflation

For core goods specifically, we construct a bottom-up weighted price index directly from the 27 individual category price series from T20404, using PCE bridge purchasers' values as weights:

$$P^t_{\text{core goods}} = \frac{\sum_{k \in \text{core goods}} w_k \cdot P_k^t}{\sum_{k \in \text{core goods}} w_k}$$

where $w_k$ is the 2022 purchasers' value for category $k$ from the PCE bridge. This is preferred over using the broad BEA durable/nondurable aggregates because those include food and energy, which we exclude from core goods.

The counterfactual is then:

$$\pi^{\text{no tariff}}_{\text{core goods}} = \pi^{\text{actual}}_{\text{core goods}} - \hat{P}_{\text{core goods}}$$

where $\hat{P}_{\text{core goods}}$ is the spending-weighted average of predicted tariff effects across the 27 core goods categories from Step 6.

### 7.4 — Key Assumptions and Caveats

1. **Full pass-through:** The predicted tariff contribution $\hat{P}_k$ assumes 100% pass-through from the border to consumer prices. Empirically, Minton and Somale (2025) estimate realized pass-through of approximately 54% for the 2025 tariff episode. The counterfactual as computed here is therefore an upper bound on the true tariff contribution; scaling by an estimated pass-through coefficient yields a more conservative estimate.
2. **No general equilibrium effects:** The counterfactual holds all non-tariff factors constant. It does not account for second-round effects such as wage responses, substitution away from imported goods, or monetary policy reactions.
3. **Static weights:** Spending weights are fixed at 2022 values from the PCE bridge and do not update to reflect the 2025 consumption basket.
4. **Services assumed unaffected:** Services PCE is treated as having zero direct tariff exposure. This is a simplification — some services use imported inputs — but is standard in the literature.

---

## References

Minton, Robert, and Mariano Somale (2025). "Detecting Tariff Effects on Consumer Prices in Real Time," *FEDS Notes*. Board of Governors of the Federal Reserve System, May 09, 2025.

The Budget Lab at Yale (2026). "Tracking the Economic Effects of Tariffs," February 18, 2026. https://budgetlab.yale.edu/research/tracking-economic-effects-tariffs

The Budget Lab at Yale (2026). "Methodological Appendix for Tracking the Economic Effects of Tariffs," February 17, 2026. https://budgetlab.yale.edu/research/methodological-appendix-tracking-economic-effects-tariffs
