"""
concordance_detail.py — NAICS6 → BEA 402-commodity detail concordance.

Parses BEA's official Industry-and-Commodity-Codes-and-NAICS-Concordance file
to map 6-digit Census NAICS codes to BEA detail commodity codes used in the
402-commodity IO tables.

The concordance uses longest-prefix matching: each Census NAICS6 code is
matched to the BEA detail code whose NAICS prefix is the longest match.
"""

from typing import Optional

import pandas as pd


def _load_bea_naics_to_detail(xlsx_path: str) -> pd.DataFrame:
    """Parse the BEA concordance Excel file into (naics_prefix, bea_detail, description) rows.

    Returns DataFrame with columns: naics_prefix, bea_detail, bea_detail_desc
    """
    raw = pd.read_excel(
        xlsx_path,
        sheet_name=0,
        header=None,
        skiprows=5,
        engine="openpyxl",
    )
    # Columns: 0=Sector, 1=Desc, 2=Summary, 3=Desc, 4=U.Summary, 5=Desc,
    #          6=Detail, 7=Desc, 8=GO Detail, 9=Desc, 10=Notes,
    #          11=Related 2017 NAICS, 12=NAICS Desc
    df = raw[[6, 7, 11]].copy()
    df.columns = ["bea_detail", "bea_detail_desc", "naics_prefix"]
    df = df.dropna(subset=["bea_detail", "naics_prefix"])
    df["bea_detail"] = df["bea_detail"].astype(str).str.strip()
    df["bea_detail_desc"] = df["bea_detail_desc"].astype(str).str.strip()
    df["naics_prefix"] = df["naics_prefix"].astype(str).str.strip()
    return df.reset_index(drop=True)


def _build_prefix_lookup(concordance_raw: pd.DataFrame) -> dict:
    """Build a dict mapping each NAICS prefix string to (bea_detail, description).

    Longer prefixes take priority when multiple entries exist for overlapping ranges.
    """
    lookup = {}
    for _, row in concordance_raw.iterrows():
        prefix = row["naics_prefix"]
        bea = row["bea_detail"]
        desc = row["bea_detail_desc"]
        lookup[prefix] = (bea, desc)
    return lookup


def _match_naics6(naics6: str, prefix_lookup: dict) -> tuple:
    """Find the longest-prefix match for a 6-digit NAICS code.

    Tries prefixes from length 6 down to 2.
    Returns (bea_detail, description) or (None, None) if no match.
    """
    for length in range(6, 1, -1):
        prefix = naics6[:length]
        if prefix in prefix_lookup:
            return prefix_lookup[prefix]
    return (None, None)


def build_detail_concordance(
    naics6_list: list,
    xlsx_path: str,
) -> pd.DataFrame:
    """Build a concordance mapping NAICS6 codes to BEA 402-commodity detail codes.

    Parameters
    ----------
    naics6_list : list of str
        All NAICS6 codes present in the tariff data.
    xlsx_path : str
        Path to BEA-Industry-and-Commodity-Codes-and-NAICS-Concordance.xlsx

    Returns
    -------
    pd.DataFrame with columns:
        naics6        : 6-digit NAICS code (zero-padded string)
        bea_detail    : BEA detail commodity code (e.g. '336111')
        bea_detail_desc : commodity description
        in_scope      : bool, True if mappable
    """
    raw = _load_bea_naics_to_detail(xlsx_path)
    lookup = _build_prefix_lookup(raw)

    # Collect all valid BEA detail codes for scope filtering
    valid_bea_codes = set(raw["bea_detail"].unique())

    records = []
    for n in naics6_list:
        naics6 = str(n).zfill(6)
        bea, desc = _match_naics6(naics6, lookup)
        records.append({
            "naics6": naics6,
            "bea_detail": bea,
            "bea_detail_desc": desc if desc else "Unmapped",
            "in_scope": bea is not None,
        })

    concordance = pd.DataFrame(records)

    n_total = len(concordance)
    n_mapped = concordance["in_scope"].sum()
    n_unmapped = n_total - n_mapped
    n_industries = concordance.loc[concordance["in_scope"], "bea_detail"].nunique()

    print(
        f"Detail concordance: {n_mapped}/{n_total} NAICS6 codes mapped "
        f"to BEA detail commodities"
    )
    print(f"  Out of scope (services/unmapped): {n_unmapped} codes")
    print(f"  BEA detail commodities covered: {n_industries}")

    return concordance


def aggregate_to_bea_detail(
    tariff_df: pd.DataFrame,
    concordance: pd.DataFrame,
) -> pd.DataFrame:
    """Merge concordance onto tariff rates and aggregate to BEA detail commodity level.

    Same logic as concordance.aggregate_to_bea() but targeting 402-commodity codes.

    Parameters
    ----------
    tariff_df : pd.DataFrame
        Output of compute_effective_tariff_rates(), with columns:
        naics6, NAICS_SDESC, time, imports, duties, tau
    concordance : pd.DataFrame
        Output of build_detail_concordance().

    Returns
    -------
    pd.DataFrame with columns:
        bea_detail, bea_detail_desc, time, imports, duties, tau
    """
    merged = tariff_df.merge(concordance, on="naics6", how="left")

    total_imports = merged["imports"].sum()
    mapped_imports = merged.loc[merged["in_scope"] == True, "imports"].sum()
    print(
        f"\nImport value coverage: {mapped_imports / total_imports * 100:.1f}% "
        f"of total import value mapped to BEA detail commodities"
    )

    in_scope = merged[merged["in_scope"] == True].copy()

    bea_rates = (
        in_scope
        .groupby(["bea_detail", "bea_detail_desc", "time"])[["duties", "imports"]]
        .sum()
        .reset_index()
        .assign(tau=lambda x: x["duties"] / x["imports"].replace(0, float("nan")))
        .sort_values(["time", "bea_detail"])
        .reset_index(drop=True)
    )

    return bea_rates
