import os
import requests
import pandas as pd
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



