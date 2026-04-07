## Summary of the Comparison

This note summarizes a comparison of the Yale Budget Lab approach versus the `tradewartracker` repo. As a summary, Budget Lab’s framework is useful for tracking import-sensitive prices, but it is weaker as a structural exercise linking tariffs to observed inflation. The main concern is that its predicted-price object and observed-price object are constructed in a way which can obscure the true role of tariff heterogeneity and allow unrelated shocks to look like tariff effects.

---

## 1. How Budget Lab Constructs the Predicted Price Effect

The key point is that Budget Lab does **not** appear to construct the predicted consumer price effect by carrying category-specific tariff changes all the way through category-specific exposure measures and then aggregating. Instead, for the price-impact / passthrough exercise, the object is closer to:

$$
\text{Predicted price effect for basket}
\approx
\bar s \cdot \Delta \tau
$$

where:

- $\bar s$ is an average import-exposure measure for the basket, typically based on total import content
- $\Delta \tau$ is an aggregate tariff change

So the basic structure is:

1. Construct an **aggregate tariff change**
2. Construct a **weighted-average exposure** for a broad basket
3. Multiply the two together to get the relevant predicted tariff-pressure term

### How this differs from this repo

This repo is essentially a disaggregated accounting model. There, the relevant object that it builds is:

$$
\hat p_j = \sum_i (m_i \Delta \tau_i)L_{ij}
$$

where:

- $i$ indexes commodities facing tariff changes
- $m_i$ is import exposure
- $\Delta \tau_i$ is the tariff change for commodity $i$
- $L_{ij}$ is the Leontief inverse element, capturing both direct and indirect input linkages from commodity $i$ to consumption category $j$

So `tradewartracker` does the interaction in the right order:

1. Take **commodity-specific tariffs**
2. Interact them with **commodity-specific import exposure**
3. Propagate through the IO system
4. Then aggregate to broader consumption categories

That is the central difference.

### Main implication

Budget Lab is closer to:

$$
E[s_k] \cdot E[\Delta \tau_k]
$$

whereas `tradewartracker` is closer to:

$$
E[s_k \Delta \tau_k]
$$

Those are only the same under restrictive conditions.

---

## 2. How Budget Lab Constructs the Import-Content Price Index

A second issue is what the Budget Lab compares the price impact above with. They do not compare it against observed inflation rates but they construct an “import-content” PCE price index.

The logic is the following. They take observed PCE component prices and reweight them so that categories with higher import exposure get more weight. Importantly, for this index they use **direct import shares**, not total import content to avoid double counting. So the object is something like:

$$
I_t = \sum_k w_k P_{k,t}
$$

where:

- $P_{k,t}$ is the observed price of category $k$
- $w_k$ is larger for categories with greater direct import exposure

The rationale is that observed PCE component prices already embody upstream cost pressures, so weighting by **total** import content would double count indirect exposure already embedded in the price series.

### Summarizing sections 1 and 2

This means Budget Lab is using:

- one object for **predicted tariff pressure**: aggregate tariff change times average exposure
- another object for **observed prices**: a reweighted import-sensitive price index

Both constructions have implications for interpreting "price impacts of tariffs."

---

## 3. Implication 1: No Covariance Between Tariffs and Exposure

The Budget Lab’s predicted price-impact treatment misses the covariance between tariff changes and import exposure.

Suppose some categories have high import content but low tariff exposure, while others have lower import content but high tariff exposure. Then the relevant predicted effect should depend on:

$$
\sum_k \omega_k s_k \Delta \tau_k
$$

not on:

$$
\bar s \cdot \Delta \tau
$$

The Budget Lab shortcut effectively aggregates too early. It uses an average exposure and an average tariff change separately, rather than letting tariff variation line up with exposure variation at the category level.

### Why this matters

If tariffs are heterogeneous across goods, then categories with high import content but low tariff changes should not mechanically contribute much to the predicted price effect. A formula based on aggregate tariff change times average exposure can misstate the true first-order impact.

---

## 4. Implication 2: Model–Data Mismatch

Even setting aside the predicted-side covariance problem above, the observed-side construction introduces its own issues.

Normally, one would want:

- a predicted object from the model
- an observed object from the data

to be constructed in a closely aligned way.

But here, Budget Lab is comparing:

