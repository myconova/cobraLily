import os
import requests
import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()
fred_api_key = os.getenv("FRED_API_KEY")

if not fred_api_key:
    raise ValueError("FRED_API_KEY not found in environment. Please check your .env file.")

DBNOMICS_BASE_URL = "https://api.db.nomics.world/v22"
CHINA_M2_SERIES = "NBS/M_A0D01/A0D0101"
FRED_BASE_URL = "https://api.stlouisfed.org/fred/"
FRED_OBSERVATIONS_ENDPOINT = "series/observations"


def fetch_dbnomics_series(series_path):
    url = f"{DBNOMICS_BASE_URL}/series/{series_path}"
    response = requests.get(url, params={"observations": 1})
    response.raise_for_status()

    data = response.json()
    series = data["series"]["docs"][0]

    china_m2_df = pd.DataFrame(
        {
            "date": series["period"],
            "china_m2_100m_cny": series["value"],
        }
    )

    china_m2_df["date"] = pd.to_datetime(china_m2_df["date"])
    china_m2_df["china_m2_100m_cny"] = pd.to_numeric(
        china_m2_df["china_m2_100m_cny"],
        errors="coerce",
    )
    return china_m2_df.set_index("date")


def fetch_fred_series(series_id, api_key):
    url = f"{FRED_BASE_URL}{FRED_OBSERVATIONS_ENDPOINT}"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "frequency": "m",
        "units": "lin",
    }
    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    fred_df = pd.DataFrame(data["observations"])[["date", "value"]]

    fred_df["date"] = pd.to_datetime(fred_df["date"])
    fred_df["cny_per_usd"] = pd.to_numeric(
        fred_df["value"],
        errors="coerce",
    )
    return fred_df.set_index("date")[["cny_per_usd"]]


china_m2_df = fetch_dbnomics_series(CHINA_M2_SERIES)
cny_fx_df = fetch_fred_series("EXCHUS", fred_api_key)

china_df = china_m2_df.join(cny_fx_df, how="inner")

china_df["china_m2_yoy_growth"] = (
    china_df["china_m2_100m_cny"].pct_change(12) * 100
)

china_df["rmb_fx_pressure_3m"] = (
    china_df["cny_per_usd"].pct_change(3) * 100
)

china_df["china_m2_impulse"] = (
    china_df["china_m2_yoy_growth"] - china_df["china_m2_yoy_growth"].shift(3)
)

conditions = [
    (china_df["china_m2_impulse"] > 0)
    & (china_df["rmb_fx_pressure_3m"] <= 0),
    (china_df["china_m2_impulse"] > 0)
    & (china_df["rmb_fx_pressure_3m"] > 0),
    (china_df["china_m2_impulse"] <= 0)
    & (china_df["rmb_fx_pressure_3m"] <= 0),
    (china_df["china_m2_impulse"] <= 0)
    & (china_df["rmb_fx_pressure_3m"] > 0),
]

choices = [
    "Accelerating M2, Low FX Pressure",
    "Accelerating M2, High FX Pressure",
    "Decelerating M2, Low FX Pressure",
    "Decelerating M2, High FX Pressure",
]

china_df["china_liquidity_regime"] = np.select(
    conditions,
    choices,
    default="Unknown",
)

print(china_df.tail())




