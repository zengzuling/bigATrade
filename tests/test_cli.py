from typer.testing import CliRunner

from bigatrade import cli
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
    ):
        self.last_kwargs = {
            "scan_limit": scan_limit,
            "price_buckets": price_buckets,
            "prefilter_buckets": prefilter_buckets,
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
