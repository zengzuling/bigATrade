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

    def recommend(self, date: str, top: int = 30, scan_limit: int | None = None):
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
        ][:top]


def test_recommend_command_writes_csv(tmp_path, monkeypatch):
    """recommend 命令应调用推荐服务并写出 CSV 文件。"""
    monkeypatch.setattr(cli, "create_recommendation_service", lambda: FakeRecommendationService())
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
        ],
    )

    assert result.exit_code == 0
    assert str(output_path) in result.output
    assert output_path.exists()
