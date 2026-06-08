from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StockInfo:
    """A 股基础股票信息。"""

    code: str
    name: str
    latest_price: float | None = None
    change_percent: float | None = None
    amount: float | None = None
