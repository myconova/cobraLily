import pandas as pd
import yfinance as yf
from m2 import m2_df

BITCOIN_TICKER = "BTC-USD"
START_DATE = "2015-01-01"


def fetch_monthly_bitcoin_prices():
    bitcoin_prices = yf.download(
        BITCOIN_TICKER,
        start=START_DATE,
        auto_adjust=False,
        progress=False,
    )

    monthly_prices = bitcoin_prices["Close"].resample("MS").last()
    current_month_start = pd.Timestamp.today().normalize().replace(day=1)
    monthly_prices = monthly_prices[monthly_prices.index < current_month_start]
    monthly_prices.columns = ["bitcoin_close"]

    return monthly_prices


bitcoin_df = fetch_monthly_bitcoin_prices()

backtest_df = m2_df.join(bitcoin_df, how="inner")
backtest_df["signal_regime"] = backtest_df["regime"].shift(1)

backtest_df["bitcoin_return_1m"] = (
    backtest_df["bitcoin_close"].shift(-1) 
    / backtest_df["bitcoin_close"]
    - 1
) * 100

backtest_df["bitcoin_return_3m"] = (
    backtest_df["bitcoin_close"].shift(-3)
    / backtest_df["bitcoin_close"]
    - 1
) * 100

backtest_df["bitcoin_return_6m"] = (
    backtest_df["bitcoin_close"].shift(-6)
    / backtest_df["bitcoin_close"]
    - 1
) * 100 

return_columns = [
    "bitcoin_return_1m",
    "bitcoin_return_3m",
    "bitcoin_return_6m",
]

backtest_summary = (
    backtest_df.groupby("signal_regime")[return_columns]
    .agg(["count", "mean", "median"])
    .round(2)
)

print(backtest_summary)




