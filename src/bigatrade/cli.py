from pathlib import Path

import typer

from bigatrade.data.akshare_provider import AkShareProvider
from bigatrade.output.writers import write_trade_plans_csv
from bigatrade.recommend.service import RecommendationService

app = typer.Typer(help="A股一周强势股捕捉与回测工具。")


@app.command()
def recommend(
    date: str = typer.Option(..., help="推荐交易日，格式 YYYY-MM-DD。"),
    top: int = typer.Option(30, help="输出前 N 只候选股。"),
    scan_limit: int | None = typer.Option(None, help="限制扫描股票数量，首次验证建议 100。"),
    output: Path | None = typer.Option(None, help="CSV 输出路径。"),
) -> None:
    """按指定交易日生成强势股推荐列表。"""
    service = create_recommendation_service()
    plans = service.recommend(date=date, top=top, scan_limit=scan_limit)
    output_path = output or Path("outputs") / f"recommend_{date}.csv"
    written_path = write_trade_plans_csv(plans, output_path)
    typer.echo(f"推荐结果已写入: {written_path}")


@app.command()
def backtest(start: str, end: str) -> None:
    """按历史区间回测一周 10% 目标策略。"""
    typer.echo(f"backtest start={start} end={end}")


def create_recommendation_service() -> RecommendationService:
    """创建默认推荐服务，生产环境使用 AkShare 免费数据。"""
    return RecommendationService(provider=AkShareProvider())
