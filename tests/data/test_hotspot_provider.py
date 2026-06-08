import pandas as pd

from bigatrade.data.akshare_provider import normalize_hotspot_boards


def test_normalize_hotspot_boards_maps_board_rows():
    """热点板块应从 AkShare 板块行情转换为内部热点结构。"""
    raw = pd.DataFrame(
        {
            "板块名称": ["机器人"],
            "涨跌幅": [4.02],
            "换手率": [5.33],
            "上涨家数": [16],
            "下跌家数": [4],
            "领涨股票": ["巨能股份"],
            "领涨股票-涨跌幅": [30.0],
        }
    )

    result = normalize_hotspot_boards(raw, board_type="industry")

    assert result[0].board_type == "industry"
    assert result[0].board_name == "机器人"
    assert result[0].change_pct == 4.02
