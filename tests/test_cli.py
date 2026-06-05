from typer.testing import CliRunner

from bigatrade.cli import app


def test_cli_shows_help():
    """命令行帮助应展示推荐和回测两个入口。"""
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "recommend" in result.output
    assert "backtest" in result.output
