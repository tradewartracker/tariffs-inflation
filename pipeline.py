"""
pipeline.py — Tariff PCE pass-through computation pipeline.

Each function corresponds to a numbered step in tariff_pce_methodology.md.
Functions are pure: they accept inputs and return clean DataFrames / arrays
with no side effects.  Import and call them from the notebook.
"""

import io

import numpy as np
import pandas as pd
import requests

from concordance import aggregate_to_bea, build_concordance
from compute_tariff_rates import compute_effective_tariff_rates, load_naics_imports


# ── Step 1: Direct import shares ─────────────────────────────────────────────

def step1_import_shares(year: int, api_key: str) -> pd.DataFrame:
    """Step 1 (methodology §2): Direct import share m_i per BEA commodity.

    m_i = imports(i) / total_supply(i)   [BEA Supply Table 262]

    Returns DataFrame with columns:
        BEA_code, BEA_descr, imports, total_supply, import_share
    """
    r = requests.get(
        "https://apps.bea.gov/api/data"
        f"?UserID={api_key}"
        "&method=GetData"
        "&DataSetName=InputOutput"
        "&TableID=262"
        f"&Year={year}"
        "&ResultFormat=json"
    )
    r.raise_for_status()
    df = pd.DataFrame(r.json()["BEAAPI"]["Results"][0]["Data"])
    df["DataValue"] = pd.to_numeric(df["DataValue"].str.replace(",", ""), errors="coerce")

    imports_by_commodity = (
        df[df["ColCode"] == "MCIF"][["RowCode", "RowDescr", "DataValue"]]
        .copy()
        .rename(columns={"RowCode": "BEA_code", "RowDescr": "BEA_descr", "DataValue": "imports"})
        .reset_index(drop=True)
    )
    total_supply = (
        df[df["ColCode"] == "T013"][["RowCode", "DataValue"]]
        .copy()
        .rename(columns={"RowCode": "BEA_code", "DataValue": "total_supply"})
    )

    result = imports_by_commodity.merge(total_supply, on="BEA_code", how="inner")
    result["import_share"] = result["imports"] / result["total_supply"]
    return result.reset_index(drop=True)


# ── Steps 2–3: Technical coefficients matrix and Leontief inverse ─────────────

def step2_3_leontief(year: int, api_key: str, leontief_source: str = "computed") -> tuple:
    """Steps 2–3 (methodology §3–4): Build A matrix and Leontief inverse L.

    A_ij = intermediate use of commodity i per dollar of output of industry j
           [BEA Use Table 259]

    leontief_source:
        "computed" — invert (I - A) directly from Table 259 (default).
        "bea"      — replace L with BEA's pre-computed Commodity-by-Commodity
                     Total Requirements table (TableID 59).  A is still built
                     from Table 259 for the sanity checks.

    Returns (industries, A, L):
        industries : list of BEA IO codes defining the shared row/column ordering
        A          : np.ndarray (n, n) technical coefficients matrix
        L          : np.ndarray (n, n) Leontief inverse
    """
    r = requests.get(
        "https://apps.bea.gov/api/data"
        f"?UserID={api_key}"
        "&method=GetData"
        "&DataSetName=InputOutput"
        "&TableID=259"
        f"&Year={year}"
        "&ResultFormat=json"
    )
    r.raise_for_status()
    df = pd.DataFrame(r.json()["BEAAPI"]["Results"][0]["Data"])
    df["DataValue"] = pd.to_numeric(df["DataValue"].str.replace(",", ""), errors="coerce")

    gross_output = (
        df[df["RowCode"] == "T018"][["ColCode", "DataValue"]]
        .copy()
        .rename(columns={"ColCode": "BEA_code", "DataValue": "gross_output"})
    )

    industries = sorted(
        set(df["RowCode"].unique())
        & set(df["ColCode"].unique())
        & set(gross_output["BEA_code"].unique())
    )

    use_matrix = (
        df[df["RowCode"].isin(industries) & df["ColCode"].isin(industries)]
        .pivot_table(index="RowCode", columns="ColCode", values="DataValue", fill_value=0)
        .reindex(index=industries, columns=industries, fill_value=0)
    )

    go = gross_output.set_index("BEA_code").reindex(industries)["gross_output"].values
    A = use_matrix.values / go[np.newaxis, :]

    if leontief_source == "bea":
        r2 = requests.get(
            "https://apps.bea.gov/api/data"
            f"?UserID={api_key}"
            "&method=GetData"
            "&DataSetName=InputOutput"
            "&TableID=59"
            f"&Year={year}"
            "&ResultFormat=json"
        )
        r2.raise_for_status()
        df2 = pd.DataFrame(r2.json()["BEAAPI"]["Results"][0]["Data"])
        df2["DataValue"] = pd.to_numeric(df2["DataValue"].str.replace(",", ""), errors="coerce")
        L = (
            df2[df2["RowCode"].isin(industries) & df2["ColCode"].isin(industries)]
            .pivot_table(index="RowCode", columns="ColCode", values="DataValue", fill_value=0)
            .reindex(index=industries, columns=industries, fill_value=0)
            .values
        )
        print("Leontief source: BEA pre-computed Total Requirements (TableID 59)")
    else:
        I = np.eye(len(industries))
        L = np.linalg.inv(I - A)
        print("Leontief source: computed from (I - A)^{-1} via Use Table 259")

    return industries, A, L


