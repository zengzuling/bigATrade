import pandas as pd

from bigatrade.tracking.performance import DailyQuote, PerformanceTracker, RecommendationToTrack


class FakeProvider:
    """测试用行情源，返回推荐日和跟踪日两天数据。"""

    def daily_bars(self, code: str, start_date: str, end_date: str):
        return pd.DataFrame(
            {
                "date": ["2026-06-05", "2026-06-08"],
                "open": [10.0, 10.5],
                "close": [10.0, 11.2],
                "high": [10.2, 11.5],
                "low": [9.8, 10.4],
                "volume": [1000, 2000],
                "amount": [10_000_000, 22_000_000],
            }
        )


class FakeRepository:
    """记录跟踪服务写入的每日表现。"""

    def __init__(self):
        self.saved_quotes: list[DailyQuote] = []

    def list_open_recommendations(self, trade_date: str):
        return [
            RecommendationToTrack(
                recommendation_id=1,
                run_id=2,
                recommend_date="2026-06-05",
                stock_code="600000",
                stock_name="测试股票",
                recommend_close=10.0,
                buy_price=10.0,
                target_price=11.0,
                stop_loss_price=9.5,
                max_holding_days=5,
            )
        ]

    def save_daily_quotes(self, quotes: list[DailyQuote]) -> int:
        self.saved_quotes.extend(quotes)
        return len(quotes)


def test_tracker_saves_daily_quote_with_gain_and_target_flags():
    """跟踪服务应计算当日涨跌幅、相对买入价涨幅，并记录是否达到目标价。"""
    repository = FakeRepository()
    tracker = PerformanceTracker(provider=FakeProvider(), repository=repository)

    result = tracker.track("2026-06-08")

    assert result.tracked_count == 1
    quote = repository.saved_quotes[0]
    assert quote.trade_date == "2026-06-08"
    assert quote.close_price == 11.2
    assert quote.change_pct == 12.0
    assert quote.gain_from_buy_pct == 12.0
    assert quote.gain_from_close_pct == 12.0
    assert quote.gain_from_recommend_pct == 12.0
    assert quote.hit_target is True
    assert quote.hit_stop_loss is False
