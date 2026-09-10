import sys
from pathlib import Path

import pandas as pd
import yfinance as yf

from dxy import DXY_SERIES_ID, fetch_fred_series, fred_api_key

SWAMP_WATER_DIR = Path(__file__).resolve().parents[1] / "swampWater"
sys.path.insert(0, str(SWAMP_WATER_DIR))
from m2_bitcoin_backtest import fetch_monthly_bitcoin_prices

# Fetch and calculate DXY stress
dxy_df = fetch_fred_series(DXY_SERIES_ID, fred_api_key)

dxy_df["dxy_roc_14d"] = dxy_df["dxy_level"].pct_change(14) * 100
dxy_df["dxy_stress_1pct"] = dxy_df["dxy_roc_14d"] > 1
dxy_df["dxy_stress_2pct"] = dxy_df["dxy_roc_14d"] > 2
dxy_df["dxy_stress_3pct"] = dxy_df["dxy_roc_14d"] > 3

# Convert daily DXY to monthly signals
monthly_dxy = dxy_df.resample("MS").last()

# Fetch bitcoin and align everything
bitcoin_df = fetch_monthly_bitcoin_prices()

backtest_df = bitcoin_df.join(
    monthly_dxy[
        [
            "dxy_roc_14d",
            "dxy_stress_1pct",
            "dxy_stress_2pct",
            "dxy_stress_3pct",
        ]
    ],
    how="inner",
)

# Calculate bitcoin forward returns
for months in [1, 3, 6, 9]:
    backtest_df[f"bitcoin_return_{months}m"] = (
        backtest_df["bitcoin_close"].shift(-months)
        / backtest_df["bitcoin_close"]
        - 1
    ) * 100

# Calculate re-entry rates for each threshold
for threshold in [1, 2, 3]:
    stress_column = f"dxy_stress_{threshold}pct"

    for months in [1, 3, 6, 9]:
        return_column = f"bitcoin_return_{months}m"
        reentry_column = f"reentry_{threshold}pct_{months}m"

        backtest_df[reentry_column] = (
            backtest_df[return_column] < 0 
        ).where(backtest_df[return_column].notna())

    summary_columns = [
        f"reentry_{threshold}pct_{months}m"
        for months in [1, 3, 6, 9]
    ]

    summary = (
        backtest_df.loc[backtest_df[stress_column]]
        [summary_columns]
        .mean()
        .mul(100)
        .round(2)
    )

    print(f"\nDXY stress threshold: {threshold}%")
    print(summary)
    print(f"Observations: {backtest_df[stress_column].sum()}")
