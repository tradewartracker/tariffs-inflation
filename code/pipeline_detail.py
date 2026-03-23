"""
pipeline_detail.py — 402-commodity tariff PCE pass-through pipeline.

Parallel implementation of pipeline.py using BEA's detail-level (402-commodity)
IO tables instead of the 71-industry summary tables.  Uses pre-computed BEA
Commodity-by-Commodity Total Requirements as the Leontief inverse.

Data files must be downloaded first via download_detail_data.py.

Functions are pure: they accept inputs and return clean DataFrames / arrays.
"""

import io
from typing import Optional

import numpy as np
import pandas as pd

from compute_tariff_rates import compute_effective_tariff_rates, load_naics_imports
from concordance_detail import aggregate_to_bea_detail, build_detail_concordance


# ── Step 1: Direct import shares (detail) ────────────────────────────────────

def detail_step1_import_shares(supply_xlsx: str, year: int = 2017) -> pd.DataFrame:
    """Direct import share m_i per BEA detail commodity from the Supply table.

    m_i = imports(i) / total_supply(i)

    Parses the Supply_2017_DET.xlsx file.  Row 5 contains column codes;
    row 6 onward contains data.  Column 'MCIF' = imports, 'T013' = total supply.

    Returns DataFrame with columns:
        bea_detail, bea_detail_desc, imports, total_supply, import_share
    """
    # Row 6 (0-indexed: skiprows=5) has column codes (Code, commodity codes, MCIF, T013, ...)
    header = pd.read_excel(
        supply_xlsx, sheet_name=str(year), header=None,
        skiprows=5, nrows=1, engine="openpyxl",
    )
    col_codes = [str(v).strip() if pd.notna(v) else "" for v in header.iloc[0]]

    # Row 7 onward is data
    data = pd.read_excel(
        supply_xlsx, sheet_name=str(year), header=None,
        skiprows=6, engine="openpyxl",
    )
    data.columns = col_codes

    df = data[["Code", "Commodity Description", "MCIF", "T013"]].copy()
    df.columns = ["bea_detail", "bea_detail_desc", "imports", "total_supply"]
    df["bea_detail"] = df["bea_detail"].astype(str).str.strip()
    df = df[~df["bea_detail"].isin({"nan", "None", "", "T017"})]
    df = df[~df["bea_detail"].str.startswith("Note")]

    df["imports"] = pd.to_numeric(df["imports"], errors="coerce").fillna(0)
    df["total_supply"] = pd.to_numeric(df["total_supply"], errors="coerce")
    df["import_share"] = df["imports"] / df["total_supply"].replace(0, float("nan"))

    return df.reset_index(drop=True)


# ── Steps 2–3: Leontief inverse (detail, pre-computed) ──────────────────────

def detail_step2_3_leontief(
    cxc_tr_xlsx: str,
    year: int = 2017,
) -> tuple:
    """Load the BEA pre-computed Commodity-by-Commodity Total Requirements matrix.

    This is BEA's official Leontief inverse at the 402-commodity detail level.
    No matrix inversion is needed — BEA computes it using the proper Make/Use
    framework with the market share matrix D.

    Parses CxC_TR_2017_PRO_DET.xlsx.  Row 5 has column codes, row 6+ has data.
    Excludes the T010 (total) row.

    Returns (commodities, L):
        commodities : list of BEA detail commodity codes
        L           : np.ndarray (n, n) Leontief inverse
    """
    # Row 5 (0-indexed: skiprows=4) has column codes (Code, Commodity Description, 1111A0, ...)
    header = pd.read_excel(
        cxc_tr_xlsx, sheet_name=str(year), header=None,
        skiprows=4, nrows=1, engine="openpyxl",
    )
    col_codes = [str(v).strip() if pd.notna(v) else "" for v in header.iloc[0]]

    # Row 6 onward is data
    data = pd.read_excel(
        cxc_tr_xlsx, sheet_name=str(year), header=None,
        skiprows=5, engine="openpyxl",
    )
    data.columns = col_codes

    # Row codes are in column 'Code'
    data["Code"] = data["Code"].astype(str).str.strip()

    # Exclude totals row (T010) and any non-commodity rows
    data = data[~data["Code"].isin({"T010", "nan", "None", ""})]

    # Column commodity codes (skip 'Code' and 'Commodity Description')
    commodity_cols = [c for c in col_codes[2:] if c not in {"nan", "None", ""}]

    # Ensure row order matches column order
    commodities = commodity_cols
    data = data.set_index("Code").reindex(commodities)

    L = data[commodities].apply(pd.to_numeric, errors="coerce").fillna(0).values

    print(f"Detail Leontief: {L.shape[0]} commodities, "
          f"diagonal range [{L.diagonal().min():.3f}, {L.diagonal().max():.3f}]")

    return commodities, L


