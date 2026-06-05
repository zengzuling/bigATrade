from __future__ import annotations

import csv
from pathlib import Path

from bigatrade.strategy.trade_plan import TradePlan


CSV_HEADERS = [
    "推荐日期",
    "股票代码",
    "股票名称",
    "所属板块",
    "市场热度",
    "收盘价",
    "买入价下限",
    "买入价上限",
    "买入中位价",
    "目标价",
    "止损价",
    "目标涨幅",
    "最大持有交易日",
    "强势评分",
    "推荐原因",
    "风险提示",
]


def write_trade_plans_csv(plans: list[TradePlan], output_path: str | Path) -> Path:
    """把推荐交易计划写入 CSV 文件。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for plan in plans:
            writer.writerow(_plan_to_row(plan))

    return path


def _plan_to_row(plan: TradePlan) -> dict[str, str | float | int]:
    """转换交易计划为 CSV 行。"""
    return {
        "推荐日期": plan.recommend_date,
        "股票代码": plan.code,
        "股票名称": plan.name,
        "所属板块": plan.sector_name,
        "市场热度": plan.market_heat,
        "收盘价": plan.close,
        "买入价下限": plan.buy_low,
        "买入价上限": plan.buy_high,
        "买入中位价": plan.buy_price,
        "目标价": plan.target_price,
        "止损价": plan.stop_loss_price,
        "目标涨幅": plan.target_gain_pct,
        "最大持有交易日": plan.max_holding_days,
        "强势评分": plan.strength_score,
        "推荐原因": "; ".join(plan.reasons),
        "风险提示": "; ".join(plan.risks),
    }
