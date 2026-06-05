import csv

from bigatrade.output.writers import write_trade_plans_csv
from bigatrade.strategy.trade_plan import build_trade_plan


def test_write_trade_plans_csv_writes_stable_chinese_headers(tmp_path):
    """推荐 CSV 应使用稳定中文表头，方便人工打开复核。"""
    plan = build_trade_plan(
        recommend_date="2026-06-05",
        code="600000",
        name="浦发银行",
        close=10.0,
        strength_score=88.0,
        reasons=["站上多条均线", "成交量放大"],
        risks=["跌破均线则退出"],
    )
    output_path = tmp_path / "recommend.csv"

    result_path = write_trade_plans_csv([plan], output_path)

    with result_path.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    assert rows[0]["股票代码"] == "600000"
    assert rows[0]["股票名称"] == "浦发银行"
    assert rows[0]["推荐原因"] == "站上多条均线; 成交量放大"
    assert rows[0]["风险提示"] == "跌破均线则退出"