# ── Step 4: Total import content (detail) ────────────────────────────────────

def detail_step4_total_import_content(
    import_shares: pd.DataFrame,
    commodities: list,
    L: np.ndarray,
) -> tuple:
    """Total import content per commodity via Leontief: m_total = m' L.

    Returns (m_vec, m_total):
        m_vec   : np.ndarray (n,) direct import shares aligned to `commodities`
        m_total : np.ndarray (n,) total (direct + indirect) import content
    """
    m_vec = (
        import_shares.set_index("bea_detail")
        .reindex(commodities)["import_share"]
        .fillna(0)
        .values
    )
    m_total = m_vec @ L
    return m_vec, m_total


# ── PCE Bridge (detail) ─────────────────────────────────────────────────────

def load_detail_pce_bridge(pce_bridge_xlsx: str, year: int = 2017) -> pd.DataFrame:
    """Load the detail PCE Bridge table.

    Returns DataFrame with columns:
        NIPA_line, PCE_category, commodity_code, commodity_descr,
        producers_value, transport_costs, wholesale, retail,
        purchasers_value, year
    """
    df = pd.read_excel(
        pce_bridge_xlsx,
        sheet_name=str(year),
        engine="openpyxl",
        skiprows=4,
        header=None,
        names=[
            "NIPA_line", "PCE_category", "commodity_code", "commodity_descr",
            "producers_value", "transport_costs", "wholesale", "retail",
            "purchasers_value", "year",
        ],
    )
    df["commodity_code"] = df["commodity_code"].astype(str).str.strip()
    df["PCE_category"] = df["PCE_category"].astype(str).str.strip()
    df = df[
        ~df["commodity_code"].isin({"nan", "None", ""})
        & ~df["PCE_category"].isin({"nan", "None", ""})
    ]
    df["producers_value"] = pd.to_numeric(df["producers_value"], errors="coerce")
    df["purchasers_value"] = pd.to_numeric(df["purchasers_value"], errors="coerce")
    return df.reset_index(drop=True)


# ── Step 5: Delta tariff per BEA detail commodity ────────────────────────────

def detail_step5_delta_tariff(
    imports_file: str,
    baseline_year: int,
    current_month: str,
    concordance_xlsx: str,
) -> pd.DataFrame:
    """Δτ = τ_current − τ_baseline per BEA detail commodity.

    Baseline = annual average over all 12 months of baseline_year.
    Current  = single month current_month ('YYYY-MM').

    Returns DataFrame with columns:
        bea_detail, bea_detail_desc, tau_base, tau, delta_tariff, imports, duties
    """
    df = load_naics_imports(imports_file)

    dates_baseline = [f"{baseline_year}-{str(m).zfill(2)}" for m in range(1, 13)]
    rates_baseline = compute_effective_tariff_rates(df, dates_baseline)
    rates_current = compute_effective_tariff_rates(df, [current_month])

    concordance = build_detail_concordance(
        rates_current["naics6"].tolist(),
        concordance_xlsx,
    )
    df_baseline = aggregate_to_bea_detail(rates_baseline, concordance)
    df_current = aggregate_to_bea_detail(rates_current, concordance)

    # Annual average: pool all 12 months then divide once
    baseline_avg = (
        df_baseline
        .groupby("bea_detail")[["duties", "imports"]]
        .sum()
        .reset_index()
        .assign(tau_base=lambda x: x["duties"] / x["imports"].replace(0, float("nan")))
    )

    result = df_current[["bea_detail", "bea_detail_desc", "tau", "imports", "duties"]].merge(
        baseline_avg[["bea_detail", "tau_base"]], on="bea_detail", how="left"
    )
    result["delta_tariff"] = result["tau"] - result["tau_base"]
    return result.reset_index(drop=True)


# ── Step 6: Predicted PCE price effect (detail) ─────────────────────────────