# ── Validation: compare computed L against BEA pre-computed Total Requirements ─

def validate_leontief(year: int, api_key: str, industries: list, L: np.ndarray) -> dict:
    """Fetch BEA TableID 260 (Commodity-by-Commodity Total Requirements) and
    compare element-wise against the locally computed Leontief inverse L.

    Returns a dict with summary statistics and a DataFrame of the top discrepancies.
    """
    r = requests.get(
        "https://apps.bea.gov/api/data"
        f"?UserID={api_key}"
        "&method=GetData"
        "&DataSetName=InputOutput"
        "&TableID=59"
        f"&Year={year}"
        "&ResultFormat=json"
    )
    r.raise_for_status()
    df_bea = pd.DataFrame(r.json()["BEAAPI"]["Results"][0]["Data"])
    df_bea["DataValue"] = pd.to_numeric(df_bea["DataValue"].str.replace(",", ""), errors="coerce")

    L_bea = (
        df_bea[df_bea["RowCode"].isin(industries) & df_bea["ColCode"].isin(industries)]
        .pivot_table(index="RowCode", columns="ColCode", values="DataValue", fill_value=0)
        .reindex(index=industries, columns=industries, fill_value=0)
        .values
    )

    diff     = L - L_bea
    abs_diff = np.abs(diff)

    flat_idx = np.argsort(abs_diff.ravel())[-10:][::-1]
    top_rows = []
    for flat in flat_idx:
        i, j = divmod(flat, len(industries))
        top_rows.append({
            "row_industry": industries[i],
            "col_industry": industries[j],
            "L_computed":   L[i, j],
            "L_bea":        L_bea[i, j],
            "abs_diff":     abs_diff[i, j],
        })

    return {
        "max_abs_diff":  abs_diff.max(),
        "mean_abs_diff": abs_diff.mean(),
        "max_rel_diff":  (abs_diff / np.abs(L_bea).clip(1e-10)).max(),
        "top_diffs":     pd.DataFrame(top_rows),
        "L_bea":         L_bea,
    }


# ── Step 4: Total import content ─────────────────────────────────────────────

def step4_total_import_content(
    import_shares: pd.DataFrame,
    industries: list,
    L: np.ndarray,
) -> tuple:
    """Step 4 (methodology §5): Total import content per industry via Leontief.

    m_total[j] = m' L — direct import share of each commodity propagated
                 through the full supply chain (direct + all indirect tiers).

    Returns (m_vec, m_total):
        m_vec   : np.ndarray (n,) direct import shares aligned to `industries`
        m_total : np.ndarray (n,) total (direct + indirect) import content
    """
    m_vec = (
        import_shares.set_index("BEA_code")
        .reindex(industries)["import_share"]
        .fillna(0)
        .values
    )
    m_total = m_vec @ L
    return m_vec, m_total


# ── PCE Bridge (utility) ──────────────────────────────────────────────────────