### Predicted side
A basket-level tariff-pressure term built from:

$$
\bar s \cdot \Delta \tau
$$

### Observed side
A reweighted import-content PCE price index built from:

$$
I_t = \sum_k w_k P_{k,t}
$$

using direct import shares

These are not the same object. The predicted side uses one exposure concept and an aggregate tariff shock. The observed side uses a different weighting scheme and actual price movements. So the comparison is informative as a rough tracker, but it is not a tightly aligned model-versus-data comparison.

The import-content index may be a useful descriptive indicator, but it is weaker as a clean validation test of a predicted tariff-price model.

###  Potential for False Positives

AI-demand driven forces is an example where these issues could come into play. 

Suppose a category like video equipment:

- has high import content
- receives a large weight in the import-content price index
- but is not actually subject to much tariff pressure

Now suppose AI demand pushes up prices in that category.

Then the import-content price index rises, even though tariffs are not the cause. Why would this happen? The observed index is driven by:

$$
\Delta I_t = \sum_k w_k \Delta P_{k,t}
$$

So any shock that raises prices in highly weighted categories will move the index, regardless of whether the shock is tariff-related.

### Implication

This creates the possibility of a false positive:

- the observed import-content index rises
- the predicted tariff term is in the background
- one might infer tariff pressure is showing up in prices
- but in fact the movement could be driven by something else entirely, such as AI demand

So the index is an **import-sensitive price thermometer**, not a tariff-attribution statistic.

That is a conceptual limitation.

---

## 5. Data Mechanics

This section walks through the concrete pipeline steps side by side. The notation follows the rest of this document: $i$ indexes commodities, $k$ indexes PCE categories, $m_i$ is import exposure, $\Delta\tau_i$ is the tariff change for commodity $i$, and $L_{ij}$ is the Leontief inverse element.

### 5a. Import Shares

Both pipelines start from BEA data to compute how much of each commodity's domestic availability comes from imports.

| | This Repo | Budget Lab |
|---|---|---|
| **Source** | BEA Supply Table (API, TableID 262) | BEA Import Matrix (static Excel, 2024) |
| **Formula** | $m_i = \text{imports}_i / \text{total supply}_i$ | $m_i = \text{imports}_i / \text{total use}_i$ |
| **Year** | Configurable (default 2024) | Fixed at 2024 |
| **Retrieval** | BEA API at runtime | Pre-downloaded file |

The denominators (total supply vs. total use) differ slightly but are near-identical for most commodities. Both represent the total availability of commodity $i$ in the domestic economy.

### 5b. Leontief Inverse

Both pipelines use the BEA's Leontief total requirements matrix $L_{ij}$, which captures direct and indirect input linkages across commodities.

| | This Repo | Budget Lab |
|---|---|---|
| **Method** | Compute $(I - A)^{-1}$ from Use Table, or fetch BEA pre-computed (TableID 59) | Read BEA pre-computed total requirements from Excel |
| **Default** | Pre-computed from BEA | Pre-computed from BEA |
| **Granularity** | 71 summary industries (or 402 in detail pipeline) | ~73 commodities (summary level) |
| **Validation** | Cross-checks computed $L$ against BEA published $L$ | None documented |

Both use the same underlying object. Total import content is then computed identically in both pipelines:

$$
\tilde{m}_j = \sum_i m_i \cdot L_{ij}
$$

This gives the total import content embedded in one dollar of commodity $j$'s output, via all upstream tiers.

### 5c. Tariff Rates

Both compute effective tariff rates (duties collected / import value) per commodity, not statutory rates. The key difference is what happens next.

| | This Repo | Budget Lab |
|---|---|---|
| **Source** | Census monthly import data (parquet), NAICS6 | USITC Customs and Duties (monthly Excel) |
| **Effective rate** | duties / imports at NAICS6 | duties / customs value at NAICS commodity level |
| **Baseline** | Annual average over all months of baseline year (default 2024) | 2022–2024 average effective rate |
| **Concordance** | NAICS6 $\to$ BEA summary codes | NAICS $\to$ BEA via crosswalk CSV |
| **Output** | Per-commodity vector $\Delta\tau_i$ carried forward | Collapsed to a single scalar $\overline{\Delta\tau} = \sum_i v_i \Delta\tau_i$ (customs-value-weighted average) |

