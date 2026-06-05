import pandas as pd

from bigatrade.strategy.strong_stock import score_latest_stock


def test_score_latest_stock_accepts_clear_strong_sample():
    """明显放量上行且接近新高的样本应被识别为强势股。"""
    df = pd.DataFrame(
        {
            "close": list(range(10, 40)),
            "high": [price + 0.5 for price in range(10, 40)],
            "low": [price - 0.5 for price in range(10, 40)],
            "volume": [100] * 27 + [180, 190, 220],
            "amount": [10_000_000] * 30,
        }
    )

    result = score_latest_stock("600000", "测试股票", df)

    assert result is not None
    assert result.score >= 70
    assert any("均线" in reason for reason in result.reasons)


def test_score_latest_stock_rejects_st_stock():
    """ST 或退市风险股票不进入强势股候选。"""
    df = pd.DataFrame(
        {
            "close": list(range(10, 40)),
            "high": [price + 0.5 for price in range(10, 40)],
            "low": [price - 0.5 for price in range(10, 40)],
            "volume": [100] * 30,
            "amount": [10_000_000] * 30,
        }
    )

    assert score_latest_stock("600001", "ST测试", df) is None