def load_pce_bridge(year: int, api_key: str) -> pd.DataFrame:
    """Load the BEA PCE Bridge workbook for the given IO year.

    Returns DataFrame with columns:
        NIPA_line, PCE_category, commodity_code, commodity_descr,
        producers_value, transport_costs, wholesale, retail,
        purchasers_value, year
    """
    r = requests.get("https://apps.bea.gov/industry/release/xlsx/PCEBridge_Summary.xlsx")
    r.raise_for_status()
    df = pd.read_excel(
        io.BytesIO(r.content),
        sheet_name=str(year),
        engine="openpyxl",
        skiprows=5,
        header=None,
        names=[
            "NIPA_line", "PCE_category", "commodity_code", "commodity_descr",
            "producers_value", "transport_costs", "wholesale", "retail",
            "purchasers_value", "year",
        ],
    )
    df["commodity_code"]  = df["commodity_code"].astype(str).str.strip()
    df["PCE_category"]    = df["PCE_category"].astype(str).str.strip()
    df = df[
        ~df["commodity_code"].isin({"nan", "None", ""})
        & ~df["PCE_category"].isin({"nan", "None", ""})
    ]
    df["producers_value"]  = pd.to_numeric(df["producers_value"],  errors="coerce")
    df["purchasers_value"] = pd.to_numeric(df["purchasers_value"], errors="coerce")
    return df.reset_index(drop=True)


# ── Step 5: Delta tariff per BEA industry ─────────────────────────────────────

def step5_delta_tariff(
    imports_file: str,
    baseline_year: int,
    current_month: str,
) -> pd.DataFrame:
    """Step 5 (methodology §6): Δτ = τ_current − τ_baseline per BEA IO industry.

    Baseline  = annual average over all 12 months of `baseline_year`
                (sum duties and imports across months, then divide once —
                 correctly handles varying import volumes across months).
    Current   = single month `current_month` in 'YYYY-MM' format.

    Returns DataFrame with columns:
        bea_io, bea_desc, tau_base, tau, delta_tariff, imports, duties
    """
    df = load_naics_imports(imports_file)

    dates_baseline = [f"{baseline_year}-{str(m).zfill(2)}" for m in range(1, 13)]
    rates_baseline = compute_effective_tariff_rates(df, dates_baseline)
    rates_current  = compute_effective_tariff_rates(df, [current_month])

    concordance  = build_concordance(rates_current["naics6"].tolist())
    df_baseline  = aggregate_to_bea(rates_baseline, concordance)
    df_current   = aggregate_to_bea(rates_current,  concordance)

    # Annual average: pool all 12 months then divide once
    baseline_avg = (
        df_baseline
        .groupby("bea_io")[["duties", "imports"]]
        .sum()
        .reset_index()
        .assign(tau_base=lambda x: x["duties"] / x["imports"].replace(0, float("nan")))
    )

    result = df_current[["bea_io", "bea_desc", "tau", "imports", "duties"]].merge(
        baseline_avg[["bea_io", "tau_base"]], on="bea_io", how="left"
    )
    result["delta_tariff"] = result["tau"] - result["tau_base"]
    return result.reset_index(drop=True)


# ── Step 6: Predicted PCE price effect ───────────────────────────────────────

def step6_pce_effect(
    industries: list,
    m_vec: np.ndarray,
    L: np.ndarray,
    delta_tariff_df: pd.DataFrame,
    pce_bridge: pd.DataFrame,
    markup: str = "constant_dollar",
) -> pd.DataFrame:
    """Step 6 (methodology §7): Predicted tariff effect aggregated to PCE categories.

    Producer price effect per industry j:
        p̂_j = Σ_i  m_i · Δτ_i · L_ij

    PCE bridge aggregation (two options controlled by `markup`):

        "constant_dollar"  — retailers maintain a fixed dollar margin.
                             Numerator weight = producers_value (factory-gate value).
                             Only the producers' share of consumer spending passes
                             through.  Conservative baseline (Minton & Somale 2025).

        "constant_percent" — retailers maintain a fixed percentage margin.
                             Numerator weight = purchasers_value.
                             Full consumer price moves with the producer price.

    Denominator is always purchasers_value (total consumer spending per category).

    Returns DataFrame with columns:
        PCE_category, predicted_effect, producers_value_total, purchasers_value_total
    Sorted descending by predicted_effect.
    """
    if markup not in ("constant_dollar", "constant_percent"):
        raise ValueError(
            f"markup must be 'constant_dollar' or 'constant_percent', got '{markup}'"
        )

    tau_series = (
        delta_tariff_df.set_index("bea_io")["delta_tariff"]
        .reindex(industries)
        .fillna(0)
    )

    tariff_weighted_imports = m_vec * tau_series.values
    predicted_effect_arr    = tariff_weighted_imports @ L
    predicted_effect_series = pd.Series(predicted_effect_arr, index=industries)

    bridge = pce_bridge.copy()
    bridge["predicted_effect"] = bridge["commodity_code"].map(predicted_effect_series)

    weight_col = "producers_value" if markup == "constant_dollar" else "purchasers_value"
    bridge["effect_dollars"] = bridge["predicted_effect"] * bridge[weight_col]

    pce_effect      = bridge.groupby("PCE_category")["effect_dollars"].sum()
    pce_pv_total    = bridge.groupby("PCE_category")["producers_value"].sum()
    pce_purc_total  = bridge.groupby("PCE_category")["purchasers_value"].sum()
    denom           = bridge.groupby("PCE_category")["purchasers_value"].sum()

    result = pd.DataFrame({
        "predicted_effect":       pce_effect / denom,
        "producers_value_total":  pce_pv_total,
        "purchasers_value_total": pce_purc_total,
    }).dropna(subset=["predicted_effect"]).sort_values("predicted_effect", ascending=False)

    return result.reset_index()


