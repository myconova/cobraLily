import os
import requests
import pandas as pd
import numpy as np  
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('FRED_API_KEY')

if not api_key:
    raise ValueError("FRED_API_KEY not found in environment. Please check your .env file."
                     )
# ---Backtesting Configuration Toggles ---
SCOPE = "US_ONLY"   # Options: "US_ONLY" or "GLOBAL_AGGREGATE"
IMPULSE_METHOD = "YOY_DELTA"   # Options: "YOY_DELTA" or "ANNUALIZED_SPREAD" (3M Ann - YoY)

# define the FRED API endpoint
BASE_URL = 'https://api.stlouisfed.org/fred/'
OBS_ENDPOINT = 'series/observations'

def fetch_fred_series(series_id, api_key, start_date='2000-01-01', end_date='2030-12-31'):
    '''
    Fetches raw level time series data from FRED API and returns a cleaned pandas DataFrame.
    '''
    url = f"{BASE_URL}{OBS_ENDPOINT}"
    params = {
        'series_id': series_id,
        'api_key': api_key,
        'file_type': 'json',
        'observation_start': start_date,
        'observation_end': end_date,
        'frequency': 'm',
        'units': 'lin'
    }
    response = requests.get(url, params=params)
    response.raise_for_status() 

    data = response.json()
    df = pd.DataFrame(data['observations'])[['date', 'value']]
    df['date'] = pd.to_datetime(df['date'])
    df[series_id] = pd.to_numeric(df['value'], errors='coerce')
    df = df.set_index('date')[[series_id]]
    return df

# --- STEP 1: FETCH DATA BASED ON SCOPE TOGGLE ---
if SCOPE == "US_ONLY":
    m2_df = fetch_fred_series('M2SL', api_key)
    m2_df = m2_df.rename(columns={'M2SL': 'm2_level'})

elif SCOPE == "GLOBAL_AGGREGATE":
    # 1. Fetch US, Euro Area, Japan, China M2 series
    us_m2 = fetch_fred_series('M2SL', api_key) # Billions USD
    ea_m2 = fetch_fred_series('MYAGM2EZM196N', api_key) # Millions EUR
    jp_m2 = fetch_fred_series('JPNCBMM2JPYM', api_key) # Billions JPY
    cn_m2 = fetch_fred_series('MYAGM2CNM189N', api_key) # Billions CNY

    # 2. Fetch exchange rates
    eur_usd = fetch_fred_series('DEXUSEU', api_key) # USD per 1 EUR
    jpy_usd = fetch_fred_series('DEXJPUS', api_key) # JPY per 1 USD
    cny_usd = fetch_fred_series('DEXCHUS', api_key) # CNY per 1 USD

    # 3. Combine into a single DataFrame and handle daily/monthly alignment
    global_df = pd.concat([us_m2, ea_m2, jp_m2, cn_m2, eur_usd, jpy_usd, cny_usd], axis=1)
    global_df = global_df.resample('ME').last().ffill().dropna()

    # 4. Currency conversions to Billions USD
    us_usd = global_df['M2SL'] # Already in Billions USD
    ea_usd = (global_df['MYAGM2EZM196N'] / 1000.0) * global_df['DEXUSEU'] # Convert Millions EUR to Billions USD
    jp_usd = global_df['JPNCBMM2JPYM'] / global_df['DEXJPUS'] # Convert Billions JPY to Billions USD
    cn_usd = global_df['MYAGM2CNM189N'] / global_df['DEXCHUS'] # Convert Billions CNY to Billions USD

    # 5. Sum into unified m2_level series
    m2_df = pd.DataFrame()
    m2_df['m2_level'] = us_usd + ea_usd + jp_usd + cn_usd

else:
    raise ValueError(f"Invalid SCOPE value: '{SCOPE}'. Expected 'US_ONLY' or 'GLOBAL_AGGREGATE'.")

# --- STEP 2: CALCULATE YoY GROWTH RATE ---
m2_df['yoy_growth'] = m2_df['m2_level'].pct_change(12) * 100

# --- STEP 3: CALCULATE 3-MONTH MOMENTUM / IMPULSE ---
if IMPULSE_METHOD == "YOY_DELTA":
    # 3-Month Change in YoY Rate
    m2_df['impulse'] = m2_df['yoy_growth'] - m2_df['yoy_growth'].shift(3)

elif IMPULSE_METHOD == "ANNUALIZED_SPREAD":
    # Spread between 3-Month Annualized Growth and YoY Rate
    three_m_ann = (((m2_df['m2_level'] / m2_df['m2_level'].shift(3)) ** 4) - 1) * 100
    m2_df['impulse'] = three_m_ann - m2_df['yoy_growth']

else:
    raise ValueError(f"Invalid IMPULSE_METHOD value: '{IMPULSE_METHOD}'. Expected 'YOY_DELTA' or 'ANNUALIZED_SPREAD'.")

# --- STEP 4: REGIME CLASSIFICATION MATRIX ---
conditions = [
    (m2_df['yoy_growth'] > 0) & (m2_df['impulse'] > 0), # Regime 1: Accelerating Expansion
    (m2_df['yoy_growth'] > 0) & (m2_df['impulse'] <= 0), # Regime 2: Decelerating Expansion
    (m2_df['yoy_growth'] <= 0) & (m2_df['impulse'] <= 0), # Regime 3: Accelerating Contraction
    (m2_df['yoy_growth'] <= 0) & (m2_df['impulse'] > 0) # Regime 4: Decelerating Contraction
]

choices = [
    'Accelerating Expansion', 
    'Decelerating Expansion',
    'Accelerating Contraction',
    'Decelerating Contraction'
]

m2_df['regime'] = np.select(conditions, choices, default='Unknown')


if __name__ == "__main__":
    print(m2_df.tail())


