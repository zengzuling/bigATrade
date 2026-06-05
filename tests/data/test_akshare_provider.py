import pandas as pd

from bigatrade.data.akshare_provider import (
    format_market_heat,
    filter_supported_stock_codes,
    normalize_daily_bars,
    normalize_industry_heat,
    normalize_stock_list,
)


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


def test_normalize_stock_list_keeps_latest_price_when_available():
    """全市场快照带最新价时，应保留到股票信息里用于请求前预过滤。"""
    raw = pd.DataFrame(
        {
            "代码": ["000001", "000002"],
            "名称": ["平安银行", "万科A"],
            "最新价": [11.0, 7.5],
        }
    )

    result = normalize_stock_list(raw)

    assert result[0].latest_price == 11.0
    assert result[1].latest_price == 7.5


def test_filter_supported_stock_codes_keeps_six_digit_a_share_codes():
    """推荐主流程第一版只扫描常见沪深六位数字代码。"""
    stocks = normalize_stock_list(
        pd.DataFrame(
            {
                "代码": ["bj920000", "000001", "600000"],
                "名称": ["北交所样本", "平安银行", "浦发银行"],
            }
        )
    )

    result = filter_supported_stock_codes(stocks)

    assert [stock.code for stock in result] == ["000001", "600000"]


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


def test_normalize_industry_heat_maps_board_name_to_heat_text():
    """行业板块热度应按板块名称映射为可读文本。"""
    raw = pd.DataFrame(
        {
            "排名": [1, 12],
            "板块名称": ["通信设备", "银行"],
            "涨跌幅": [3.2, -0.5],
            "上涨家数": [15, 2],
            "下跌家数": [5, 8],
        }
    )

    result = normalize_industry_heat(raw)

    assert result["通信设备"] == "涨跌幅 3.20%，上涨占比 75.00%，排名 1"
    assert result["银行"] == "涨跌幅 -0.50%，上涨占比 20.00%，排名 12"


def test_format_market_heat_handles_missing_sector():
    """找不到行业且没有平均热度时返回未知，避免推荐命令失败。"""
    assert format_market_heat("不存在行业", {"通信设备": "热度"}) == "未知"


def test_format_market_heat_uses_market_average_when_available():
    """行业无法精确匹配时应使用全行业平均热度作为退路。"""
    heat = {
        "通信设备": "涨跌幅 3.20%，上涨占比 75.00%，排名 8",
        "__market_average__": "全行业平均涨跌幅 1.25%，平均上涨占比 60.00%",
    }

    assert format_market_heat("不存在行业", heat) == "全行业平均涨跌幅 1.25%，平均上涨占比 60.00%"
