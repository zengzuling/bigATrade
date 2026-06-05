from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from bigatrade.strategy.indicators import add_indicators


@dataclass(frozen=True)
class StockScore:
    """单只股票在推荐日的强势评分结果。"""

    code: str
    name: str
    score: float
    reasons: list[str]
    risks: list[str]


def score_latest_stock(code: str, name: str, daily_bars: pd.DataFrame) -> StockScore | None:
    """按最新一个交易日判断股票是否满足一周强势股候选条件。"""
    if is_risky_stock_name(name):
        return None
    if len(daily_bars) < 30:
        return None

    bars = add_indicators(daily_bars).reset_index(drop=True)
    latest = bars.iloc[-1]

    if latest["close"] > 100:
        return None
    if latest.get("amount_ma20", 0) < 5_000_000:
        return None
    if not _is_above_key_averages(latest):
        return None
    if latest["return_5d"] <= 0:
        return None

    score = 0.0
    reasons: list[str] = []
    risks: list[str] = []

    if _is_above_key_averages(latest):
        score += 30
        reasons.append("收盘价站上 5 日、10 日、20 日均线")

    if latest["volume_ratio_3_to_10"] >= 1.2:
        score += 25
        reasons.append("最近 3 日成交量相对 10 日均量明显放大")

    high_proximity = latest["close"] / latest["high_20d"]
    if high_proximity >= 0.97:
        score += 25
        reasons.append("价格接近或突破最近 20 日高点")

    if 0 < latest["return_5d"] <= 0.35:
        score += 20
        reasons.append("最近 5 日保持正动量且未明显透支")
    elif latest["return_5d"] > 0.35:
        score += 8
        risks.append("最近 5 日涨幅偏大，追高风险增加")

    return StockScore(
        code=code,
        name=name,
        score=round(score, 2),
        reasons=reasons,
        risks=risks or ["若跌破关键均线则趋势失效"],
    )


def is_risky_stock_name(name: str) -> bool:
    """识别 ST、退市等第一版直接排除的股票名称。"""
    upper_name = name.upper()
    return "ST" in upper_name or "退" in name


def _is_above_key_averages(row: pd.Series) -> bool:
    """判断最新收盘价是否站上关键均线。"""
    close = row["close"]
    return close > row["ma5"] and close > row["ma10"] and close > row["ma20"]
