from pathlib import Path

import typer

from bigatrade.data.akshare_provider import AkShareProvider
from bigatrade.data.cache_provider import CachedMarketDataProvider
from bigatrade.output.writers import write_trade_plans_csv
from bigatrade.recommend.service import (
    RecommendationDiagnostics,
    RecommendationService,
    filter_plans_by_price_buckets,
    parse_price_buckets,
)

app = typer.Typer(help="A股一周强势股捕捉与回测工具。")


@app.command()
def recommend(
    date: str = typer.Option(..., help="推荐交易日，格式 YYYY-MM-DD。"),
    top: int = typer.Option(30, help="输出前 N 只候选股。"),
    scan_limit: str | None = typer.Option(None, help="限制扫描股票数量；传 all 表示全量扫描。"),
    price_buckets: str | None = typer.Option(None, help="价格分层，例如 0-10:2,10-20:2,20-50:1。"),
    prefilter_per_bucket: str | None = typer.Option(None, help="日线前候选预筛，例如 0-10:120,10-20:120,20-50:80。"),
    cache_dir: Path | None = typer.Option(Path("data/cache"), help="本地行情缓存目录；传空值则不启用缓存。"),
    output: Path | None = typer.Option(None, help="CSV 输出路径。"),
) -> None:
    """按指定交易日生成强势股推荐列表。"""
    service = create_recommendation_service(cache_dir=cache_dir)
    buckets = parse_price_buckets(price_buckets)
    prefilter_buckets = parse_price_buckets(prefilter_per_bucket)
    plans = service.recommend(
        date=date,
        top=top,
        scan_limit=_parse_scan_limit(scan_limit),
        price_buckets=buckets,
        prefilter_buckets=prefilter_buckets,
    )
    plans = filter_plans_by_price_buckets(plans, buckets)
    diagnostics = getattr(service, "last_diagnostics", None)
    if isinstance(diagnostics, RecommendationDiagnostics):
        diagnostics.output_plans = len(plans)
    output_path = output or Path("outputs") / f"recommend_{date}.csv"
    written_path = write_trade_plans_csv(plans, output_path)
    typer.echo(f"推荐结果已写入: {written_path}")
    if isinstance(diagnostics, RecommendationDiagnostics):
        typer.echo(_format_recommendation_diagnostics(diagnostics))


@app.command()
def backtest(start: str, end: str) -> None:
    """按历史区间回测一周 10% 目标策略。"""
    typer.echo(f"backtest start={start} end={end}")


def create_recommendation_service(cache_dir: Path | None = Path("data/cache")) -> RecommendationService:
    """创建默认推荐服务，生产环境使用 AkShare 免费数据。"""
    provider = AkShareProvider()
    if cache_dir is not None:
        return RecommendationService(provider=CachedMarketDataProvider(provider=provider, cache_dir=cache_dir))
    return RecommendationService(provider=provider)


def _format_recommendation_diagnostics(diagnostics: RecommendationDiagnostics) -> str:
    """格式化推荐流程统计，空结果时直接暴露失败阶段。"""
    return (
        "扫描统计: "
        f"股票总数={diagnostics.total_stocks}, "
        f"本次扫描={diagnostics.scanned_stocks}, "
        f"价格预筛后={diagnostics.price_prefiltered_stocks}, "
        f"候选预筛后={diagnostics.candidate_prefiltered_stocks}, "
        f"风险名称跳过={diagnostics.risky_name_stocks}, "
        f"日线异常={diagnostics.daily_bar_errors}, "
        f"日线为空={diagnostics.empty_daily_bars}, "
        f"策略过滤={diagnostics.score_filtered_stocks}, "
        f"入选候选={diagnostics.scored_plans}, "
        f"最终输出={diagnostics.output_plans}"
    )


def _parse_scan_limit(value: str | None) -> int | None:
    """解析扫描数量，支持 all/full 表示不限制。"""
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"", "all", "full"}:
        return None
    return int(normalized)
