from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from bigatrade.strategy.trade_plan import TradePlan


@dataclass(frozen=True)
class BacktestResult:
    """单条交易计划的 5 日回测结果。"""

    code: str
    name: str
    recommend_date: str
    entry_date: str | None
    exit_date: str | None
    entry_price: float | None
    exit_price: float | None
    highest_gain_pct: float
    hit_target: bool
    return_pct: float
    exit_reason: str
    holding_days: int | None


def backtest_trade_plan(plan: TradePlan, future_bars: pd.DataFrame) -> BacktestResult:
    """按实际买入日后的时间顺序回测一条交易计划。"""
    holding_bars = future_bars.head(plan.max_holding_days).reset_index(drop=True)
    entry_index = _find_entry_index(plan, holding_bars)
    if entry_index is None:
        return _no_entry_result(plan, holding_bars)

    entry_date = str(holding_bars.loc[entry_index, "date"])
    scanned = holding_bars.loc[entry_index:].head(plan.max_holding_days).reset_index(drop=True)
    highest_gain_pct = _highest_gain_pct(plan.buy_price, scanned)

    for holding_index, row in scanned.iterrows():
        current_date = str(row["date"])
        hit_stop = row["low"] <= plan.stop_loss_price
        hit_target = row["high"] >= plan.target_price
        holding_days = int(holding_index) + 1

        # 同日同时触发时采用保守假设，先按止损退出。
        if hit_stop:
            return _exit_result(
                plan=plan,
                entry_date=entry_date,
                exit_date=current_date,
                exit_price=plan.stop_loss_price,
                highest_gain_pct=highest_gain_pct,
                hit_target=False,
                exit_reason="止损",
                holding_days=holding_days,
            )
        if hit_target:
            return _exit_result(
                plan=plan,
                entry_date=entry_date,
                exit_date=current_date,
                exit_price=plan.target_price,
                highest_gain_pct=highest_gain_pct,
                hit_target=True,
                exit_reason="止盈",
                holding_days=holding_days,
            )

    last = scanned.iloc[-1]
    return _exit_result(
        plan=plan,
        entry_date=entry_date,
        exit_date=str(last["date"]),
        exit_price=float(last["close"]),
        highest_gain_pct=highest_gain_pct,
        hit_target=False,
        exit_reason="到期",
        holding_days=len(scanned),
    )


def _find_entry_index(plan: TradePlan, bars: pd.DataFrame) -> int | None:
    """查找第一个触发买入区间的交易日。"""
    for index, row in bars.iterrows():
        if row["low"] <= plan.buy_high and row["high"] >= plan.buy_low:
            return int(index)
    return None


def _highest_gain_pct(entry_price: float, bars: pd.DataFrame) -> float:
    """计算持有观察期内相对买入价的最高浮盈。"""
    if bars.empty:
        return 0.0
    return round((float(bars["high"].max()) / entry_price - 1) * 100, 1)


def _exit_result(
    plan: TradePlan,
    entry_date: str,
    exit_date: str,
    exit_price: float,
    highest_gain_pct: float,
    hit_target: bool,
    exit_reason: str,
    holding_days: int,
) -> BacktestResult:
    """构造已触发买入后的退出结果。"""
    return BacktestResult(
        code=plan.code,
        name=plan.name,
        recommend_date=plan.recommend_date,
        entry_date=entry_date,
        exit_date=exit_date,
        entry_price=plan.buy_price,
        exit_price=round(exit_price, 2),
        highest_gain_pct=highest_gain_pct,
        hit_target=hit_target,
        return_pct=round((exit_price / plan.buy_price - 1) * 100, 1),
        exit_reason=exit_reason,
        holding_days=holding_days,
    )


def _no_entry_result(plan: TradePlan, bars: pd.DataFrame) -> BacktestResult:
    """构造未触发买入的回测结果。"""
    return BacktestResult(
        code=plan.code,
        name=plan.name,
        recommend_date=plan.recommend_date,
        entry_date=None,
        exit_date=None,
        entry_price=None,
        exit_price=None,
        highest_gain_pct=_highest_gain_pct(plan.buy_price, bars),
        hit_target=False,
        return_pct=0.0,
        exit_reason="未触发买入",
        holding_days=None,
    )
