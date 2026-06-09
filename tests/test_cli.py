from datetime import datetime

from typer.testing import CliRunner

from bigatrade import cli
from bigatrade.hotspot.service import HotspotVersion
from bigatrade.recommend.service import RecommendationDiagnostics
from bigatrade.results.service import DailyReviewRow, FiveDaySummary
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
        self.last_diagnostics = RecommendationDiagnostics()

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


class FakeRecommendationRepository:
    """测试用推荐入库仓储。"""

    def __init__(self):
        self.saved_plans = []

    def save_successful_run(self, **kwargs):
        self.saved_plans = kwargs["plans"]
        return 12


def test_daily_run_tracks_then_recommends_and_saves(monkeypatch, tmp_path):
    """daily-run 应先跟踪旧推荐，再生成当天推荐并写入推荐表。"""
    fake_tracker = FakePerformanceTracker()
    fake_recommendation_service = FakeRecommendationService()
    fake_hotspot_service = FakeHotspotService()
    fake_repository = FakeRecommendationRepository()
    output_path = tmp_path / "recommend.csv"

    monkeypatch.setattr(cli, "_resolve_track_date", lambda value: "2026-06-09")
    monkeypatch.setattr(cli, "create_performance_tracker", lambda **kwargs: fake_tracker)
    monkeypatch.setattr(cli, "create_recommendation_service", lambda **kwargs: fake_recommendation_service)
    monkeypatch.setattr(cli, "create_hotspot_service", lambda **kwargs: fake_hotspot_service)
    monkeypatch.setattr(cli, "create_recommendation_repository", lambda **kwargs: fake_repository)

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        [
            "daily-run",
            "--date",
            "today",
            "--db-host",
            "127.0.0.1",
            "--db-user",
            "u",
            "--db-password",
            "p",
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0
    assert fake_tracker.tracked_date == "2026-06-09"
    assert fake_hotspot_service.called is True
    assert len(fake_repository.saved_plans) == 1
    assert "daily tracking: date=2026-06-09" in result.output
    assert "daily recommendation: date=2026-06-09, run_id=12" in result.output


class FakeResultRepository:
    """测试用结果仓储。"""

    def __init__(self):
        self.settled = False

    def list_settlement_candidates(self, as_of_date: str):
        return []

    def list_quotes(self, recommendation_id: int):
        return []

    def save_backtest_results(self, results):
        self.settled = True
        return len(results)

    def list_daily_review_rows(self, trade_date: str):
        return [
            DailyReviewRow(
                stock_code="600000",
                stock_name="测试股",
                close_price=10.5,
                change_pct=5.0,
                gain_from_recommend_pct=5.0,
                amount=100000000,
                hit_target=False,
                hit_stop_loss=False,
                recommend_reason="站上均线",
                risk_tip="跌破止损退出",
            )
        ]

    def load_five_day_summary(self, as_of_date: str):
        return FiveDaySummary(
            result_count=1,
            hit_target_count=0,
            positive_count=1,
            average_return_pct=5.0,
            worst_return_pct=5.0,
            best_return_pct=5.0,
        )


def test_settle_results_command_uses_result_repository(monkeypatch):
    """settle-results 命令应输出结算统计。"""
    monkeypatch.setattr(cli, "_resolve_track_date", lambda value: "2026-06-09")
    monkeypatch.setattr(cli, "create_result_repository", lambda **kwargs: FakeResultRepository())

    runner = CliRunner()
    result = runner.invoke(
        cli.app,
        ["settle-results", "--date", "today", "--db-host", "127.0.0.1", "--db-user", "u", "--db-password", "p"],
    )

    assert result.exit_code == 0
    assert "settled results: date=2026-06-09" in result.output


def test_summary_and_review_commands_render_outputs(monkeypatch):
    """summary 和 review 命令应从结果仓储读取数据并渲染文本。"""
    monkeypatch.setattr(cli, "_resolve_track_date", lambda value: "2026-06-09")
    monkeypatch.setattr(cli, "create_result_repository", lambda **kwargs: FakeResultRepository())
    runner = CliRunner()

    summary_result = runner.invoke(
        cli.app,
        ["five-day-summary", "--date", "today", "--db-host", "127.0.0.1", "--db-user", "u", "--db-password", "p"],
    )
    review_result = runner.invoke(
        cli.app,
        ["review", "--date", "today", "--db-host", "127.0.0.1", "--db-user", "u", "--db-password", "p"],
    )

    assert summary_result.exit_code == 0
    assert "已结算 1 条推荐" in summary_result.output
    assert review_result.exit_code == 0
    assert "测试股" in review_result.output


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
