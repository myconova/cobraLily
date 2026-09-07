import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
fred_api_key = os.getenv("FRED_API_KEY")

if not fred_api_key:
    raise ValueError("FRED_API_KEY not found in environment. Please check your .env file.")

FRED_BASE_URL = "https://api.stlouisfed.org/fred/"
FRED_OBS_ENDPOINT = "series/observations"
DXY_SERIES_ID = "DTWEXBGS"


def fetch_fred_series(series_id, api_key):
    url = f"{FRED_BASE_URL}{FRED_OBS_ENDPOINT}"
    params = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "frequency": "d",
        "units": "lin",
    }
    response = requests.get(url, params=params)
    response.raise_for_status()

    data = response.json()
    dxy_df = pd.DataFrame(data["observations"])[["date", "value"]]

    dxy_df["date"] = pd.to_datetime(dxy_df["date"])
    dxy_df["dxy_level"] = pd.to_numeric(
        dxy_df["value"],
        errors="coerce",
    )
    return dxy_df.set_index("date")[["dxy_level"]]

dxy_df = fetch_fred_series(DXY_SERIES_ID, fred_api_key)

dxy_df["dxy_roc_14d"] = dxy_df["dxy_level"].pct_change(14) * 100

dxy_df["dxy_stress_2pct"] = dxy_df["dxy_roc_14d"] > 2

print(dxy_df.tail())