def detail_step6_pce_effect(
    commodities: list,
    m_vec: np.ndarray,
    L: np.ndarray,
    delta_tariff_df: pd.DataFrame,
    pce_bridge: pd.DataFrame,
    markup: str = "constant_dollar",
) -> pd.DataFrame:
    """Predicted tariff effect aggregated to PCE categories (402-commodity detail).

    Same algebra as pipeline.step6_pce_effect:
        p̂_j = Σ_i m_i · Δτ_i · L_ij
        P̂_k = Σ_j p̂_j · weight_jk / Σ_j purchasers_value_jk

    markup:
        "constant_dollar"  — weight = producers_value (conservative)
        "constant_percent" — weight = purchasers_value

    Returns DataFrame with columns:
        PCE_category, predicted_effect, producers_value_total, purchasers_value_total
    """
    if markup not in ("constant_dollar", "constant_percent"):
        raise ValueError(f"markup must be 'constant_dollar' or 'constant_percent', got '{markup}'")

    tau_series = (
        delta_tariff_df.set_index("bea_detail")["delta_tariff"]
        .reindex(commodities)
        .fillna(0)
    )

    tariff_weighted_imports = m_vec * tau_series.values
    predicted_effect_arr = tariff_weighted_imports @ L
    predicted_effect_series = pd.Series(predicted_effect_arr, index=commodities)

    bridge = pce_bridge.copy()
    bridge["predicted_effect"] = bridge["commodity_code"].map(predicted_effect_series)

    weight_col = "producers_value" if markup == "constant_dollar" else "purchasers_value"
    bridge["effect_dollars"] = bridge["predicted_effect"] * bridge[weight_col]

    pce_effect = bridge.groupby("PCE_category")["effect_dollars"].sum()
    pce_pv_total = bridge.groupby("PCE_category")["producers_value"].sum()
    pce_purc_total = bridge.groupby("PCE_category")["purchasers_value"].sum()
    denom = bridge.groupby("PCE_category")["purchasers_value"].sum()

    result = pd.DataFrame({
        "predicted_effect": pce_effect / denom,
        "producers_value_total": pce_pv_total,
        "purchasers_value_total": pce_purc_total,
    }).dropna(subset=["predicted_effect"]).sort_values("predicted_effect", ascending=False)

    return result.reset_index()


# ── Detail → Summary PCE aggregation ─────────────────────────────────────────

