from __future__ import annotations

from pathlib import Path

import pandas as pd

from bigatrade.data.models import StockInfo


class CachedMarketDataProvider:
    """给行情数据源增加本地日线缓存，减少重复 AkShare 请求。"""

    def __init__(self, provider, cache_dir: Path) -> None:
        self._provider = provider
        self._daily_cache_dir = cache_dir / "daily_bars"

    def list_stocks(self) -> list[StockInfo]:
        """股票列表仍直接使用底层数据源，保证每次拿到最新快照。"""
        return self._provider.list_stocks()

    def daily_bars(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """优先读取本地日线缓存，未命中时再请求底层数据源并写入缓存。"""
        cache_path = self._daily_cache_path(code, start_date, end_date)
        if cache_path.exists():
            return pd.read_csv(cache_path)

        bars = self._provider.daily_bars(code, start_date, end_date)
        self._daily_cache_dir.mkdir(parents=True, exist_ok=True)
        bars.to_csv(cache_path, index=False)
        return bars

    def stock_sector(self, code: str) -> str:
        """个股行业仍委托底层数据源。"""
        return self._provider.stock_sector(code)

    def industry_heat(self) -> dict[str, str]:
        """行业热度仍委托底层数据源。"""
        return self._provider.industry_heat()

    def _daily_cache_path(self, code: str, start_date: str, end_date: str) -> Path:
        """生成单只股票指定日期区间的缓存文件路径。"""
        safe_start = start_date.replace("-", "")
        safe_end = end_date.replace("-", "")
        return self._daily_cache_dir / f"{code}_{safe_start}_{safe_end}.csv"
