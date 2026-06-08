from bigatrade.hotspot.service import HotspotBoard, HotspotService


class FakeHotspotProvider:
    """测试用热点数据源。"""

    def industry_boards(self):
        return [
            HotspotBoard(board_type="industry", board_name="机器人", change_pct=4.0, turnover_rate=5.0, rise_count=16, fall_count=4, leading_stock="巨能股份", leading_stock_change_pct=30.0),
            HotspotBoard(board_type="industry", board_name="通信设备", change_pct=3.0, turnover_rate=4.0, rise_count=10, fall_count=2, leading_stock="测试股", leading_stock_change_pct=10.0),
            HotspotBoard(board_type="industry", board_name="银行", change_pct=-1.0, turnover_rate=1.0, rise_count=1, fall_count=20, leading_stock="弱股", leading_stock_change_pct=1.0),
        ]

    def concept_boards(self):
        return [
            HotspotBoard(board_type="concept", board_name="减速器", change_pct=2.0, turnover_rate=3.0, rise_count=20, fall_count=10, leading_stock="宁波东力", leading_stock_change_pct=9.98),
        ]


class FakeHotspotRepository:
    """测试用热点仓储。"""

    def __init__(self):
        self.saved = None

    def save_version(self, trade_date, boards, source):
        self.saved = (trade_date, boards, source)
        return 7


class FlakyHotspotProvider(FakeHotspotProvider):
    """第一次行业接口失败，第二次恢复，用于验证热点刷新重试。"""

    def __init__(self):
        self.industry_calls = 0

    def industry_boards(self):
        self.industry_calls += 1
        if self.industry_calls == 1:
            raise RuntimeError("temporary board api error")
        return super().industry_boards()


def test_hotspot_service_saves_version_and_returns_industry_bonus_map():
    """热点服务应保存热点版本，并按行业热点形成推荐加分映射。"""
    repository = FakeHotspotRepository()
    service = HotspotService(provider=FakeHotspotProvider(), repository=repository)

    version = service.refresh_hotspots("2026-06-08", top_industry=2, top_concept=1)

    assert version.version_id == 7
    assert [board.board_name for board in repository.saved[1]] == ["机器人", "通信设备", "减速器"]
    assert version.industry_bonus_scores["机器人"] > version.industry_bonus_scores["通信设备"]
    assert "减速器" not in version.industry_bonus_scores


def test_hotspot_service_retries_temporary_board_api_errors():
    """热点服务应重试临时接口错误，避免推荐前刷新热点直接失败。"""
    provider = FlakyHotspotProvider()
    service = HotspotService(provider=provider, repository=FakeHotspotRepository(), retry_delay_seconds=0)

    version = service.refresh_hotspots("2026-06-08", top_industry=1, top_concept=0)

    assert provider.industry_calls == 2
    assert version.industry_bonus_scores == {"机器人": 10.0}
