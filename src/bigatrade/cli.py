import os
from datetime import date as date_type
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
from bigatrade.tracking.mysql_repository import MySqlTrackingRepository
from bigatrade.tracking.performance import PerformanceTracker

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


@app.command("track-performance")
def track_performance(
    date: str = typer.Option("today", help="跟踪交易日，格式 YYYY-MM-DD；today 表示当天。"),
    db_host: str | None = typer.Option(None, help="MySQL 地址；默认读 BIGATRADE_DB_HOST。"),
    db_port: int | None = typer.Option(None, help="MySQL 端口；默认读 BIGATRADE_DB_PORT。"),
    db_user: str | None = typer.Option(None, help="MySQL 用户；默认读 BIGATRADE_DB_USER。"),
    db_password: str | None = typer.Option(None, help="MySQL 密码；默认读 BIGATRADE_DB_PASSWORD。"),
    db_name: str = typer.Option("bigatrade", help="MySQL 数据库名。"),
    cache_dir: Path | None = typer.Option(Path("data/cache"), help="本地行情缓存目录。"),
) -> None:
    """抓取观察期内推荐股票的每日收盘表现并写入 MySQL。"""
    trade_date = _resolve_track_date(date)
    tracker = create_performance_tracker(
        db_host=db_host,
        db_port=db_port,
        db_user=db_user,
        db_password=db_password,
        db_name=db_name,
        cache_dir=cache_dir,
    )
    result = tracker.track(trade_date)
    typer.echo(
        f"daily quotes tracked: date={result.trade_date}, "
        f"candidates={result.candidate_count}, "
        f"tracked={result.tracked_count}, skipped={result.skipped_count}"
    )


def create_recommendation_service(cache_dir: Path | None = Path("data/cache")) -> RecommendationService:
    """创建默认推荐服务，生产环境使用 AkShare 免费数据。"""
    provider = AkShareProvider()
    if cache_dir is not None:
        return RecommendationService(provider=CachedMarketDataProvider(provider=provider, cache_dir=cache_dir))
    return RecommendationService(provider=provider)


def create_performance_tracker(
    db_host: str | None,
    db_port: int | None,
    db_user: str | None,
    db_password: str | None,
    db_name: str = "bigatrade",
    cache_dir: Path | None = Path("data/cache"),
) -> PerformanceTracker:
    """创建每日表现跟踪服务。"""
    provider = AkShareProvider()
    if cache_dir is not None:
        provider = CachedMarketDataProvider(provider=provider, cache_dir=cache_dir)
    repository = MySqlTrackingRepository(
        host=_required_option(db_host, "BIGATRADE_DB_HOST"),
        port=db_port or int(os.environ.get("BIGATRADE_DB_PORT", "3306")),
        user=_required_option(db_user, "BIGATRADE_DB_USER"),
        password=_required_option(db_password, "BIGATRADE_DB_PASSWORD"),
        database=db_name,
    )
    return PerformanceTracker(provider=provider, repository=repository)


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


def _resolve_track_date(value: str) -> str:
    """解析跟踪日期，today 表示当前日期。"""
    if value.lower() == "today":
        return date_type.today().strftime("%Y-%m-%d")
    return value


def _required_option(value: str | None, env_name: str) -> str:
    """读取命令行参数或环境变量，缺失时明确报错。"""
    resolved = value or os.environ.get(env_name)
    if not resolved:
        raise typer.BadParameter(f"缺少参数或环境变量 {env_name}")
    return resolved
