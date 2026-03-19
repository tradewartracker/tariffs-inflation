# concordance.py

import re
from typing import Optional

import pandas as pd

# ── NAICS3 → BEA IO mapping ───────────────────────────────────────────────────
# For most sectors, the first 3 digits of NAICS6 determine the BEA IO code.
# Exceptions handled separately below (336xx split, combined codes).

NAICS3_TO_BEA = {
    # Agriculture, forestry, fishing
    '111': '111CA', '112': '111CA',
    '113': '113FF', '114': '113FF', '115': '113FF',
    # Mining
    '211': '211',
    '212': '212',
    '213': '213',
    # Manufacturing — simple 1-to-1
    '321': '321',
    '322': '322',
    '323': '323',
    '324': '324',
    '325': '325',
    '326': '326',
    '327': '327',
    '331': '331',
    '332': '332',
    '333': '333',
    '334': '334',
    '335': '335',
    '337': '337',
    '339': '339',
    # Manufacturing — combined BEA codes (multiple NAICS3 → one BEA IO)
    '311': '311FT', '312': '311FT',   # Food, beverage & tobacco
    '313': '313TT', '314': '313TT',   # Textile mills & products
    '315': '315AL', '316': '315AL',   # Apparel & leather
    # 336 is handled separately below via NAICS4 override
}

# Within NAICS 336, BEA splits into motor vehicles vs. other transport
# This requires looking at NAICS4, not just NAICS3
NAICS4_336_TO_BEA = {
    '3361': '3361MV',   # Motor vehicles
    '3362': '3361MV',   # Motor vehicle bodies & trailers
    '3363': '3361MV',   # Motor vehicle parts
    '3364': '3364OT',   # Aerospace
    '3365': '3364OT',   # Railroad rolling stock
    '3366': '3364OT',   # Ships & boats
    '3369': '3364OT',   # Other transport equipment
}

BEA_DESCRIPTIONS = {
    '111CA': 'Farms',
    '113FF': 'Forestry, fishing, and related activities',
    '211':   'Oil and gas extraction',
    '212':   'Mining, except oil and gas',
    '213':   'Support activities for mining',
    '311FT': 'Food and beverage and tobacco products',
    '313TT': 'Textile mills and textile product mills',
    '315AL': 'Apparel and leather and allied products',
    '321':   'Wood products',
    '322':   'Paper products',
    '323':   'Printing and related support activities',
    '324':   'Petroleum and coal products',
    '325':   'Chemical products',
    '326':   'Plastics and rubber products',
    '327':   'Nonmetallic mineral products',
    '331':   'Primary metals',
    '332':   'Fabricated metal products',
    '333':   'Machinery',
    '334':   'Computer and electronic products',
    '335':   'Electrical equipment, appliances, and components',
    '3361MV':'Motor vehicles, bodies and trailers, and parts',
    '3364OT':'Other transportation equipment',
    '337':   'Furniture and related products',
    '339':   'Miscellaneous manufacturing',
}


def _map_single(naics6):
    """Map a single NAICS6 string to a BEA IO code. Returns None if out of scope."""
    n = str(naics6).zfill(6)
    if n.startswith('336'):
        return NAICS4_336_TO_BEA.get(n[:4])
    return NAICS3_TO_BEA.get(n[:3])


def _normalize_naics6(value) -> str:
    """Normalize any NAICS-like value into a 6-digit code string."""
    digits = re.sub(r"\D", "", str(value))
    return digits[:6].zfill(6)


def _normalize_bea_code(value) -> str:
    """Normalize BEA IO codes read from external files."""
    code = str(value).strip()
    code = re.sub(r"\.0$", "", code)
    return code


