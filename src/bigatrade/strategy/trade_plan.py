from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TradePlan:
    """一条强势股推荐对应的交易计划。"""

    recommend_date: str
    code: str
    name: str
    close: float
    buy_low: float
    buy_high: float
    buy_price: float
    target_price: float
    stop_loss_price: float
    target_gain_pct: float
    max_holding_days: int
    strength_score: float
    reasons: list[str]
    risks: list[str]


def build_trade_plan(
    recommend_date: str,
    code: str,
    name: str,
    close: float,
    strength_score: float,
    reasons: list[str],
    risks: list[str],
) -> TradePlan:
    """按第一版固定风控规则生成买入区间、目标价和止损价。"""
    buy_low = round(close * 0.99, 2)
    buy_high = round(close * 1.02, 2)
    buy_price = round((buy_low + buy_high) / 2, 2)

    return TradePlan(
        recommend_date=recommend_date,
        code=code,
        name=name,
        close=round(close, 2),
        buy_low=buy_low,
        buy_high=buy_high,
        buy_price=buy_price,
        target_price=round(buy_price * 1.10, 2),
        stop_loss_price=round(buy_price * 0.95, 2),
        target_gain_pct=10.0,
        max_holding_days=5,
        strength_score=round(strength_score, 2),
        reasons=reasons,
        risks=risks,
    )
