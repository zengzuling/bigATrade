import pandas as pd

from bigatrade.data.models import StockInfo
from bigatrade.recommend.service import RecommendationService


class FakeProvider:
    """测试用数据源，避免推荐服务测试依赖真实网络。"""

    def list_stocks(self):
        return [
            StockInfo(code="600000", name="测试股票"),
            StockInfo(code="600001", name="ST测试"),
        ]

    def daily_bars(self, code: str, start_date: str, end_date: str):
        return pd.DataFrame(
            {
                "date": pd.date_range("2026-04-20", periods=30).strftime("%Y-%m-%d"),
                "close": list(range(10, 40)),
                "high": [price + 0.5 for price in range(10, 40)],
                "low": [price - 0.5 for price in range(10, 40)],
                "open": [price - 0.2 for price in range(10, 40)],
                "volume": [100] * 27 + [180, 190, 220],
                "amount": [10_000_000] * 30,
            }
        )


class PartiallyFailingProvider(FakeProvider):
    """模拟单只股票行情接口失败，其余股票仍应继续处理。"""

    def list_stocks(self):
        return [
            StockInfo(code="600002", name="接口失败股票"),
            StockInfo(code="600000", name="测试股票"),
        ]

    def daily_bars(self, code: str, start_date: str, end_date: str):
        if code == "600002":
            raise RuntimeError("temporary akshare error")
        return super().daily_bars(code, start_date, end_date)


def test_recommendation_service_returns_top_trade_plans():
    """推荐服务应筛掉风险股票，并把强势评分转换为交易计划。"""
    service = RecommendationService(provider=FakeProvider())

    result = service.recommend(date="2026-06-05", top=5)

    assert len(result) == 1
    assert result[0].code == "600000"
    assert result[0].name == "测试股票"
    assert result[0].target_price > result[0].buy_price
    assert result[0].strength_score >= 70


def test_recommendation_service_skips_stock_when_daily_bars_fail():
    """单只股票行情失败时不应中断整批推荐。"""
    service = RecommendationService(provider=PartiallyFailingProvider())

    result = service.recommend(date="2026-06-05", top=5)

    assert [plan.code for plan in result] == ["600000"]
