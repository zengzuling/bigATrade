from __future__ import annotations

import pandas as pd

from bigatrade.data.models import StockInfo


def normalize_stock_list(raw: pd.DataFrame) -> list[StockInfo]:
    """把 AkShare 股票列表转换为内部股票信息。"""
    code_column = _first_existing_column(raw, ["代码", "code"])
    name_column = _first_existing_column(raw, ["名称", "name"])
    price_column = _optional_existing_column(raw, ["最新价", "latest_price", "最新"])
    return [
        StockInfo(
            code=_normalize_stock_code(row[code_column]),
            name=str(row[name_column]),
            latest_price=_to_optional_float(row[price_column]) if price_column else None,
        )
        for _, row in raw.iterrows()
    ]


def filter_supported_stock_codes(stocks: list[StockInfo]) -> list[StockInfo]:
    """过滤当前推荐主流程支持的沪深六位数字股票代码。"""
    return [stock for stock in stocks if stock.code.isdigit() and len(stock.code) == 6]


def normalize_daily_bars(raw: pd.DataFrame) -> pd.DataFrame:
    """把 AkShare 日线行情转换为内部统一列名。"""
    result = raw.rename(
        columns={
            "日期": "date",
            "开盘": "open",
            "收盘": "close",
            "最高": "high",
            "最低": "low",
            "成交量": "volume",
            "成交额": "amount",
        }
    )[["date", "open", "close", "high", "low", "volume", "amount"]].copy()
    result["date"] = result["date"].astype(str)
    return result.sort_values("date").reset_index(drop=True)


def normalize_industry_heat(raw: pd.DataFrame) -> dict[str, str]:
    """把 AkShare 行业板块行情转换为行业名称到市场热度文本的映射。"""
    result: dict[str, str] = {}
    rise_ratios: list[float] = []
    change_pcts: list[float] = []
    for _, row in raw.iterrows():
        sector_name = str(row["板块名称"])
        total_count = float(row["上涨家数"]) + float(row["下跌家数"])
        rise_ratio = 0.0 if total_count == 0 else float(row["上涨家数"]) / total_count * 100
        change_pct = float(row["涨跌幅"])
        rise_ratios.append(rise_ratio)
        change_pcts.append(change_pct)
        result[sector_name] = (
            f"涨跌幅 {change_pct:.2f}%，"
            f"上涨占比 {rise_ratio:.2f}%，"
            f"排名 {int(row['排名'])}"
        )
    if change_pcts:
        avg_change = sum(change_pcts) / len(change_pcts)
        avg_rise_ratio = sum(rise_ratios) / len(rise_ratios)
        result["__market_average__"] = (
            f"全行业平均涨跌幅 {avg_change:.2f}%，"
            f"平均上涨占比 {avg_rise_ratio:.2f}%"
        )
    return result


def format_market_heat(sector_name: str, industry_heat: dict[str, str]) -> str:
    """根据行业名称格式化市场热度，缺失时返回未知。"""
    return industry_heat.get(sector_name) or industry_heat.get("__market_average__", "未知")


class AkShareProvider:
    """AkShare 免费行情数据提供者。"""

    def __init__(self) -> None:
        import akshare as ak

        self._ak = ak

    def list_stocks(self) -> list[StockInfo]:
        """获取 A 股股票列表。"""
        try:
            return filter_supported_stock_codes(normalize_stock_list(self._ak.stock_zh_a_spot()))
        except Exception:
            return filter_supported_stock_codes(normalize_stock_list(self._ak.stock_info_a_code_name()))

    def daily_bars(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取单只股票历史日线行情。"""
        raw = self._ak.stock_zh_a_hist(
            symbol=code,
            period="daily",
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
            adjust="qfq",
        )
        return normalize_daily_bars(raw)

    def stock_sector(self, code: str) -> str:
        """获取单只股票所属行业板块。"""
        raw = self._ak.stock_individual_info_em(symbol=code)
        matched = raw.loc[raw["item"] == "行业", "value"]
        if matched.empty:
            return "未知"
        return str(matched.iloc[0])

    def industry_heat(self) -> dict[str, str]:
        """获取当前行业板块市场热度。"""
        return normalize_industry_heat(self._ak.stock_board_industry_name_em())


def _first_existing_column(raw: pd.DataFrame, candidates: list[str]) -> str:
    """从候选列名中选择 AkShare 当前实际返回的列名。"""
    for candidate in candidates:
        if candidate in raw.columns:
            return candidate
    raise KeyError(f"缺少必要列，候选列名: {candidates}，实际列名: {list(raw.columns)}")


def _optional_existing_column(raw: pd.DataFrame, candidates: list[str]) -> str | None:
    """从候选列名中选择可选列名。"""
    for candidate in candidates:
        if candidate in raw.columns:
            return candidate
    return None


def _normalize_stock_code(value: object) -> str:
    """规范化 AkShare 股票代码，保留北交所 bj 前缀。"""
    code = str(value)
    if code.lower().startswith("bj"):
        return code.lower()
    return code.zfill(6)


def _to_optional_float(value: object) -> float | None:
    """把 AkShare 数字字段转换为可选浮点数。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
