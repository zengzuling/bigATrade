from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Protocol


@dataclass(frozen=True)
class HotspotBoard:
    """市场热点板块。"""

    board_type: str
    board_name: str
    change_pct: float
    turnover_rate: float
    rise_count: int
    fall_count: int
    leading_stock: str
    leading_stock_change_pct: float


@dataclass(frozen=True)
class HotspotVersion:
    """一次推荐前生成的热点版本。"""

    version_id: int
    trade_date: str
    boards: list[HotspotBoard]
    industry_bonus_scores: dict[str, float]


class HotspotProvider(Protocol):
    """热点服务依赖的数据源协议。"""

    def industry_boards(self) -> list[HotspotBoard]:
        """返回行业板块热点列表。"""

    def concept_boards(self) -> list[HotspotBoard]:
        """返回概念板块热点列表。"""


class HotspotRepository(Protocol):
    """热点版本仓储协议。"""

    def save_version(self, trade_date: str, boards: list[HotspotBoard], source: str) -> int:
        """保存热点版本和明细，返回版本 ID。"""


class HotspotService:
    """推荐前刷新市场热点，并生成板块加分映射。"""

    def __init__(
        self,
        provider: HotspotProvider,
        repository: HotspotRepository,
        retry_times: int = 3,
        retry_delay_seconds: float = 2.0,
    ) -> None:
        self._provider = provider
        self._repository = repository
        self._retry_times = retry_times
        self._retry_delay_seconds = retry_delay_seconds

    def refresh_hotspots(
        self,
        trade_date: str,
        top_industry: int = 20,
        top_concept: int = 20,
        source: str = "akshare_eastmoney",
    ) -> HotspotVersion:
        """拉取行业和概念热点，保存一个可追溯版本。"""
        industry_boards = _top_boards(
            _load_with_retry(self._provider.industry_boards, self._retry_times, self._retry_delay_seconds),
            top_industry,
        )
        concept_boards = _top_boards(
            _load_with_retry(self._provider.concept_boards, self._retry_times, self._retry_delay_seconds),
            top_concept,
        )
        boards = industry_boards + concept_boards
        version_id = self._repository.save_version(trade_date, boards, source)
        return HotspotVersion(
            version_id=version_id,
            trade_date=trade_date,
            boards=boards,
            industry_bonus_scores=_industry_bonus_scores(industry_boards),
        )


def _top_boards(boards: list[HotspotBoard], count: int) -> list[HotspotBoard]:
    """按涨跌幅、上涨家数占比和换手率选择热点板块。"""
    if count <= 0:
        return []
    sorted_boards = sorted(boards, key=_board_rank, reverse=True)
    return sorted_boards[:count]


def _load_with_retry(loader, retry_times: int, retry_delay_seconds: float) -> list[HotspotBoard]:
    """带重试地拉取热点板块，降低免费接口偶发断开的影响。"""
    last_error: Exception | None = None
    for attempt in range(max(1, retry_times)):
        try:
            return loader()
        except Exception as error:
            last_error = error
            if attempt < retry_times - 1 and retry_delay_seconds > 0:
                time.sleep(retry_delay_seconds)
    if last_error:
        raise last_error
    return []


def _board_rank(board: HotspotBoard) -> tuple[float, float, float]:
    """板块热度排序分值。"""
    total = board.rise_count + board.fall_count
    rise_ratio = 0.0 if total == 0 else board.rise_count / total
    return (board.change_pct, rise_ratio, board.turnover_rate)


def _industry_bonus_scores(boards: list[HotspotBoard]) -> dict[str, float]:
    """把行业热点排名转换为推荐加分，最高 10 分，最低 2 分。"""
    if not boards:
        return {}
    max_bonus = 10.0
    min_bonus = 2.0
    if len(boards) == 1:
        return {boards[0].board_name: max_bonus}

    step = (max_bonus - min_bonus) / (len(boards) - 1)
    return {
        board.board_name: round(max_bonus - index * step, 2)
        for index, board in enumerate(boards)
    }
