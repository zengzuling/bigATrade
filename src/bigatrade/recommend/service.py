from __future__ import annotations

from datetime import date as date_type
from datetime import datetime, timedelta
from typing import Protocol

import pandas as pd

from bigatrade.data.models import StockInfo
from bigatrade.strategy.strong_stock import is_risky_stock_name, score_latest_stock
from bigatrade.strategy.trade_plan import TradePlan, build_trade_plan


class MarketDataProvider(Protocol):
    """推荐服务依赖的数据源协议。"""

    def list_stocks(self) -> list[StockInfo]:
        """返回可扫描的 A 股股票列表。"""

    def daily_bars(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """返回指定股票的日线行情。"""


class RecommendationService:
    """从行情数据中筛选强势股并生成交易计划。"""

    def __init__(self, provider: MarketDataProvider) -> None:
        self._provider = provider

    def recommend(self, date: str, top: int = 30, scan_limit: int | None = None) -> list[TradePlan]:
        """生成指定日期的强势股推荐计划。"""
        start_date = _lookback_start(date)
        plans: list[TradePlan] = []
        stocks = self._provider.list_stocks()
        if scan_limit is not None:
            stocks = stocks[:scan_limit]

        for stock in stocks:
            if is_risky_stock_name(stock.name):
                continue
            try:
                bars = self._provider.daily_bars(stock.code, start_date, date)
            except Exception:
                continue
            if bars.empty:
                continue

            score = score_latest_stock(stock.code, stock.name, bars)
            if score is None:
                continue

            latest_close = float(bars.sort_values("date").iloc[-1]["close"])
            plans.append(
                build_trade_plan(
                    recommend_date=date,
                    code=stock.code,
                    name=stock.name,
                    close=latest_close,
                    strength_score=score.score,
                    reasons=score.reasons,
                    risks=score.risks,
                )
            )

        return sorted(plans, key=lambda plan: plan.strength_score, reverse=True)[:top]


def _lookback_start(date: str) -> str:
    """按推荐日期向前取 90 个自然日，保证至少覆盖 30 个交易日。"""
    current = datetime.strptime(date, "%Y-%m-%d").date()
    start: date_type = current - timedelta(days=90)
    return start.strftime("%Y-%m-%d")
