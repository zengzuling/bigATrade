import pandas as pd

from bigatrade.data.models import StockInfo
from bigatrade.recommend.service import RecommendationService, filter_plans_by_price_buckets, parse_price_buckets


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

    def stock_sector(self, code: str):
        return "通信设备"

    def industry_heat(self):
        return {"通信设备": "涨跌幅 3.20%，上涨占比 75.00%，排名 8"}


class RecordingProvider(FakeProvider):
    """记录行情请求，用于验证服务层是否提前跳过风险股票。"""

    def __init__(self):
        self.requested_codes = []

    def daily_bars(self, code: str, start_date: str, end_date: str):
        self.requested_codes.append(code)
        return super().daily_bars(code, start_date, end_date)


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


class UnknownSectorProvider(FakeProvider):
    """模拟个股行业和行业热度表无法精确匹配。"""

    def stock_sector(self, code: str):
        return "细分行业"

    def industry_heat(self):
        return {"__market_average__": "全行业平均涨跌幅 1.25%，平均上涨占比 60.00%"}


def test_recommendation_service_returns_top_trade_plans():
    """推荐服务应筛掉风险股票，并把强势评分转换为交易计划。"""
    service = RecommendationService(provider=FakeProvider())

    result = service.recommend(date="2026-06-05", top=5)

    assert len(result) == 1
    assert result[0].code == "600000"
    assert result[0].name == "测试股票"
    assert result[0].target_price > result[0].buy_price
    assert result[0].strength_score >= 70
    assert result[0].sector_name == "通信设备"
    assert result[0].market_heat == "涨跌幅 3.20%，上涨占比 75.00%，排名 8"


def test_recommendation_service_uses_market_average_heat_when_sector_missing():
    """所属板块无法精确匹配热度时，应写入全行业平均热度。"""
    service = RecommendationService(provider=UnknownSectorProvider())

    result = service.recommend(date="2026-06-05", top=5)

    assert result[0].sector_name == "细分行业"
    assert result[0].market_heat == "全行业平均涨跌幅 1.25%，平均上涨占比 60.00%"


def test_recommendation_service_respects_scan_limit():
    """真实运行时应支持限制扫描数量，避免首次验证扫全市场过慢。"""
    service = RecommendationService(provider=FakeProvider())

    result = service.recommend(date="2026-06-05", top=5, scan_limit=1)

    assert len(result) == 1
    assert result[0].code == "600000"


def test_recommendation_service_prefilters_by_price_buckets_before_fetching_daily_bars():
    """带最新价时，应在拉日线前按价格分层预过滤，减少 AkShare 请求。"""
    provider = RecordingProvider()
    provider.list_stocks = lambda: [
        StockInfo(code="000001", name="低价", latest_price=8.0),
        StockInfo(code="000002", name="高价", latest_price=55.0),
    ]
    service = RecommendationService(provider=provider)

    service.recommend(date="2026-06-05", top=10, price_buckets=parse_price_buckets("0-10:1"))

    assert provider.requested_codes == ["000001"]


def test_recommendation_service_skips_st_before_fetching_daily_bars():
    """ST 股票应在拉行情前跳过，避免浪费 AkShare 请求。"""
    provider = RecordingProvider()
    service = RecommendationService(provider=provider)

    service.recommend(date="2026-06-05", top=5)

    assert provider.requested_codes == ["600000"]


def test_recommendation_service_skips_stock_when_daily_bars_fail():
    """单只股票行情失败时不应中断整批推荐。"""
    service = RecommendationService(provider=PartiallyFailingProvider())

    result = service.recommend(date="2026-06-05", top=5)

    assert [plan.code for plan in result] == ["600000"]


def test_recommendation_service_records_diagnostics_for_empty_or_failed_stages():
    """推荐服务应记录各阶段数量，避免空结果时无法判断根因。"""
    service = RecommendationService(provider=PartiallyFailingProvider())

    service.recommend(date="2026-06-05", top=5)

    diagnostics = service.last_diagnostics
    assert diagnostics.scanned_stocks == 2
    assert diagnostics.risky_name_stocks == 0
    assert diagnostics.daily_bar_errors == 1
    assert diagnostics.scored_plans == 1
    assert diagnostics.output_plans == 1


def test_parse_price_buckets_parses_non_overlapping_ranges():
    """价格分层参数应解析为不重叠区间和目标数量。"""
    buckets = parse_price_buckets("0-10:2,10-20:2,20-50:1")

    assert [(bucket.low, bucket.high, bucket.count) for bucket in buckets] == [
        (0, 10, 2),
        (10, 20, 2),
        (20, 50, 1),
    ]


def test_filter_plans_by_price_buckets_keeps_top_scores_per_bucket():
    """价格分层应按评分从高到低分别取每档目标数量。"""
    plans = [
        build_plan("000001", 8.0, 70),
        build_plan("000002", 9.0, 90),
        build_plan("000003", 12.0, 88),
        build_plan("000004", 18.0, 60),
        build_plan("000005", 30.0, 99),
        build_plan("000006", 55.0, 100),
    ]

    result = filter_plans_by_price_buckets(plans, parse_price_buckets("0-10:1,10-20:2,20-50:1"))

    assert [plan.code for plan in result] == ["000002", "000003", "000004", "000005"]


def build_plan(code: str, close: float, score: float):
    """构造价格分层测试用交易计划。"""
    from bigatrade.strategy.trade_plan import build_trade_plan

    return build_trade_plan(
        recommend_date="2026-06-05",
        code=code,
        name=f"测试{code}",
        close=close,
        strength_score=score,
        reasons=["测试"],
        risks=["测试"],
    )
