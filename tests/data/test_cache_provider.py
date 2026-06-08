import pandas as pd

from bigatrade.data.cache_provider import CachedMarketDataProvider
from tests.recommend.test_service import FakeProvider


class CountingProvider(FakeProvider):
    """记录日线接口调用次数，验证缓存是否真正减少 AkShare 请求。"""

    def __init__(self):
        self.daily_calls = 0

    def daily_bars(self, code: str, start_date: str, end_date: str):
        self.daily_calls += 1
        return super().daily_bars(code, start_date, end_date)


def test_cached_provider_reuses_daily_bars_from_disk(tmp_path):
    """同一股票和日期范围的日线应命中本地缓存，避免重复请求。"""
    provider = CountingProvider()
    cached = CachedMarketDataProvider(provider=provider, cache_dir=tmp_path)

    first = cached.daily_bars("600000", "2026-03-07", "2026-06-05")
    second = cached.daily_bars("600000", "2026-03-07", "2026-06-05")

    assert provider.daily_calls == 1
    pd.testing.assert_frame_equal(first, second)
