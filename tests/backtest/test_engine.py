import pandas as pd

from bigatrade.backtest.engine import backtest_trade_plan
from bigatrade.strategy.trade_plan import build_trade_plan


def make_plan():
    """构造固定交易计划，便于回测测试聚焦卖出规则。"""
    return build_trade_plan(
        recommend_date="2026-06-05",
        code="600000",
        name="浦发银行",
        close=10.0,
        strength_score=80.0,
        reasons=["强势突破"],
        risks=["跌破止损则退出"],
    )


def test_backtest_takes_profit_after_entry():
    """触发买入后，后续交易日达到目标价应按止盈退出。"""
    future = pd.DataFrame(
        {
            "date": ["2026-06-08", "2026-06-09"],
            "open": [10.0, 10.8],
            "high": [10.3, 11.2],
            "low": [9.95, 10.7],
            "close": [10.2, 11.1],
        }
    )

    result = backtest_trade_plan(make_plan(), future)

    assert result.exit_reason == "止盈"
    assert result.hit_target is True
    assert round(result.return_pct, 2) == 10.0


def test_backtest_uses_conservative_stop_loss_when_same_day_hits_both():
    """同一天同时触发止盈止损时，第一版按保守止损处理。"""
    future = pd.DataFrame(
        {
            "date": ["2026-06-08"],
            "open": [10.0],
            "high": [11.2],
            "low": [9.4],
            "close": [10.5],
        }
    )

    result = backtest_trade_plan(make_plan(), future)

    assert result.exit_reason == "止损"
    assert result.hit_target is False
    assert round(result.return_pct, 2) == -5.0