def _load_external_concordance_mapping(bea_concordance_file: str) -> dict:
    """Load a NAICS6 -> BEA mapping from a user-provided CSV/XLSX file."""
    path = bea_concordance_file.strip()
    lower = path.lower()

    if lower.endswith(".csv"):
        raw = pd.read_csv(path)
    elif lower.endswith((".xlsx", ".xls")):
        raw = pd.read_excel(path)
    else:
        raise ValueError(
            "Unsupported concordance file format. Use .csv, .xlsx, or .xls. "
            f"Got: {bea_concordance_file}"
        )

    norm_cols = {
        c: re.sub(r"[^a-z0-9]", "", str(c).lower())
        for c in raw.columns
    }

    naics_candidates = {
        "naics6", "naics", "naicscode", "naics2017", "relatednaics",
        "sourceindustry", "sourcecode",
    }
    bea_candidates = {
        "beaio", "beaiocode", "beacode", "iocode", "summaryiocode",
        "commoditycode", "targetindustry", "targetcode",
    }

    naics_col = next((c for c, n in norm_cols.items() if n in naics_candidates), None)
    bea_col = next((c for c, n in norm_cols.items() if n in bea_candidates), None)

    if naics_col is None or bea_col is None:
        available = ", ".join(str(c) for c in raw.columns)
        raise ValueError(
            "Could not infer NAICS/BEA columns from concordance file. "
            "Expected NAICS-like and BEA-like columns. "
            f"Available columns: {available}"
        )

    mapping_df = raw[[naics_col, bea_col]].copy()
    mapping_df.columns = ["naics6", "bea_io"]
    mapping_df["naics6"] = mapping_df["naics6"].map(_normalize_naics6)
    mapping_df["bea_io"] = mapping_df["bea_io"].map(_normalize_bea_code)
    mapping_df = mapping_df.dropna(subset=["naics6", "bea_io"])

    # Keep only BEA industries used by this project's IO summary design.
    mapping_df = mapping_df[mapping_df["bea_io"].isin(BEA_DESCRIPTIONS)]

    conflicts = (
        mapping_df.groupby("naics6")["bea_io"]
        .nunique()
        .loc[lambda s: s > 1]
    )
    if not conflicts.empty:
        print(
            "Warning: external concordance has NAICS6 codes mapping to multiple "
            "BEA industries. Keeping the first non-null mapping per NAICS6."
        )

    mapping_df = mapping_df.drop_duplicates(subset=["naics6"], keep="first")
    return mapping_df.set_index("naics6")["bea_io"].to_dict()


def build_concordance(
    naics6_list,
    method: str = "manual",
    bea_concordance_file: Optional[str] = None,
    fallback_to_manual_unmapped: bool = False,
):
    """
    Build a concordance dataframe mapping NAICS6 codes to BEA IO industries.

    Parameters
    ----------
    naics6_list : list of str
        All NAICS6 codes present in your tariff data.
    method : str
        "manual" (default): built-in mapping rules from this repo.
        "bea_file": mapping loaded from `bea_concordance_file`.
    bea_concordance_file : str, optional
        Path to an external concordance file (.csv/.xlsx/.xls) when
        method="bea_file".
    fallback_to_manual_unmapped : bool
        If True with method="bea_file", any NAICS6 code not present in the
        external file falls back to the built-in manual mapping.

    Returns
    -------
    pd.DataFrame with columns:
        naics6      : 6-digit NAICS code (zero-padded string)
        bea_io      : BEA IO industry code (None if out of scope)
        bea_desc    : BEA IO industry description
        in_scope    : bool, True if mappable to a BEA goods industry
    """
    if method not in {"manual", "bea_file"}:
        raise ValueError(f"Unknown concordance method '{method}'. Use 'manual' or 'bea_file'.")

    ext_mapping = None
    if method == "bea_file":
        if not bea_concordance_file:
            raise ValueError(
                "method='bea_file' requires bea_concordance_file to be set."
            )
        ext_mapping = _load_external_concordance_mapping(bea_concordance_file)

    records = []
    n_fallback = 0
    for n in naics6_list:
        naics6 = _normalize_naics6(n)
        if method == "manual":
            bea = _map_single(naics6)
        else:
            bea = ext_mapping.get(naics6)
            if bea is None and fallback_to_manual_unmapped:
                bea = _map_single(naics6)
                if bea is not None:
                    n_fallback += 1
        records.append({
            'naics6':   naics6,
            'bea_io':   bea,
            'bea_desc': BEA_DESCRIPTIONS.get(bea, 'Services / unmapped'),
            'in_scope': bea is not None,
        })

    concordance = pd.DataFrame(records)

    n_total    = len(concordance)
    n_mapped   = concordance['in_scope'].sum()
    n_unmapped = n_total - n_mapped

    covered_industries = concordance.loc[concordance['in_scope'], 'bea_io'].nunique()

    print(
        f"Concordance built ({method}): "
        f"{n_mapped}/{n_total} NAICS6 codes mapped to BEA IO industries"
    )
    if method == "bea_file" and fallback_to_manual_unmapped:
        print(f"  Manual fallback used for {n_fallback} unmapped NAICS6 codes")
    print(f"  Out of scope (services/unmapped): {n_unmapped} codes")
    print(f"  BEA IO industries covered: {covered_industries}")

    return concordance