This is where the pipelines begin to diverge. This repo keeps $\Delta\tau_i$ as a vector; Budget Lab reduces it to one number before the price calculation.

### 5d. Tariff Propagation

This is the core divergence, and where the conceptual issues from Sections 1 and 3 show up in the actual code.

**This repo** feeds per-commodity tariffs directly into the Leontief multiplication:

$$
\hat p_j = \sum_i (m_i \cdot \Delta\tau_i) \cdot L_{ij}
$$

Each industry $j$ gets a distinct predicted price effect that reflects the specific tariff rates faced by each of its upstream inputs (steel, electronics, chemicals, etc.).

**Budget Lab** multiplies two pre-aggregated scalars:

$$
\hat p^{\text{BL}} = \overline{\Delta\tau} \cdot \bar s
$$

where $\bar s = \sum_k e_k \cdot s_k$ is an expenditure-weighted average of per-category import content. All cross-commodity variation in tariff rates has been averaged away.

| | This Repo | Budget Lab |
|---|---|---|
| **Tariff input** | Per-commodity $\Delta\tau_i$ inside the Leontief sum | Scalar $\overline{\Delta\tau}$ outside the sum |
| **Output** | Vector of predicted price effects $\hat p_j$, one per commodity | Single scalar $\hat p^{\text{BL}}$ |
| **Sensitivity to tariff composition** | Yes — different tariff mixes produce different predictions | No — only the weighted-average rate matters |
| **Covariance between tariffs and exposure** | Preserved | Lost (Section 3) |

Note: Budget Lab *does* use the disaggregated structure $\sum_i \Delta\tau_i \cdot L_{ij} \cdot m_i$ for their **employment index**. But this is not carried over to the price passthrough calculation.

### 5e. PCE Bridge

Both pipelines use BEA's PCE bridge matrix $B_{ik}$ to map commodity-level results to consumption categories.

| | This Repo | Budget Lab |
|---|---|---|
| **Bridge source** | `PCEBridge_Summary.xlsx` (fetched at runtime) | `PCEBridge_Summary.xlsx` (static Excel, 2024) |
| **What gets bridged** | Per-commodity predicted price effects $\hat p_j$ | Per-commodity import content $\tilde{m}_j$ |
| **Output** | Per-category predicted tariff effect: $\hat P_k = \sum_i \hat p_i \cdot B_{ik} / \sum_i B_{ik}$ | Per-category import content share: $s_k = \sum_i \tilde{m}_i \cdot B_{ik} / \sum_i B_{ik}$ |
| **Categories** | 27 core goods (food and energy excluded) | 27 core goods (same set, filtered at runtime) |

This repo produces a **predicted price effect** for each PCE category (a number in percentage points). Budget Lab produces an **import content weight** for each category, used to construct the price index described in Section 2.

### 5f. Comparison to Data

This is where the methodologies diverge most sharply.

**This repo** compares the model to data **category by category**:

1. For each of the 27 core goods PCE categories, compute:
   - **X-axis**: predicted tariff effect $\hat P_k$ from the pipeline above
   - **Y-axis**: excess inflation = actual price growth minus a pre-tariff baseline trend
2. Plot all 27 categories in a scatter, weighted by PCE expenditure share
3. Fit a WLS regression — under the hypothesis that the IO model is correct, the slope should be ~1

**Budget Lab** compares the model to data **in aggregate**:

1. Construct the import-content price index $I_t = \sum_k w_k P_{k,t}$ (Section 2)
2. Estimate a pre-2025 trend for $I_t$ and measure the deviation
3. Compute implied passthrough = deviation / $\hat p^{\text{BL}}$

| | This Repo | Budget Lab |
|---|---|---|
| **Predicted object** | 27-element vector $\hat P_k$ | Single scalar $\hat p^{\text{BL}}$ |
| **Observed object** | Actual PCE price changes by category | Import-content-weighted price index $I_t$ |
| **Comparison** | Cross-category regression (slope, $R^2$) | Aggregate ratio (implied passthrough) |
| **Can detect wrong composition** | Yes — if the model predicts the wrong categories, the scatter shows it | No — composition is averaged away on both sides |
| **Vulnerable to non-tariff shocks** | Less so — a demand shock in one category only affects one point | More so — any shock in high-$w_k$ categories moves the index (Section 4) |