# ── Industry trace (diagnostic) ──────────────────────────────────────────────

def trace_industry(
    bea_code: str,
    import_shares: pd.DataFrame,
    industries: list,
    L: np.ndarray,
    m_vec: np.ndarray,
    m_total: np.ndarray,
    delta_tariff_df: pd.DataFrame,
    pce_bridge: pd.DataFrame,
    pce_effect_df: pd.DataFrame,
    markup: str = "constant_dollar",
) -> None:
    """Print a full methodology trace for a single BEA IO industry.

    Walks through every step in tariff_pce_methodology.md for `bea_code`:

      Step 1  — direct import share  (m_i)
      Step 4  — total import content via Leontief  (m̃_j)
      Step 5  — tariff change  (Δτ)
      Step 5  — predicted producer-level price effect  (p̂_j)
      Step 6  — PCE bridge breakdown and final consumer-price effect

    All pre-computed objects (import_shares, industries, L, m_vec, m_total,
    delta_tariff_df, pce_bridge, pce_effect_df) should come from the
    corresponding step functions so that the trace is consistent with the
    main pipeline run.

    Parameters
    ----------
    bea_code        : BEA IO commodity code, e.g. '3361MV'
    import_shares   : output of step1_import_shares()
    industries      : list returned by step2_3_leontief()
    L               : Leontief inverse returned by step2_3_leontief()
    m_vec           : direct import-share vector from step4_total_import_content()
    m_total         : total import-content vector from step4_total_import_content()
    delta_tariff_df : output of step5_delta_tariff()
    pce_bridge      : output of load_pce_bridge()
    pce_effect_df   : output of step6_pce_effect()
    markup          : 'constant_dollar' (default) or 'constant_percent'
    """
    sep   = "─" * 64
    sep2  = "· " * 32

    # ── Resolve display name ──────────────────────────────────────────────────
    descr_row = import_shares.query("BEA_code == @bea_code")
    descr = descr_row["BEA_descr"].iloc[0] if not descr_row.empty else bea_code

    print(sep)
    print(f"  INDUSTRY TRACE  ·  {bea_code}  —  {descr}")
    print(sep)

    # ── Step 1: direct import share ───────────────────────────────────────────
    direct_share = descr_row["import_share"].iloc[0] if not descr_row.empty else float("nan")
    imports_val  = descr_row["imports"].iloc[0]      if not descr_row.empty else float("nan")
    supply_val   = descr_row["total_supply"].iloc[0] if not descr_row.empty else float("nan")

    print(f"\nStep 1  —  Direct import share  (m_i = imports / total supply)")
    print(f"  imports       =  {imports_val:>12,.0f}  ($M)")
    print(f"  total supply  =  {supply_val:>12,.0f}  ($M)")
    print(f"  m_i           =  {direct_share:>12.1%}")

    # ── Check industry list membership ───────────────────────────────────────
    if bea_code not in industries:
        print(f"\n  WARNING: '{bea_code}' is not in the Leontief industry list.")
        print(f"  Steps 4–6 require the code to appear in both rows and columns of the")
        print(f"  Use Table.  Cannot continue trace.")
        return

    j = industries.index(bea_code)
    total_content = m_total[j]
    amplification = total_content / direct_share if direct_share > 0 else float("nan")

    # ── Step 4: total import content ─────────────────────────────────────────
    print(f"\nStep 4  —  Total import content via Leontief  (m̃_j = m′ L)")
    print(f"  direct m_i     =  {direct_share:>12.1%}  (imports at the border)")
    print(f"  total m̃_j      =  {total_content:>12.1%}  (direct + all upstream tiers)")
    print(f"  indirect share =  {total_content - direct_share:>12.1%}  (embedded in domestic inputs)")
    print(f"  amplification  =  {amplification:>12.2f}×")

    # ── Step 5: tariff change ─────────────────────────────────────────────────
    tau_row = delta_tariff_df.query("bea_io == @bea_code")
    print(f"\nStep 5  —  Import tariff change  (Δτ = τ_current − τ_baseline)")
    if tau_row.empty:
        delta_tau = 0.0
        print(f"  '{bea_code}' not found in tariff data — Δτ = 0.0 (no tariff change modelled)")
    else:
        tau_base  = tau_row["tau_base"].iloc[0]
        tau_curr  = tau_row["tau"].iloc[0]
        delta_tau = tau_row["delta_tariff"].iloc[0]
        print(f"  τ_baseline  =  {tau_base:>12.1%}")
        print(f"  τ_current   =  {tau_curr:>12.1%}")
        print(f"  Δτ          =  {delta_tau:>+12.1%}")

    # ── Step 5: predicted producer-level price effect ─────────────────────────
    tau_series = (
        delta_tariff_df.set_index("bea_io")["delta_tariff"]
        .reindex(industries)
        .fillna(0)
    )
    tw_imports    = m_vec * tau_series.values
    pred_full     = tw_imports @ L
    p_hat         = pred_full[j]
    naive_approx  = total_content * delta_tau

    print(f"\nStep 5  —  Predicted producer-level price effect  (p̂_j = Σ_i m_i·Δτ_i·L_ij)")
    print(f"  p̂_j             =  {p_hat:>12.1%}")
    print(f"  Naive approx    =  {naive_approx:>12.1%}  (m̃_j × Δτ_j, ignores upstream tariff mix)")
    print(f"  The gap reflects different Δτ rates on each upstream input commodity.")

    # ── Step 6: PCE bridge ────────────────────────────────────────────────────
    bridge_rows = pce_bridge.query("commodity_code == @bea_code").copy()
    print(f"\nStep 6  —  PCE Bridge  ({bea_code} → PCE consumer categories)")

    if bridge_rows.empty:
        print(f"  No PCE bridge entries for '{bea_code}'.  No consumer-price effect computed.")
        print(sep)
        return

    prod_val_total = bridge_rows["producers_value"].sum()
    purc_val_total = bridge_rows["purchasers_value"].sum()
    margins_total  = purc_val_total - prod_val_total
    margin_share   = margins_total / purc_val_total if purc_val_total > 0 else float("nan")

    weight_col = "producers_value" if markup == "constant_dollar" else "purchasers_value"
    assumption = (
        "constant dollar  (producers' value weight — margins unchanged)"
        if markup == "constant_dollar"
        else "constant percent (purchasers' value weight — margins scale up)"
    )

    print(f"  Markup assumption: {assumption}")
    print()
    print(f"  {'':40s}  {'Producers ($M)':>16}  {'Purchasers ($M)':>16}  {'Margins ($M)':>14}")
    print(f"  {sep2}")

    # Pre-compute category-level purchasers' value totals from the full bridge
    # (a PCE category can span many commodities — the denominator must be the full total)
    cat_purc_total = pce_bridge.groupby("PCE_category")["purchasers_value"].sum()

    for _, row in bridge_rows.sort_values("purchasers_value", ascending=False).iterrows():
        cat   = row["PCE_category"]
        pv    = row["producers_value"]
        puv   = row["purchasers_value"]
        marg  = puv - pv
        denom = cat_purc_total.get(cat, puv)
        contrib = p_hat * row[weight_col] / denom if denom > 0 else float("nan")
        print(f"  {cat:<40s}  {pv:>16,.0f}  {puv:>16,.0f}  {marg:>14,.0f}  → {contrib:.2%} this commodity")

    print(f"  {sep2}")
    print(f"  {'TOTAL (this commodity)':40s}  {prod_val_total:>16,.0f}  {purc_val_total:>16,.0f}  {margins_total:>14,.0f}")
    print(f"  Margin share of consumer price: {margin_share:.1%}")

    # Final PCE effects
    pce_cats = bridge_rows["PCE_category"].unique().tolist()
    matched  = pce_effect_df.query("PCE_category in @pce_cats")

    print(f"\n  Final consumer-price effect (all commodities → PCE category):")
    print(f"  {'PCE category':<40s}  {'Effect':>8}  {'Producers ($M)':>16}  {'Purchasers ($M)':>16}")
    for _, row in matched.sort_values("predicted_effect", ascending=False).iterrows():
        print(
            f"  {row['PCE_category']:<40s}  "
            f"{row['predicted_effect']:>8.2%}  "
            f"{row['producers_value_total']:>16,.0f}  "
            f"{row['purchasers_value_total']:>16,.0f}"
        )

    # Illustrative formula for single-commodity categories
    if len(pce_cats) == 1 and len(bridge_rows) == 1:
        eff = matched["predicted_effect"].iloc[0] if not matched.empty else float("nan")
        pv  = bridge_rows["producers_value"].iloc[0]
        puv = bridge_rows["purchasers_value"].iloc[0]
        print(f"\n  Formula check (single-commodity PCE category):")
        print(f"    p̂_j × producers_value / purchasers_value")
        print(f"    {p_hat:.4f} × {pv:,.0f} / {puv:,.0f} = {p_hat * pv / puv:.2%}")
        if not matched.empty:
            print(f"    Matches pce_effect_df: {eff:.2%}")

    print(sep)