# Maps each detail-level PCE category to the corresponding summary-level
# category used in config.CORE_GOODS_CATEGORIES.  Built from the NIPA line
# hierarchy in PCEBridge_Detail.xlsx.
DETAIL_TO_SUMMARY_PCE = {
    "Accessories and parts": "Motor vehicle parts and accessories",
    "Audio discs, tapes, vinyl, and permanent digital downloads": "Video, audio, photographic, and information processing equipment and media",
    "Audio equipment": "Video, audio, photographic, and information processing equipment and media",
    "Bicycles and accessories": "Sports and recreational vehicles",
    "Calculators, typewriters, and other information processing equipment": "Video, audio, photographic, and information processing equipment and media",
    "Carpets and other floor coverings": "Furniture and furnishings",
    "Children's and infants' clothing": "Children's and infants' clothing",
    "Clocks, lamps, lighting fixtures, and other household decorative items": "Furniture and furnishings",
    "Clothing materials": "Other clothing materials and footwear",
    "Computer software and accessories": "Video, audio, photographic, and information processing equipment and media",
    "Corrective eyeglasses and contact lenses": "Therapeutic appliances and equipment",
    "Cosmetic/perfumes/bath/nail preparations and implements": "Personal care products",
    "Dishes and flatware": "Glassware, tableware, and household utensils",
    "Educational books": "Educational books",
    "Electric appliances for personal care": "Personal care products",
    "Film and photographic supplies": "Recreational items",
    "Flowers, seeds, and potted plants": "Recreational items",
    "Furniture": "Furniture and furnishings",
    "Games, toys, and hobbies": "Recreational items",
    "Hair, dental, shaving, and miscellaneous personal care products except electrical products": "Personal care products",
    "Household cleaning products": "Household supplies",
    "Household linens": "Household supplies",
    "Household paper products": "Household supplies",
    "Jewelry": "Jewelry and watches",
    "Luggage and similar personal items": "Luggage and similar personal items",
    "Major household appliances": "Household appliances",
    "Men's and boys' clothing": "Men's and boys' clothing",
    "Miscellaneous household products": "Household supplies",
    "Motorcycles": "Sports and recreational vehicles",
    "Musical instruments": "Musical instruments",
    "New domestic autos": "New motor vehicles",
    "New foreign autos": "New motor vehicles",
    "New light trucks": "New motor vehicles",
    "Newspapers and periodicals": "Magazines, newspapers, and stationery",
    "Nonelectric cookware and tableware": "Glassware, tableware, and household utensils",
    "Other medical products": "Pharmaceutical and other medical products",
    "Other recreational vehicles": "Sports and recreational vehicles",
    "Other video equipment": "Video, audio, photographic, and information processing equipment and media",
    "Outdoor equipment and supplies": "Tools and equipment for house and garden",
    "Personal computers/tablets and peripheral equipment": "Video, audio, photographic, and information processing equipment and media",
    "Pets and related products": "Recreational items",
    "Pharmaceutical products": "Pharmaceutical and other medical products",
    "Photographic equipment": "Video, audio, photographic, and information processing equipment and media",
    "Pleasure aircraft": "Sports and recreational vehicles",
    "Pleasure boats": "Sports and recreational vehicles",
    "Recreational books": "Recreational books",
    "Sewing items": "Household supplies",
    "Shoes and other footwear": "Other clothing materials and footwear",
    "Small electric household appliances": "Household appliances",
    "Sporting equipment, supplies, guns, and ammunition": "Sporting equipment, supplies, guns, and ammunition",
    "Standard clothing issued to military personnel": "Other clothing materials and footwear",
    "Stationery and miscellaneous printed materials": "Magazines, newspapers, and stationery",
    "Telephone and related communication equipment": "Telephone and related communication equipment",
    "Televisions": "Video, audio, photographic, and information processing equipment and media",
    "Therapeutic medical equipment": "Therapeutic appliances and equipment",
    "Tires": "Motor vehicle parts and accessories",
    "Tobacco": "Tobacco",
    "Tools, hardware, and supplies": "Tools and equipment for house and garden",
    "Used autos": "Net purchases of used motor vehicles",
    "Used light trucks": "Net purchases of used motor vehicles",
    "Video discs, tapes, and permanent digital downloads": "Video, audio, photographic, and information processing equipment and media",
    "Watches": "Jewelry and watches",
    "Window coverings": "Furniture and furnishings",
    "Women's and girls' clothing": "Women's and girls' clothing",
    # Energy categories (detail → summary)
    "Fuel oil": "Fuel oil and other fuels",
    "Other fuels": "Fuel oil and other fuels",
    "Gasoline and other motor fuel": "Motor vehicle fuels, lubricants, and fluids",
    "Lubricants and fluids": "Motor vehicle fuels, lubricants, and fluids",
    "Electricity": "Electricity",
    "Natural gas": "Natural gas",
    # Food categories (detail → summary)
    "Cereals": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Bakery products": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Beef and veal": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Pork": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Other meats": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Poultry": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Fish and seafood": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Fresh milk": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Processed dairy products": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Eggs": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Fats and oils": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Fruit (fresh)": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Vegetables (fresh)": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Processed fruits and vegetables": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Sugar and sweets": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Food products, not elsewhere classified": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Coffee, tea, and other beverage materials": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Mineral waters, soft drinks, and vegetable juices": "Food and nonalcoholic beverages purchased for off-premises consumption",
    "Spirits": "Alcoholic beverages purchased for off-premises consumption",
    "Wine": "Alcoholic beverages purchased for off-premises consumption",
    "Beer": "Alcoholic beverages purchased for off-premises consumption",
    "Food produced and consumed on farms": "Food produced and consumed on farms",
    "Meals at limited service eating places": "Purchased meals and beverages",
    "Meals at other eating places": "Purchased meals and beverages",
    "Meals at drinking places": "Purchased meals and beverages",
    "Alcohol in purchased meals": "Purchased meals and beverages",
    "Food furnished to employees (including military)": "Food furnished to employees",
}


def aggregate_to_summary_pce(
    detail_pce_effect: pd.DataFrame,
) -> pd.DataFrame:
    """Aggregate detail-level PCE effects to the 27 summary core goods categories.

    Uses purchasers_value weighting to combine detail categories into their
    summary parents.

    Parameters
    ----------
    detail_pce_effect : pd.DataFrame
        Output of detail_step6_pce_effect().

    Returns
    -------
    pd.DataFrame with same columns as input but grouped to summary categories.
    """
    df = detail_pce_effect.copy()
    df["summary_category"] = df["PCE_category"].map(DETAIL_TO_SUMMARY_PCE)

    # Keep only rows that map to a summary category
    mapped = df.dropna(subset=["summary_category"]).copy()

    # Weighted aggregation: effect = Σ(effect_i × puv_i) / Σ(puv_i)
    mapped["effect_x_puv"] = mapped["predicted_effect"] * mapped["purchasers_value_total"]

    summary = (
        mapped
        .groupby("summary_category")
        .agg(
            effect_x_puv=("effect_x_puv", "sum"),
            producers_value_total=("producers_value_total", "sum"),
            purchasers_value_total=("purchasers_value_total", "sum"),
        )
        .reset_index()
    )
    summary["predicted_effect"] = summary["effect_x_puv"] / summary["purchasers_value_total"]
    summary = summary.drop(columns=["effect_x_puv"])
    summary = summary.rename(columns={"summary_category": "PCE_category"})
    return summary.sort_values("predicted_effect", ascending=False).reset_index(drop=True)