def aggregate_to_bea(tariff_df, concordance):
    """
    Merge concordance onto tariff rates, aggregate to BEA IO level, then
    ensure every BEA IO goods industry appears in the output — even those
    with no tariff data — so downstream IO matrix multiplication is complete.

    Parameters
    ----------
    tariff_df : pd.DataFrame
        Output of compute_effective_tariff_rates(), with columns:
        naics6, NAICS_SDESC, time, imports, duties, tau
    concordance : pd.DataFrame
        Output of build_concordance().

    Returns
    -------
    pd.DataFrame with columns:
        bea_io, bea_desc, time, imports, duties, tau, tau_imputed
        tau_imputed : bool flag, True where tau was missing and filled with 0
    """
    merged = tariff_df.merge(concordance, on='naics6', how='left')

    # Flag any NAICS6 in tariff data not found in concordance at all
    no_match = merged['bea_io'].isna() & merged['in_scope'].isna()
    if no_match.any():
        print(f"Warning: {no_match.sum()} rows had no concordance match at all")

    # Coverage by import value
    total_imports  = merged['imports'].sum()
    mapped_imports = merged.loc[merged['in_scope'] == True, 'imports'].sum()
    print(f"\nImport value coverage: {mapped_imports / total_imports * 100:.1f}% "
          f"of total import value mapped to BEA IO industries")

    # Drop out-of-scope (services etc.) — safe because services carry near-zero
    # tariffs. Their indirect tariff exposure via inputs is handled in the
    # Leontief step using the full IO matrix, not here.
    in_scope = merged[merged['in_scope'] == True].copy()

    # Aggregate — sum duties and imports first, then divide
    bea_rates = (
        in_scope
        .groupby(['bea_io', 'bea_desc', 'time'])[['duties', 'imports']]
        .sum()
        .reset_index()
        .assign(tau=lambda x: x['duties'] / x['imports'].replace(0, float('nan')))
        .sort_values(['time', 'bea_io'])
        .reset_index(drop=True)
    )

    # ── Completeness check: ensure every BEA IO industry appears ─────────────
    # Left-join from the full BEA industry list so no industry is silently
    # absent in the downstream IO matrix step. Missing tau is flagged and
    # filled with 0 only after reporting so the user can inspect gaps.

    all_bea = pd.DataFrame({
        'bea_io':   list(BEA_DESCRIPTIONS.keys()),
        'bea_desc': list(BEA_DESCRIPTIONS.values()),
    })

    # For each date in the data, ensure all BEA industries are present
    dates     = bea_rates['time'].unique()
    date_grid = pd.DataFrame(
        [(b, d) for b in BEA_DESCRIPTIONS.keys() for d in dates],
        columns=['bea_io', 'time']
    )

    bea_rates_complete = (
        date_grid
        .merge(all_bea,    on='bea_io', how='left')
        .merge(bea_rates[['bea_io', 'time', 'imports', 'duties', 'tau']],
               on=['bea_io', 'time'], how='left')
    )

    # Flag imputed zeros
    bea_rates_complete['tau_imputed'] = bea_rates_complete['tau'].isna()

    missing = bea_rates_complete[bea_rates_complete['tau_imputed']]
    if not missing.empty:
        print(f"\nBEA IO industries with no tariff data (tau set to 0):")
        print(
            missing[['bea_io', 'bea_desc']]
            .drop_duplicates()
            .to_string(index=False)
        )

    # Fill missing tau, duties, imports with 0 after reporting
    bea_rates_complete['tau']     = bea_rates_complete['tau'].fillna(0.0)
    bea_rates_complete['duties']  = bea_rates_complete['duties'].fillna(0.0)
    bea_rates_complete['imports'] = bea_rates_complete['imports'].fillna(0.0)

    return bea_rates_complete[[
        'bea_io', 'bea_desc', 'time', 'imports', 'duties', 'tau', 'tau_imputed'
    ]]