# ── Step 7a: Load monthly PCE price index ────────────────────────────────────

_NIPA_MEASURE_MAP = {
    "core_pce":     ("T20804", "PCE excluding food and energy"),
    "headline_pce": ("T20804", "Personal consumption expenditures (PCE)"),
}


def step7_load_inflation(
    measure: str,
    api_key: str,
    years: list,
) -> pd.Series:
    """Step 7 (methodology §8): Monthly PCE price index from BEA NIPA T20804.

    measure : 'core_pce' or 'headline_pce'
    years   : list of ints, e.g. [2024, 2025]

    Returns pd.Series indexed by 'YYYY-MM' strings, values = price index level.
    """
    if measure not in _NIPA_MEASURE_MAP:
        raise ValueError(
            f"measure must be one of {list(_NIPA_MEASURE_MAP)}, got '{measure}'"
        )

    table, line_desc = _NIPA_MEASURE_MAP[measure]
    year_str = ",".join(str(y) for y in years)

    r = requests.get(
        "https://apps.bea.gov/api/data"
        f"?UserID={api_key}"
        "&method=GetData"
        "&DataSetName=NIPA"
        f"&TableName={table}"
        "&Frequency=M"
        f"&Year={year_str}"
        "&ResultFormat=json"
    )
    r.raise_for_status()
    data = pd.DataFrame(r.json()["BEAAPI"]["Results"]["Data"])
    data["DataValue"] = pd.to_numeric(data["DataValue"], errors="coerce")

    series = data[data["LineDescription"] == line_desc][["TimePeriod", "DataValue"]].copy()
    if series.empty:
        available = sorted(data["LineDescription"].unique().tolist())
        raise ValueError(
            f"Line '{line_desc}' not found in {table}.\nAvailable lines: {available}"
        )

    # Convert BEA format '2024M12' → '2024-12'
    series["TimePeriod"] = series["TimePeriod"].str.replace("M", "-", regex=False)
    return series.sort_values("TimePeriod").set_index("TimePeriod")["DataValue"]


