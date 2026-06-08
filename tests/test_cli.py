from datetime import datetime

from typer.testing import CliRunner

from bigatrade import cli
from bigatrade.hotspot.service import HotspotVersion
from bigatrade.tracking.performance import TrackingResult
from bigatrade.strategy.trade_plan import build_trade_plan


def test_cli_shows_help():
    """命令行帮助应展示推荐和回测两个入口。"""
    runner = CliRunner()
    result = runner.invoke(cli.app, ["--help"])

    assert result.exit_code == 0
    assert "recommend" in result.output
    assert "backtest" in result.output


class FakeRecommendationService:
    """测试用推荐服务，避免 CLI 测试依赖 AkShare 网络。"""

    def __init__(self):
        self.last_kwargs = {}

    def recommend(
        self,
        date: str,
        top: int = 30,
        scan_limit: int | None = None,
        price_buckets=None,
        prefilter_buckets=None,
        hotspot_scores=None,
    ):
        self.last_kwargs = {
            "scan_limit": scan_limit,
            "price_buckets": price_buckets,
            "prefilter_buckets": prefilter_buckets,
            "hotspot_scores": hotspot_scores,
        }
        return [
            build_trade_plan(
                recommend_date=date,
                code="600000",
                name="浦发银行",
                close=10.0,
                strength_score=88.0,
                reasons=["站上多条均线"],
                risks=["跌破均线则退出"],
            )
        ]


def test_recommend_command_writes_csv(tmp_path, monkeypatch):
    """recommend 命令应调用推荐服务并写出 CSV 文件。"""
    monkeypatch.setattr(cli, "create_recommendation_service", lambda **kwargs: FakeRecommendationService())
    output_path = tmp_path / "recommend.csv"

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "recommend",
            "--date",
            "2026-06-05",
            "--top",
            "1",
            "--scan-limit",
            "10",
            "--output",
            str(output_path),
            "--price-buckets",
            "0-10:1",
        ],
    )

    assert result.exit_code == 0
    assert str(output_path) in result.output
    assert output_path.exists()


def test_recommend_command_accepts_all_scan_limit_and_prefilter_buckets(tmp_path, monkeypatch):
    """recommend 命令应支持全量扫描和日线前候选预筛参数。"""
    fake_service = FakeRecommendationService()
    monkeypatch.setattr(cli, "create_recommendation_service", lambda **kwargs: fake_service)
    output_path = tmp_path / "recommend.csv"

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "recommend",
            "--date",
            "2026-06-05",
            "--scan-limit",
            "all",
            "--price-buckets",
            "0-10:2,10-20:2,20-50:1",
            "--prefilter-per-bucket",
            "0-10:120,10-20:120,20-50:80",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert fake_service.last_kwargs["scan_limit"] is None
    assert [(bucket.low, bucket.high, bucket.count) for bucket in fake_service.last_kwargs["prefilter_buckets"]] == [
        (0, 10, 120),
        (10, 20, 120),
        (20, 50, 80),
    ]


class FakeHotspotService:
    """测试用热点服务。"""

    def __init__(self):
        self.called = False

    def refresh_hotspots(self, trade_date: str, top_industry: int = 20, top_concept: int = 20):
        self.called = True
        return HotspotVersion(
            version_id=9,
            trade_date=trade_date,
            boards=[],
            industry_bonus_scores={"通信设备": 8.0},
        )


def test_recommend_command_refreshes_hotspots_before_recommend(tmp_path, monkeypatch):
    """传入热点数据库参数时，recommend 应先刷新热点版本再推荐。"""
    fake_service = FakeRecommendationService()
    fake_hotspot_service = FakeHotspotService()
    monkeypatch.setattr(cli, "create_recommendation_service", lambda **kwargs: fake_service)
    monkeypatch.setattr(cli, "create_hotspot_service", lambda **kwargs: fake_hotspot_service)
    output_path = tmp_path / "recommend.csv"

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "recommend",
            "--date",
            "2026-06-05",
            "--hotspot-db-host",
            "127.0.0.1",
            "--hotspot-db-user",
            "u",
            "--hotspot-db-password",
            "p",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert fake_hotspot_service.called is True
    assert fake_service.last_kwargs["hotspot_scores"] == {"通信设备": 8.0}
    assert "热点版本已写入: id=9" in result.output


class FakePerformanceTracker:
    """测试用表现跟踪服务，避免 CLI 测试连接 MySQL 和 AkShare。"""

    def __init__(self):
        self.tracked_date = None

    def track(self, trade_date: str):
        self.tracked_date = trade_date
        return TrackingResult(trade_date=trade_date, candidate_count=5, tracked_count=5, skipped_count=0)


def test_track_performance_command_tracks_daily_quotes(monkeypatch):
    """track-performance 命令应按指定日期触发表现跟踪。"""
    fake_tracker = FakePerformanceTracker()
    monkeypatch.setattr(cli, "create_performance_tracker", lambda **kwargs: fake_tracker)

    runner = CliRunner()
    result = runner.invoke(cli.app, ["track-performance", "--date", "2026-06-08"])

    assert result.exit_code == 0
    assert fake_tracker.tracked_date == "2026-06-08"
    assert "tracked=5" in result.output


def test_resolve_track_date_uses_previous_trade_day_before_market_close(monkeypatch):
    """today 在收盘前应回退到最近一个已收盘交易日。"""
    monkeypatch.setattr(cli, "_current_china_datetime", lambda: datetime(2026, 6, 8, 11, 0, 0))
    monkeypatch.setattr(
        cli,
        "_load_trade_dates",
        lambda: ["2026-06-04", "2026-06-05", "2026-06-08"],
    )

    assert cli._resolve_track_date("today") == "2026-06-05"


def test_resolve_track_date_uses_today_after_market_close(monkeypatch):
    """today 在收盘缓冲时间后可使用当天交易日。"""
    monkeypatch.setattr(cli, "_current_china_datetime", lambda: datetime(2026, 6, 8, 15, 30, 0))
    monkeypatch.setattr(
        cli,
        "_load_trade_dates",
        lambda: ["2026-06-04", "2026-06-05", "2026-06-08"],
    )

    assert cli._resolve_track_date("today") == "2026-06-08"


def test_resolve_track_date_uses_latest_trade_day_on_non_trading_day(monkeypatch):
    """today 落在非交易日时应回退到最近交易日。"""
    monkeypatch.setattr(cli, "_current_china_datetime", lambda: datetime(2026, 6, 7, 18, 0, 0))
    monkeypatch.setattr(
        cli,
        "_load_trade_dates",
        lambda: ["2026-06-04", "2026-06-05", "2026-06-08"],
    )

    assert cli._resolve_track_date("today") == "2026-06-05"
