from __future__ import annotations

from datetime import date as date_type
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from bigatrade.data.akshare_provider import format_market_heat
from bigatrade.data.models import StockInfo
from bigatrade.strategy.strong_stock import is_risky_stock_name, score_latest_stock
from bigatrade.strategy.trade_plan import TradePlan, build_trade_plan


@dataclass(frozen=True)
class PriceBucket:
    """价格分层规则。"""

    low: float
    high: float
    count: int


@dataclass
class RecommendationDiagnostics:
    """记录推荐流程各阶段数量，便于定位空结果根因。"""

    total_stocks: int = 0
    scanned_stocks: int = 0
    price_prefiltered_stocks: int = 0
    risky_name_stocks: int = 0
    daily_bar_errors: int = 0
    empty_daily_bars: int = 0
    candidate_prefiltered_stocks: int = 0
    score_filtered_stocks: int = 0
    scored_plans: int = 0
    output_plans: int = 0


class MarketDataProvider(Protocol):
    """推荐服务依赖的数据源协议。"""

    def list_stocks(self) -> list[StockInfo]:
        """返回可扫描的 A 股股票列表。"""

    def daily_bars(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """返回指定股票的日线行情。"""

    def stock_sector(self, code: str) -> str:
        """返回股票所属行业板块。"""

    def industry_heat(self) -> dict[str, str]:
        """返回行业板块市场热度。"""


class RecommendationService:
    """从行情数据中筛选强势股并生成交易计划。"""

    def __init__(self, provider: MarketDataProvider) -> None:
        self._provider = provider
        self.last_diagnostics = RecommendationDiagnostics()

    def recommend(
        self,
        date: str,
        top: int = 30,
        scan_limit: int | None = None,
        price_buckets: list[PriceBucket] | None = None,
        prefilter_buckets: list[PriceBucket] | None = None,
        hotspot_scores: dict[str, float] | None = None,
    ) -> list[TradePlan]:
        """生成指定日期的强势股推荐计划。"""
        diagnostics = RecommendationDiagnostics()
        start_date = _lookback_start(date)
        plans: list[TradePlan] = []
        stocks = self._provider.list_stocks()
        diagnostics.total_stocks = len(stocks)
        industry_heat = self._safe_industry_heat()
        if scan_limit is not None:
            stocks = stocks[:scan_limit]
        diagnostics.scanned_stocks = len(stocks)
        if price_buckets:
            stocks = _prefilter_stocks_by_price_buckets(stocks, price_buckets)
        diagnostics.price_prefiltered_stocks = len(stocks)
        if prefilter_buckets:
            stocks = _prefilter_snapshot_candidates_by_buckets(stocks, prefilter_buckets)
        diagnostics.candidate_prefiltered_stocks = len(stocks)

        for stock in stocks:
            if is_risky_stock_name(stock.name):
                diagnostics.risky_name_stocks += 1
                continue
            try:
                bars = self._provider.daily_bars(stock.code, start_date, date)
            except Exception:
                diagnostics.daily_bar_errors += 1
                continue
            if bars.empty:
                diagnostics.empty_daily_bars += 1
                continue

            score = score_latest_stock(stock.code, stock.name, bars)
            if score is None:
                diagnostics.score_filtered_stocks += 1
                continue

            latest_close = float(bars.sort_values("date").iloc[-1]["close"])
            sector_name = self._safe_stock_sector(stock.code)
            hotspot_bonus = (hotspot_scores or {}).get(sector_name, 0.0)
            reasons = list(score.reasons)
            if hotspot_bonus > 0:
                reasons.append(f"热点板块加分 {hotspot_bonus:.1f}：{sector_name}")
            plans.append(
                build_trade_plan(
                    recommend_date=date,
                    code=stock.code,
                    name=stock.name,
                    close=latest_close,
                    strength_score=score.score + hotspot_bonus,
                    reasons=reasons,
                    risks=score.risks,
                    sector_name=sector_name,
                    market_heat=format_market_heat(sector_name, industry_heat),
                )
            )
            diagnostics.scored_plans += 1

        result = sorted(plans, key=lambda plan: plan.strength_score, reverse=True)[:top]
        diagnostics.output_plans = len(result)
        self.last_diagnostics = diagnostics
        return result

    def _safe_industry_heat(self) -> dict[str, str]:
        """安全获取行业热度，接口失败时不影响推荐主流程。"""
        try:
            return self._provider.industry_heat()
        except Exception:
            return {}

    def _safe_stock_sector(self, code: str) -> str:
        """安全获取股票行业，接口失败时返回未知。"""
        try:
            return self._provider.stock_sector(code)
        except Exception:
            return "未知"


def _lookback_start(date: str) -> str:
    """按推荐日期向前取 90 个自然日，保证至少覆盖 30 个交易日。"""
    current = datetime.strptime(date, "%Y-%m-%d").date()
    start: date_type = current - timedelta(days=90)
    return start.strftime("%Y-%m-%d")


def parse_price_buckets(value: str | None) -> list[PriceBucket]:
    """解析价格分层参数，例如 0-10:2,10-20:2,20-50:1。"""
    if not value:
        return []

    buckets: list[PriceBucket] = []
    for item in value.split(","):
        range_part, count_part = item.split(":", maxsplit=1)
        low_part, high_part = range_part.split("-", maxsplit=1)
        buckets.append(
            PriceBucket(
                low=float(low_part),
                high=float(high_part),
                count=int(count_part),
            )
        )
    return buckets


def filter_plans_by_price_buckets(plans: list[TradePlan], buckets: list[PriceBucket]) -> list[TradePlan]:
    """按价格分层从每档里选强势评分最高的推荐计划。"""
    if not buckets:
        return plans

    selected: list[TradePlan] = []
    for bucket in buckets:
        bucket_plans = [
            plan
            for plan in plans
            if bucket.low <= plan.close < bucket.high
        ]
        bucket_plans.sort(key=lambda plan: plan.strength_score, reverse=True)
        selected.extend(bucket_plans[: bucket.count])
    return selected


def _prefilter_stocks_by_price_buckets(stocks: list[StockInfo], buckets: list[PriceBucket]) -> list[StockInfo]:
    """在拉日线前按最新价做价格分层预过滤。"""
    prefiltered: list[StockInfo] = []
    for stock in stocks:
        if stock.latest_price is None:
            prefiltered.append(stock)
            continue
        if any(bucket.low <= stock.latest_price < bucket.high for bucket in buckets):
            prefiltered.append(stock)
    return prefiltered


def _prefilter_snapshot_candidates_by_buckets(stocks: list[StockInfo], buckets: list[PriceBucket]) -> list[StockInfo]:
    """按快照强度从每个价格桶挑出候选池，减少后续日线请求。"""
    if not any(stock.latest_price is not None for stock in stocks):
        return stocks

    selected: list[StockInfo] = []
    selected_codes: set[str] = set()
    for bucket in buckets:
        bucket_stocks = [
            stock
            for stock in stocks
            if stock.latest_price is not None and bucket.low <= stock.latest_price < bucket.high
        ]
        bucket_stocks.sort(key=_snapshot_candidate_rank, reverse=True)
        for stock in bucket_stocks[: bucket.count]:
            if stock.code in selected_codes:
                continue
            selected.append(stock)
            selected_codes.add(stock.code)
    return selected


def _snapshot_candidate_rank(stock: StockInfo) -> tuple[float, float, float]:
    """用成交额、涨跌幅、最新价给快照候选排序。"""
    return (
        stock.amount or 0.0,
        stock.change_percent or 0.0,
        stock.latest_price or 0.0,
    )
