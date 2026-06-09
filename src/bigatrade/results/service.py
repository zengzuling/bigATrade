from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from bigatrade.backtest.engine import BacktestResult
from bigatrade.strategy.trade_plan import TradePlan


@dataclass(frozen=True)
class RecommendationForSettlement:
    """需要根据每日表现做结算的推荐股票。"""

    recommendation_id: int
    run_id: int
    recommend_date: str
    stock_code: str
    stock_name: str
    close_price: float
    buy_low: float
    buy_high: float
    buy_price: float
    target_price: float
    stop_loss_price: float
    target_gain_pct: float
    max_holding_days: int
    strength_score: float
    recommend_reason: str
    risk_tip: str


@dataclass(frozen=True)
class QuoteForSettlement:
    """用于回测结算的每日行情。"""

    trade_date: str
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    change_pct: float | None
    gain_from_recommend_pct: float
    amount: float
    hit_target: bool
    hit_stop_loss: bool


@dataclass(frozen=True)
class SettledBacktestResult:
    """携带推荐主键的回测结算结果。"""

    recommendation_id: int
    run_id: int
    result: BacktestResult


@dataclass(frozen=True)
class SettlementResult:
    """一次回测结算任务的统计结果。"""

    candidate_count: int
    settled_count: int
    skipped_count: int


@dataclass(frozen=True)
class DailyReviewRow:
    """复盘文案所需的单只股票表现。"""

    stock_code: str
    stock_name: str
    close_price: float
    change_pct: float | None
    gain_from_recommend_pct: float
    amount: float
    hit_target: bool
    hit_stop_loss: bool
    recommend_reason: str
    risk_tip: str


@dataclass(frozen=True)
class FiveDaySummary:
    """5 日结算汇总。"""

    result_count: int
    hit_target_count: int
    positive_count: int
    average_return_pct: float
    worst_return_pct: float
    best_return_pct: float


class ResultRepository(Protocol):
    """结果结算依赖的数据仓储协议。"""

    def list_settlement_candidates(self, as_of_date: str) -> list[RecommendationForSettlement]:
        """查询截至指定日期可以尝试结算的推荐股票。"""

    def list_quotes(self, recommendation_id: int) -> list[QuoteForSettlement]:
        """查询推荐股票已跟踪的每日表现。"""

    def save_backtest_results(self, results: list[SettledBacktestResult]) -> int:
        """保存结算后的回测结果。"""

    def list_daily_review_rows(self, trade_date: str) -> list[DailyReviewRow]:
        """查询指定交易日复盘所需的数据。"""

    def load_five_day_summary(self, as_of_date: str) -> FiveDaySummary:
        """读取截至指定日期的 5 日结算汇总。"""


class SettlementService:
    """把每日跟踪表现沉淀为可复核的每日回测快照。"""

    def __init__(self, repository: ResultRepository) -> None:
        self._repository = repository

    def settle(self, as_of_date: str) -> SettlementResult:
        """结算截至指定日期的所有已跟踪推荐，未最终退出的写入当前结果。"""
        candidates = self._repository.list_settlement_candidates(as_of_date)
        results: list[SettledBacktestResult] = []
        skipped_count = 0

        for candidate in candidates:
            quotes = [
                quote
                for quote in self._repository.list_quotes(candidate.recommendation_id)
                if candidate.recommend_date < quote.trade_date <= as_of_date
            ]
            if not quotes:
                skipped_count += 1
                continue
            results.append(_settle_one(candidate, quotes))

        settled_count = self._repository.save_backtest_results(results) if results else 0
        return SettlementResult(
            candidate_count=len(candidates),
            settled_count=settled_count,
            skipped_count=skipped_count,
        )


def render_review(trade_date: str, rows: list[DailyReviewRow]) -> str:
    """生成适合公众号初稿的每日复盘文案。"""
    if not rows:
        return f"{trade_date} 暂无可复盘的推荐表现数据。"

    sorted_rows = sorted(rows, key=lambda row: row.gain_from_recommend_pct, reverse=True)
    strongest = sorted_rows[0]
    pressure_rows = [row for row in sorted_rows if row.hit_stop_loss or row.gain_from_recommend_pct < 0]
    active_rows = [row for row in sorted_rows if row.amount >= 100_000_000]

    title_default = f"{trade_date} 推荐股复盘：{strongest.stock_name}领跑，分化继续"
    title_conservative = f"{trade_date} 推荐股票收盘跟踪"
    title_viral = f"{strongest.stock_name}最强，今天这批推荐股谁扛住了？"
    stock_labels = "；".join(
        f"{row.stock_name}{_format_pct(row.gain_from_recommend_pct)}"
        for row in sorted_rows
    )
    pressure_text = "，但需留意止损压力" if pressure_rows else "，暂未出现明显止损压力"
    active_text = "成交活跃度较高" if active_rows else "成交活跃度一般"

    return "\n\n".join(
        [
            "1. 标题",
            f"保守版：{title_conservative}",
            f"传播版：{title_viral}",
            f"推荐版：{title_default}",
            "2. 海报文案",
            f"主标题：{strongest.stock_name}领跑推荐池",
            f"副标题：{trade_date} 收盘跟踪，{stock_labels}",
            f"结论：{active_text}{pressure_text}。",
            "3. 今日复盘",
            f"今天表现最强的是 **{strongest.stock_name}**，相对推荐日涨幅 {_format_pct(strongest.gain_from_recommend_pct)}，收盘价 {strongest.close_price:.2f} 元。",
            f"从整体看，推荐池呈现分化：{stock_labels}。这比单看涨跌家数更重要，因为它能直接检验推荐后的承接质量。",
            f"资金活跃度方面，{active_text}。成交额只能说明关注度，不能直接等同于主力净流入。",
            f"风险上，{'、'.join(row.stock_name for row in pressure_rows) if pressure_rows else '当前样本'}需要继续观察回撤和止损线附近的表现。",
            "4. 明日计划",
            f"先看 **{strongest.stock_name}** 的强势能否延续，重点观察高开后是否还能站稳。",
            "其余个股先确认修复是否真实，弱势延续时保持谨慎。",
            "如果成交放大但收盘转弱，按分歧处理，不把活跃度误读成确定性。",
        ]
    )


