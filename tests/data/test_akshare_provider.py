import pandas as pd

from bigatrade.data.akshare_provider import normalize_daily_bars, normalize_stock_list


def test_normalize_stock_list_maps_akshare_columns():
    """股票列表应从 AkShare 中文列转换为内部股票信息。"""
    raw = pd.DataFrame(
        {
            "代码": ["600000", "000001"],
            "名称": ["浦发银行", "平安银行"],
        }
    )

    result = normalize_stock_list(raw)

    assert [stock.code for stock in result] == ["600000", "000001"]
    assert [stock.name for stock in result] == ["浦发银行", "平安银行"]


def test_normalize_stock_list_maps_current_akshare_lowercase_columns():
    """当前 AkShare 股票列表返回 code/name 时也应能正常转换。"""
    raw = pd.DataFrame(
        {
            "code": ["000001", "600000"],
            "name": ["平安银行", "浦发银行"],
        }
    )

    result = normalize_stock_list(raw)

    assert [stock.code for stock in result] == ["000001", "600000"]
    assert [stock.name for stock in result] == ["平安银行", "浦发银行"]


def test_normalize_daily_bars_maps_akshare_columns_and_sorts_by_date():
    """日线行情应统一列名并按日期升序排列，供指标和回测复用。"""
    raw = pd.DataFrame(
        {
            "日期": ["2026-06-05", "2026-06-04"],
            "开盘": [10.0, 9.8],
            "收盘": [10.2, 10.0],
            "最高": [10.4, 10.1],
            "最低": [9.9, 9.7],
            "成交量": [1200, 1000],
            "成交额": [12_000_000, 10_000_000],
        }
    )

    result = normalize_daily_bars(raw)

    assert list(result.columns) == ["date", "open", "close", "high", "low", "volume", "amount"]
    assert result.iloc[0]["date"] == "2026-06-04"
    assert result.iloc[1]["close"] == 10.2
