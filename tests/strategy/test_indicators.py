import pandas as pd

from bigatrade.strategy.indicators import add_indicators


def test_add_indicators_calculates_moving_averages_and_returns():
    """指标计算应给强势股筛选提供确定的技术面字段。"""
    df = pd.DataFrame(
        {
            "close": [10, 11, 12, 13, 14],
            "volume": [100, 110, 120, 130, 260],
            "high": [10.5, 11.5, 12.5, 13.5, 14.5],
            "low": [9.5, 10.5, 11.5, 12.5, 13.5],
        }
    )

    result = add_indicators(df)

    assert result.loc[4, "ma5"] == 12
    assert round(result.loc[4, "return_5d"], 4) == 0.4
    assert round(result.loc[4, "volume_ratio_3_to_10"], 4) == round((510 / 3) / 144, 4)
    assert result.loc[4, "high_20d"] == 14.5