def render_five_day_summary(as_of_date: str, summary: FiveDaySummary) -> str:
    """格式化 5 日结果总结。"""
    if summary.result_count == 0:
        return f"截至 {as_of_date} 暂无已跟踪的 5 日结果。"
    hit_rate = summary.hit_target_count / summary.result_count * 100
    positive_rate = summary.positive_count / summary.result_count * 100
    return (
        f"截至 {as_of_date}，已跟踪 {summary.result_count} 条推荐；"
        f"10% 目标命中 {summary.hit_target_count} 条，命中率 {hit_rate:.2f}%；"
        f"正收益 {summary.positive_count} 条，占比 {positive_rate:.2f}%；"
        f"平均收益 {summary.average_return_pct:.2f}%，"
        f"最佳 {summary.best_return_pct:.2f}%，最差 {summary.worst_return_pct:.2f}%。"
    )


def _settle_one(
    candidate: RecommendationForSettlement,
    quotes: list[QuoteForSettlement],
) -> SettledBacktestResult:
    """结算单条推荐截至当天的 5 日观察快照。"""
    plan = TradePlan(
        recommend_date=candidate.recommend_date,
        code=candidate.stock_code,
        name=candidate.stock_name,
        close=candidate.close_price,
        buy_low=candidate.buy_low,
        buy_high=candidate.buy_high,
        buy_price=candidate.buy_price,
        target_price=candidate.target_price,
        stop_loss_price=candidate.stop_loss_price,
        target_gain_pct=candidate.target_gain_pct,
        max_holding_days=candidate.max_holding_days,
        strength_score=candidate.strength_score,
        reasons=[candidate.recommend_reason],
        risks=[candidate.risk_tip],
        sector_name="未知",
        market_heat="未知",
    )
    frame = pd.DataFrame(
        {
            "date": [quote.trade_date for quote in quotes],
            "open": [quote.open_price for quote in quotes],
            "high": [quote.high_price for quote in quotes],
            "low": [quote.low_price for quote in quotes],
            "close": [quote.close_price for quote in quotes],
        }
    )
    return SettledBacktestResult(
        recommendation_id=candidate.recommendation_id,
        run_id=candidate.run_id,
        result=_as_of_result(plan, frame),
    )


def _as_of_result(plan: TradePlan, frame: pd.DataFrame) -> BacktestResult:
    """构造截至最新交易日的当前结果，保证每只推荐股每天都有回测记录。"""
    holding_bars = frame.head(plan.max_holding_days).reset_index(drop=True)
    entry_index = _find_entry_index(plan, holding_bars)
    if entry_index is None:
        latest = holding_bars.iloc[-1]
        return BacktestResult(
            code=plan.code,
            name=plan.name,
            recommend_date=plan.recommend_date,
            entry_date=None,
            exit_date=str(latest["date"]),
            entry_price=None,
            exit_price=None,
            highest_gain_pct=_highest_gain_pct(plan.buy_price, holding_bars),
            hit_target=False,
            return_pct=0.0,
            exit_reason="未触发买入",
            holding_days=None,
        )

    scanned = holding_bars.loc[entry_index:].reset_index(drop=True)
    latest = scanned.iloc[-1]
    latest_close = float(latest["close"])
    hit_target = bool((scanned["high"] >= plan.target_price).any())
    hit_stop_loss = bool((scanned["low"] <= plan.stop_loss_price).any())
    exit_reason = _as_of_exit_reason(hit_target=hit_target, hit_stop_loss=hit_stop_loss)
    return BacktestResult(
        code=plan.code,
        name=plan.name,
        recommend_date=plan.recommend_date,
        entry_date=str(scanned.iloc[0]["date"]),
        exit_date=str(latest["date"]),
        entry_price=plan.buy_price,
        exit_price=round(latest_close, 2),
        highest_gain_pct=_highest_gain_pct(plan.buy_price, scanned),
        hit_target=hit_target,
        return_pct=round((latest_close / plan.buy_price - 1) * 100, 1),
        exit_reason=exit_reason,
        holding_days=len(scanned),
    )


def _as_of_exit_reason(hit_target: bool, hit_stop_loss: bool) -> str:
    """根据观察期累计触发情况给当前快照打状态。"""
    if hit_target:
        return "止盈"
    if hit_stop_loss:
        return "止损"
    return "观察中"


def _find_entry_index(plan: TradePlan, frame: pd.DataFrame) -> int | None:
    """查找观察期内第一个触发买入区间的交易日。"""
    for index, row in frame.iterrows():
        if row["low"] <= plan.buy_high and row["high"] >= plan.buy_low:
            return int(index)
    return None


def _highest_gain_pct(entry_price: float, frame: pd.DataFrame) -> float:
    """计算当前观察期内的最高浮盈。"""
    if frame.empty:
        return 0.0
    return round((float(frame["high"].max()) / entry_price - 1) * 100, 1)


def _format_pct(value: float | None) -> str:
    """格式化百分比，缺失时给出未知。"""
    if value is None:
        return "未知"
    return f"{value:+.2f}%"