# ── Step 7b: Monthly counterfactual ──────────────────────────────────────────

def step7_counterfactual(
    inflation_series: pd.Series,
    pce_effect_df: pd.DataFrame,
    baseline_month: str,
    current_month: str,
    core_goods_categories: list,
) -> dict:
    """Step 7 (methodology §8): Counterfactual inflation from T20804 series.

    Subtracts the predicted tariff contribution to core goods from actual
    inflation to construct the counterfactual ("what would inflation have been
    absent the tariff increase?").

    tariff_contribution = core_goods_effect × core_goods_share_of_total_PCE

    baseline_month / current_month : 'YYYY-MM' strings matching inflation_series index.

    Returns dict with keys:
        actual_inflation, core_goods_effect, core_goods_share,
        tariff_contribution, counterfactual_inflation
    """
    core = pce_effect_df.query("PCE_category in @core_goods_categories")

    if core.empty:
        raise ValueError("No core goods categories matched in pce_effect_df.")

    core_effect = (
        (core["predicted_effect"] * core["purchasers_value_total"]).sum()
        / core["purchasers_value_total"].sum()
    )
    core_goods_share = (
        core["purchasers_value_total"].sum()
        / pce_effect_df["purchasers_value_total"].sum()
    )

    for month in (baseline_month, current_month):
        if month not in inflation_series.index:
            raise ValueError(
                f"Month '{month}' not found in inflation series. "
                f"Available range: {inflation_series.index.min()} – {inflation_series.index.max()}"
            )

    idx_base = inflation_series[baseline_month]
    idx_curr = inflation_series[current_month]

    actual_inflation    = (idx_curr - idx_base) / idx_base
    tariff_contribution = core_effect * core_goods_share

    return {
        "actual_inflation":        actual_inflation,
        "core_goods_effect":       core_effect,
        "core_goods_share":        core_goods_share,
        "tariff_contribution":     tariff_contribution,
        "counterfactual_inflation": actual_inflation - tariff_contribution,
    }


