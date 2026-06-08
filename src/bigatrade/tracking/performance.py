from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class RecommendationToTrack:
    """需要持续跟踪每日表现的推荐股票。"""

    recommendation_id: int
    run_id: int
    recommend_date: str
    stock_code: str
    stock_name: str
    recommend_close: float
    buy_price: float
    target_price: float
    stop_loss_price: float
    max_holding_days: int


@dataclass(frozen=True)
class DailyQuote:
    """推荐股票某个交易日的收盘后表现。"""

    recommendation_id: int
    run_id: int
    recommend_date: str
    trade_date: str
    stock_code: str
    stock_name: str
    open_price: float
    close_price: float
    high_price: float
    low_price: float
    pre_close_price: float | None
    change_pct: float | None
    volume: float
    amount: float
    gain_from_buy_pct: float
    gain_from_close_pct: float
    gain_from_recommend_pct: float
    hit_target: bool
    hit_stop_loss: bool


@dataclass(frozen=True)
class TrackingResult:
    """一次每日表现跟踪任务的结果统计。"""

    trade_date: str
    candidate_count: int
    tracked_count: int
    skipped_count: int


class TrackingRepository(Protocol):
    """每日表现跟踪依赖的数据仓储协议。"""

    def list_open_recommendations(self, trade_date: str) -> list[RecommendationToTrack]:
        """返回在观察期内仍需要跟踪的推荐股票。"""

    def save_daily_quotes(self, quotes: list[DailyQuote]) -> int:
        """批量保存每日行情表现，返回写入数量。"""


class MarketDataProvider(Protocol):
    """跟踪服务依赖的日线行情协议。"""

    def daily_bars(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """返回指定股票在日期区间内的日线行情。"""


class PerformanceTracker:
    """按交易日抓取推荐股票的收盘表现并落库。"""

    def __init__(self, provider: MarketDataProvider, repository: TrackingRepository) -> None:
        self._provider = provider
        self._repository = repository

    def track(self, trade_date: str) -> TrackingResult:
        """跟踪指定交易日所有观察期内推荐股票的每日表现。"""
        recommendations = self._repository.list_open_recommendations(trade_date)
        quotes: list[DailyQuote] = []
        skipped_count = 0

        for recommendation in recommendations:
            bars = self._provider.daily_bars(
                recommendation.stock_code,
                recommendation.recommend_date,
                trade_date,
            )
            quote = _build_daily_quote(recommendation, bars, trade_date)
            if quote is None:
                skipped_count += 1
                continue
            quotes.append(quote)

        tracked_count = self._repository.save_daily_quotes(quotes) if quotes else 0
        return TrackingResult(
            trade_date=trade_date,
            candidate_count=len(recommendations),
            tracked_count=tracked_count,
            skipped_count=skipped_count,
        )


def _build_daily_quote(
    recommendation: RecommendationToTrack,
    bars: pd.DataFrame,
    trade_date: str,
) -> DailyQuote | None:
    """从日线行情中抽取指定交易日，并计算相对推荐价的表现。"""
    if bars.empty:
        return None

    sorted_bars = bars.sort_values("date").reset_index(drop=True)
    matched = sorted_bars[sorted_bars["date"].astype(str) == trade_date]
    if matched.empty:
        return None

    row_index = int(matched.index[-1])
    row = sorted_bars.loc[row_index]
    previous_close = _previous_close(sorted_bars, row_index)
    close_price = float(row["close"])
    high_price = float(row["high"])
    low_price = float(row["low"])

    return DailyQuote(
        recommendation_id=recommendation.recommendation_id,
        run_id=recommendation.run_id,
        recommend_date=recommendation.recommend_date,
        trade_date=trade_date,
        stock_code=recommendation.stock_code,
        stock_name=recommendation.stock_name,
        open_price=float(row["open"]),
        close_price=close_price,
        high_price=high_price,
        low_price=low_price,
        pre_close_price=previous_close,
        change_pct=_change_pct(close_price, previous_close),
        volume=float(row["volume"]),
        amount=float(row["amount"]),
        gain_from_buy_pct=_gain_pct(close_price, recommendation.buy_price),
        gain_from_close_pct=_gain_pct(close_price, recommendation.recommend_close),
        gain_from_recommend_pct=_gain_pct(close_price, recommendation.recommend_close),
        hit_target=high_price >= recommendation.target_price,
        hit_stop_loss=low_price <= recommendation.stop_loss_price,
    )


def _previous_close(bars: pd.DataFrame, row_index: int) -> float | None:
    """获取前一个交易日收盘价，无法获取时返回 None。"""
    if row_index <= 0:
        return None
    return float(bars.loc[row_index - 1, "close"])


def _change_pct(close_price: float, previous_close: float | None) -> float | None:
    """计算当日涨跌幅百分比。"""
    if previous_close is None or previous_close == 0:
        return None
    return round((close_price / previous_close - 1) * 100, 4)


def _gain_pct(current_price: float, base_price: float) -> float:
    """计算相对指定基准价的涨幅百分比。"""
    if base_price == 0:
        return 0.0
    return round((current_price / base_price - 1) * 100, 4)
