# compute_tariff_rates.py

import pandas as pd
import pyarrow.parquet as pq

def load_naics_imports(parquet_path: str) -> pd.DataFrame:
    """
    Load the Census NAICS imports parquet file and clean types.
    """
    df = pq.read_table(parquet_path).to_pandas()
    df['imports'] = pd.to_numeric(df['CON_VAL_MO'], errors='coerce')
    df['duties']  = pd.to_numeric(df['CAL_DUT_MO'],  errors='coerce')
    df['time']    = pd.to_datetime(df['time'])
    df['naics6']  = df['NAICS'].astype(str).str.zfill(6)
    return df


from typing import Union, List

def compute_effective_tariff_rates(
    df,
    dates,  # str or list of str, e.g. '2025-07' or ['2025-04', '2025-07']
):
    if isinstance(dates, str):
        dates = [dates]

    date_list = [pd.to_datetime(d) for d in dates]

    mask = df['time'].isin(date_list)
    subset = df[mask].copy()

    if subset.empty:
        available = df['time'].dt.strftime('%Y-%m').unique()
        raise ValueError(
            f"No data found for {dates}. "
            f"Available range: {sorted(available)[0]} to {sorted(available)[-1]}"
        )

    result = (
        subset
        .groupby(['naics6', 'NAICS_SDESC', 'time'])[['duties', 'imports']]
        .sum()
        .reset_index()
        .assign(tau=lambda x: x['duties'] / x['imports'].replace(0, float('nan')))
        .sort_values(['time', 'naics6'])
        .reset_index(drop=True)
    )

    found_dates = result['time'].dt.strftime('%Y-%m').unique()
    missing = [d for d in dates if d not in found_dates]
    if missing:
        print(f"Warning: no data found for dates: {missing}")

    return result[['naics6', 'NAICS_SDESC', 'time', 'imports', 'duties', 'tau']]