# ── Step 7c: Quarterly core-goods price index ─────────────────────────────────

def step7_core_goods_index(
    api_key: str,
    years: list,
    pce_effect_df: pd.DataFrame,
    core_goods_categories: list,
    nipa_crosswalk: dict,
) -> pd.Series:
    """Construct a weighted quarterly price index for core goods (NIPA T20404).

    Uses PCE bridge purchasers' values as weights (proportional to consumer
    spending on each category).

    Returns pd.Series indexed by quarter label (e.g. '2025Q4').
    """
    year_str = ",".join(str(y) for y in years)
    r = requests.get(
        "https://apps.bea.gov/api/data"
        f"?UserID={api_key}"
        "&method=GetData"
        "&DataSetName=NIPA"
        "&TableName=T20404"
        "&Frequency=Q"
        f"&Year={year_str}"
        "&ResultFormat=json"
    )
    r.raise_for_status()
    pce_q = pd.DataFrame(r.json()["BEAAPI"]["Results"]["Data"])
    pce_q["DataValue"] = pd.to_numeric(pce_q["DataValue"], errors="coerce")

    bea_names = list(nipa_crosswalk.values())
    price_data = (
        pce_q[pce_q["LineDescription"].isin(bea_names)]
        [["LineDescription", "TimePeriod", "DataValue"]]
        .copy()
    )

    missing = [n for n in bea_names if n not in price_data["LineDescription"].values]
    if missing:
        raise ValueError(f"Missing T20404 series: {missing}")

    price_wide = price_data.pivot(
        index="TimePeriod", columns="LineDescription", values="DataValue"
    )

    core = pce_effect_df.query("PCE_category in @core_goods_categories")
    weight_map = (
        core[["PCE_category", "purchasers_value_total"]]
        .assign(bea_name=lambda df: df["PCE_category"].map(nipa_crosswalk))
        .set_index("bea_name")["purchasers_value_total"]
    )
    weights = weight_map.reindex(price_wide.columns)

    index_series = price_wide.multiply(weights, axis=1).sum(axis=1) / weights.sum()
    return index_series.sort_index()


