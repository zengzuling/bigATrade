from __future__ import annotations

import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """为日线行情补充强势股筛选所需的基础技术指标。"""
    result = df.copy()

    result["ma5"] = result["close"].rolling(window=5, min_periods=1).mean()
    result["ma10"] = result["close"].rolling(window=10, min_periods=1).mean()
    result["ma20"] = result["close"].rolling(window=20, min_periods=1).mean()

    result["return_5d"] = result["close"] / result["close"].shift(4) - 1
    result["return_10d"] = result["close"] / result["close"].shift(9) - 1

    result["volume_ma10"] = result["volume"].rolling(window=10, min_periods=1).mean()
    volume_ma3 = result["volume"].rolling(window=3, min_periods=1).mean()
    result["volume_ratio_3_to_10"] = volume_ma3 / result["volume_ma10"]

    result["high_20d"] = result["high"].rolling(window=20, min_periods=1).max()
    if "amount" in result.columns:
        result["amount_ma20"] = result["amount"].rolling(window=20, min_periods=1).mean()

    return result
