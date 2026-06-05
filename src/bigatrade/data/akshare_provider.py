from __future__ import annotations

import pandas as pd

from bigatrade.data.models import StockInfo


def normalize_stock_list(raw: pd.DataFrame) -> list[StockInfo]:
    """把 AkShare 股票列表转换为内部股票信息。"""
    return [
        StockInfo(code=str(row["代码"]).zfill(6), name=str(row["名称"]))
        for _, row in raw.iterrows()
    ]


def normalize_daily_bars(raw: pd.DataFrame) -> pd.DataFrame:
    """把 AkShare 日线行情转换为内部统一列名。"""
    result = raw.rename(
        columns={
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
        }
    )[["date", "open", "close", "high", "low", "volume", "amount"]].copy()
    result["date"] = result["date"].astype(str)
    return result.sort_values("date").reset_index(drop=True)


class AkShareProvider:
    """AkShare 免费行情数据提供者。"""

    def __init__(self) -> None:
        import akshare as ak

        self._ak = ak

    def list_stocks(self) -> list[StockInfo]:
        """获取 A 股股票列表。"""
        return normalize_stock_list(self._ak.stock_info_a_code_name())

    def daily_bars(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取单只股票历史日线行情。"""
        raw = self._ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
            adjust="qfq",
        )
        return normalize_daily_bars(raw)