def step7_core_goods_index_monthly(
    pce_monthly_df: pd.DataFrame,
    pce_effect_df: pd.DataFrame,
    core_goods_categories: list,
    nipa_crosswalk: dict,
) -> pd.Series:
    """Construct a weighted monthly price index for core goods (NI Underlying Detail U20404).

    Parameters
    ----------
    pce_monthly_df : pd.DataFrame
        DataFrame from NIUnderlyingDetail / U20404 / Frequency=M.
        Must have columns: LineDescription, TimePeriod (BEA format 'YYYYMmm'),
        DataValue.

    Returns pd.Series indexed by month label (e.g. '2025-12').
    """
    bea_names = list(nipa_crosswalk.values())
    price_data = (
        pce_monthly_df[pce_monthly_df["LineDescription"].isin(bea_names)]
        [["LineDescription", "TimePeriod", "DataValue"]]
        .copy()
    )

    missing = [n for n in bea_names if n not in price_data["LineDescription"].values]
    if missing:
        raise ValueError(f"Missing U20404 series: {missing}")

    # Convert BEA monthly format '2025M12' → '2025-12'
    price_data["TimePeriod"] = price_data["TimePeriod"].str.replace("M", "-", regex=False)

    price_wide = price_data.pivot(
        index="TimePeriod", columns="LineDescription", values="DataValue"
    )

    core = pce_effect_df.query("PCE_category in @core_goods_categories")
    weight_map = (
        core[["PCE_category", "purchasers_value_total"]]
        .assign(bea_name=lambda df: df["PCE_category"].map(nipa_crosswalk))
        .set_index("bea_name")["purchasers_value_total"]
    )
    weights = weight_map.reindex(price_wide.columns)

    index_series = price_wide.multiply(weights, axis=1).sum(axis=1) / weights.sum()
    return index_series.sort_index()


# ── Step 7d: Excess-inflation scatter data ────────────────────────────────────

def step7_excess_inflation(
    api_key: str,
    pce_effect_df: pd.DataFrame,
    core_goods_categories: list,
    nipa_crosswalk: dict,
    current_year: int,
    baseline_start: int,
    baseline_end: int,
) -> pd.DataFrame:
    """Step 7 (methodology §9): Predicted tariff effect vs. excess inflation by category.

    Excess inflation for category k:
        excess_k = YoY_inflation_k(current_year)
                   − mean(YoY_inflation_k(y) for y in baseline_start..baseline_end)

    baseline_start / baseline_end : inclusive range of YoY end-years that define
                                    the "normal" pre-tariff trend.

    Returns DataFrame with columns:
        bea_name, PCE_category, predicted_effect, pce_share,
        inflation_current, baseline_inflation, excess_inflation
    """
    baseline_years = list(range(baseline_start, baseline_end + 1))
    all_years = sorted(
        set([y - 1 for y in baseline_years] + baseline_years + [current_year - 1, current_year])
    )
    year_str = ",".join(str(y) for y in all_years)

    r = requests.get(
        "https://apps.bea.gov/api/data"
        f"?UserID={api_key}"
        "&method=GetData"
        "&DataSetName=NIPA"
        "&TableName=T20404"
        "&Frequency=A"
        f"&Year={year_str}"
        "&ResultFormat=json"
    )
    r.raise_for_status()
    hist = pd.DataFrame(r.json()["BEAAPI"]["Results"]["Data"])
    hist["DataValue"] = pd.to_numeric(hist["DataValue"], errors="coerce")
    hist["Year"] = hist["TimePeriod"].astype(int)

    bea_names = list(nipa_crosswalk.values())
    hist = hist[hist["LineDescription"].isin(bea_names)]
    hist_wide = hist.pivot(index="LineDescription", columns="Year", values="DataValue")

    baseline_inflation = pd.Series({
        name: np.mean([
            (hist_wide.loc[name, yr] - hist_wide.loc[name, yr - 1]) / hist_wide.loc[name, yr - 1]
            for yr in baseline_years
            if yr in hist_wide.columns and yr - 1 in hist_wide.columns
        ])
        for name in bea_names
        if name in hist_wide.index
    })

    inflation_current = (
        (hist_wide[current_year] - hist_wide[current_year - 1])
        / hist_wide[current_year - 1]
    )
    excess_inflation = inflation_current - baseline_inflation

    core = pce_effect_df.query("PCE_category in @core_goods_categories").copy()
    core["pce_share"] = core["purchasers_value_total"] / core["purchasers_value_total"].sum()

    summary = (
        core[["PCE_category", "predicted_effect", "pce_share"]]
        .assign(bea_name=lambda df: df["PCE_category"].map(nipa_crosswalk))
        .set_index("bea_name")
    )
    summary["inflation_current"]  = inflation_current
    summary["baseline_inflation"] = baseline_inflation
    summary["excess_inflation"]   = excess_inflation

    return summary.reset_index()
