import os
from datetime import date as date_type
from datetime import datetime, time as time_type
from pathlib import Path
from zoneinfo import ZoneInfo

import typer

from bigatrade.data.akshare_provider import AkShareProvider
from bigatrade.data.cache_provider import CachedMarketDataProvider
from bigatrade.hotspot.mysql_repository import MySqlHotspotRepository
from bigatrade.hotspot.service import HotspotService
from bigatrade.output.writers import write_trade_plans_csv
from bigatrade.recommend.mysql_repository import MySqlRecommendationRepository
from bigatrade.recommend.service import (
    RecommendationDiagnostics,
    RecommendationService,
    filter_plans_by_price_buckets,
    parse_price_buckets,
)
from bigatrade.results.mysql_repository import MySqlResultRepository
from bigatrade.results.service import SettlementService, render_five_day_summary, render_review
from bigatrade.tracking.mysql_repository import MySqlTrackingRepository
from bigatrade.tracking.performance import PerformanceTracker

app = typer.Typer(help="A股一周强势股捕捉与回测工具。")
TRACK_READY_TIME = time_type(hour=15, minute=30)
CHINA_TIMEZONE = ZoneInfo("Asia/Shanghai")


@app.command()
def recommend(
    date: str = typer.Option(..., help="推荐交易日，格式 YYYY-MM-DD。"),
    top: int = typer.Option(30, help="输出前 N 只候选股。"),
    scan_limit: str | None = typer.Option(None, help="限制扫描股票数量；传 all 表示全量扫描。"),
    price_buckets: str | None = typer.Option(None, help="价格分层，例如 0-10:2,10-20:2,20-50:1。"),
    prefilter_per_bucket: str | None = typer.Option(None, help="日线前候选预筛，例如 0-10:120,10-20:120,20-50:80。"),
    cache_dir: Path | None = typer.Option(Path("data/cache"), help="本地行情缓存目录；传空值则不启用缓存。"),
    hotspot_db_host: str | None = typer.Option(None, help="热点版本 MySQL 地址；传入后推荐前刷新热点版本。"),
    hotspot_db_port: int | None = typer.Option(None, help="热点版本 MySQL 端口。"),
    hotspot_db_user: str | None = typer.Option(None, help="热点版本 MySQL 用户。"),
    hotspot_db_password: str | None = typer.Option(None, help="热点版本 MySQL 密码。"),
    hotspot_db_name: str = typer.Option("bigatrade", help="热点版本 MySQL 数据库名。"),
    hotspot_top_industry: int = typer.Option(20, help="参与热点加分的行业板块数量。"),
    hotspot_top_concept: int = typer.Option(20, help="写入热点版本的概念板块数量。"),
    db_host: str | None = typer.Option(None, help="推荐结果 MySQL 地址；传入后同步写入推荐表。"),
    db_port: int | None = typer.Option(None, help="推荐结果 MySQL 端口。"),
    db_user: str | None = typer.Option(None, help="推荐结果 MySQL 用户。"),
    db_password: str | None = typer.Option(None, help="推荐结果 MySQL 密码。"),
    db_name: str = typer.Option("bigatrade", help="推荐结果 MySQL 数据库名。"),
    output: Path | None = typer.Option(None, help="CSV 输出路径。"),
) -> None:
    """按指定交易日生成强势股推荐列表。"""
    service = create_recommendation_service(cache_dir=cache_dir)
    buckets = parse_price_buckets(price_buckets)
    prefilter_buckets = parse_price_buckets(prefilter_per_bucket)
    hotspot_scores: dict[str, float] | None = None
    if hotspot_db_host:
        hotspot_version = create_hotspot_service(
            db_host=hotspot_db_host,
            db_port=hotspot_db_port,
            db_user=hotspot_db_user,
            db_password=hotspot_db_password,
            db_name=hotspot_db_name,
        ).refresh_hotspots(
            trade_date=date,
            top_industry=hotspot_top_industry,
            top_concept=hotspot_top_concept,
        )
        hotspot_scores = hotspot_version.industry_bonus_scores
        typer.echo(
            f"热点版本已写入: id={hotspot_version.version_id}, "
            f"行业加分板块={len(hotspot_scores)}"
        )
    plans = service.recommend(
        date=date,
        top=top,
        scan_limit=_parse_scan_limit(scan_limit),
        price_buckets=buckets,
        prefilter_buckets=prefilter_buckets,
        hotspot_scores=hotspot_scores,
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
    if db_host:
        run_id = create_recommendation_repository(
            db_host=db_host,
            db_port=db_port,
            db_user=db_user,
            db_password=db_password,
            db_name=db_name,
        ).save_successful_run(
            run_date=date,
            plans=plans,
            diagnostics=diagnostics if isinstance(diagnostics, RecommendationDiagnostics) else RecommendationDiagnostics(),
            scan_limit=_parse_scan_limit(scan_limit),
            output_path=written_path,
        )
        typer.echo(f"推荐结果已入库: run_id={run_id}, recommendations={len(plans)}")


@app.command()
def backtest(start: str, end: str) -> None:
    """按历史区间回测一周 10% 目标策略。"""
    typer.echo(f"backtest start={start} end={end}")


@app.command("daily-run")
def daily_run(
    date: str = typer.Option("today", help="运行交易日；today 表示最近已收盘交易日。"),
    top: int = typer.Option(30, help="输出前 N 只候选股。"),
    scan_limit: str | None = typer.Option(None, help="限制扫描股票数量；传 all 表示全量扫描。"),
    price_buckets: str | None = typer.Option(None, help="价格分层，例如 0-10:2,10-20:2,20-50:1。"),
    prefilter_per_bucket: str | None = typer.Option(None, help="日线前候选预筛，例如 0-10:120。"),
    cache_dir: Path | None = typer.Option(Path("data/cache"), help="本地行情缓存目录。"),
    db_host: str | None = typer.Option(None, help="MySQL 地址；默认读 BIGATRADE_DB_HOST。"),
    db_port: int | None = typer.Option(None, help="MySQL 端口；默认读 BIGATRADE_DB_PORT。"),
    db_user: str | None = typer.Option(None, help="MySQL 用户；默认读 BIGATRADE_DB_USER。"),
    db_password: str | None = typer.Option(None, help="MySQL 密码；默认读 BIGATRADE_DB_PASSWORD。"),
    db_name: str = typer.Option("bigatrade", help="MySQL 数据库名。"),
    hotspot_top_industry: int = typer.Option(20, help="参与热点加分的行业板块数量。"),
    hotspot_top_concept: int = typer.Option(20, help="写入热点版本的概念板块数量。"),
    output: Path | None = typer.Option(None, help="CSV 输出路径。"),
) -> None:
    """执行收盘后流水线：跟踪旧推荐、刷新热点、生成并入库新推荐。"""
    trade_date = _resolve_track_date(date)
    db_host = _required_option(db_host, "BIGATRADE_DB_HOST")
    db_user = _required_option(db_user, "BIGATRADE_DB_USER")
    db_password = _required_option(db_password, "BIGATRADE_DB_PASSWORD")
    resolved_port = db_port or int(os.environ.get("BIGATRADE_DB_PORT", "3306"))

    tracking_result = create_performance_tracker(
        db_host=db_host,
        db_port=resolved_port,
        db_user=db_user,
        db_password=db_password,
        db_name=db_name,
        cache_dir=cache_dir,
    ).track(trade_date)
    typer.echo(
        f"daily tracking: date={tracking_result.trade_date}, "
        f"candidates={tracking_result.candidate_count}, "
        f"tracked={tracking_result.tracked_count}, skipped={tracking_result.skipped_count}"
    )

    hotspot_version = create_hotspot_service(
        db_host=db_host,
        db_port=resolved_port,
        db_user=db_user,
        db_password=db_password,
        db_name=db_name,
    ).refresh_hotspots(
        trade_date=trade_date,
        top_industry=hotspot_top_industry,
        top_concept=hotspot_top_concept,
    )
    typer.echo(f"热点版本已写入: id={hotspot_version.version_id}")

    service = create_recommendation_service(cache_dir=cache_dir)
    buckets = parse_price_buckets(price_buckets)
    prefilter_buckets = parse_price_buckets(prefilter_per_bucket)
    scan_limit_value = _parse_scan_limit(scan_limit)
    plans = service.recommend(
        date=trade_date,
        top=top,
        scan_limit=scan_limit_value,
        price_buckets=buckets,
        prefilter_buckets=prefilter_buckets,
        hotspot_scores=hotspot_version.industry_bonus_scores,
    )
    plans = filter_plans_by_price_buckets(plans, buckets)
    diagnostics = service.last_diagnostics
    diagnostics.output_plans = len(plans)
    output_path = output or Path("outputs") / f"recommend_{trade_date}.csv"
    written_path = write_trade_plans_csv(plans, output_path)
    run_id = create_recommendation_repository(
        db_host=db_host,
        db_port=resolved_port,
        db_user=db_user,
        db_password=db_password,
        db_name=db_name,
    ).save_successful_run(
        run_date=trade_date,
        plans=plans,
        diagnostics=diagnostics,
        scan_limit=scan_limit_value,
        output_path=written_path,
        remark=f"hotspot_version_id={hotspot_version.version_id}",
    )
    typer.echo(
        f"daily recommendation: date={trade_date}, run_id={run_id}, "
        f"recommendations={len(plans)}, output={written_path}"
    )
    typer.echo(_format_recommendation_diagnostics(diagnostics))


@app.command("settle-results")
def settle_results(
    date: str = typer.Option("today", help="结算截至交易日；today 表示最近已收盘交易日。"),
    db_host: str | None = typer.Option(None, help="MySQL 地址；默认读 BIGATRADE_DB_HOST。"),
    db_port: int | None = typer.Option(None, help="MySQL 端口；默认读 BIGATRADE_DB_PORT。"),
    db_user: str | None = typer.Option(None, help="MySQL 用户；默认读 BIGATRADE_DB_USER。"),
    db_password: str | None = typer.Option(None, help="MySQL 密码；默认读 BIGATRADE_DB_PASSWORD。"),
    db_name: str = typer.Option("bigatrade", help="MySQL 数据库名。"),
) -> None:
    """把已跟踪的每日表现结算为 5 日回测结果。"""
    trade_date = _resolve_track_date(date)
    result = SettlementService(
        create_result_repository(
            db_host=db_host,
            db_port=db_port,
            db_user=db_user,
            db_password=db_password,
            db_name=db_name,
        )
    ).settle(trade_date)
    typer.echo(
        f"settled results: date={trade_date}, candidates={result.candidate_count}, "
        f"settled={result.settled_count}, skipped={result.skipped_count}"
    )


@app.command("five-day-summary")
def five_day_summary(
    date: str = typer.Option("today", help="总结截至交易日；today 表示最近已收盘交易日。"),
    db_host: str | None = typer.Option(None, help="MySQL 地址；默认读 BIGATRADE_DB_HOST。"),
    db_port: int | None = typer.Option(None, help="MySQL 端口；默认读 BIGATRADE_DB_PORT。"),
    db_user: str | None = typer.Option(None, help="MySQL 用户；默认读 BIGATRADE_DB_USER。"),
    db_password: str | None = typer.Option(None, help="MySQL 密码；默认读 BIGATRADE_DB_PASSWORD。"),
    db_name: str = typer.Option("bigatrade", help="MySQL 数据库名。"),
) -> None:
    """输出截至指定日期的 5 日结果总结。"""
    trade_date = _resolve_track_date(date)
    repository = create_result_repository(
        db_host=db_host,
        db_port=db_port,
        db_user=db_user,
        db_password=db_password,
        db_name=db_name,
    )
    typer.echo(render_five_day_summary(trade_date, repository.load_five_day_summary(trade_date)))


@app.command("review")
def review(
    date: str = typer.Option("today", help="复盘交易日；today 表示最近已收盘交易日。"),
    db_host: str | None = typer.Option(None, help="MySQL 地址；默认读 BIGATRADE_DB_HOST。"),
    db_port: int | None = typer.Option(None, help="MySQL 端口；默认读 BIGATRADE_DB_PORT。"),
    db_user: str | None = typer.Option(None, help="MySQL 用户；默认读 BIGATRADE_DB_USER。"),
    db_password: str | None = typer.Option(None, help="MySQL 密码；默认读 BIGATRADE_DB_PASSWORD。"),
    db_name: str = typer.Option("bigatrade", help="MySQL 数据库名。"),
) -> None:
    """根据每日表现生成公众号复盘初稿。"""
    trade_date = _resolve_track_date(date)
    repository = create_result_repository(
        db_host=db_host,
        db_port=db_port,
        db_user=db_user,
        db_password=db_password,
        db_name=db_name,
    )
    typer.echo(render_review(trade_date, repository.list_daily_review_rows(trade_date)))


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


def create_hotspot_service(
    db_host: str,
    db_port: int | None,
    db_user: str | None,
    db_password: str | None,
    db_name: str = "bigatrade",
) -> HotspotService:
    """创建市场热点刷新服务。"""
    repository = MySqlHotspotRepository(
        host=db_host,
        port=db_port or int(os.environ.get("BIGATRADE_DB_PORT", "3306")),
        user=_required_option(db_user, "BIGATRADE_DB_USER"),
        password=_required_option(db_password, "BIGATRADE_DB_PASSWORD"),
        database=db_name,
    )
    return HotspotService(provider=AkShareProvider(), repository=repository)


def create_recommendation_repository(
    db_host: str | None,
    db_port: int | None,
    db_user: str | None,
    db_password: str | None,
    db_name: str = "bigatrade",
) -> MySqlRecommendationRepository:
    """创建推荐入库仓储。"""
    return MySqlRecommendationRepository(
        host=_required_option(db_host, "BIGATRADE_DB_HOST"),
        port=db_port or int(os.environ.get("BIGATRADE_DB_PORT", "3306")),
        user=_required_option(db_user, "BIGATRADE_DB_USER"),
        password=_required_option(db_password, "BIGATRADE_DB_PASSWORD"),
        database=db_name,
    )


def create_result_repository(
    db_host: str | None,
    db_port: int | None,
    db_user: str | None,
    db_password: str | None,
    db_name: str = "bigatrade",
) -> MySqlResultRepository:
    """创建结果结算与复盘仓储。"""
    return MySqlResultRepository(
        host=_required_option(db_host, "BIGATRADE_DB_HOST"),
        port=db_port or int(os.environ.get("BIGATRADE_DB_PORT", "3306")),
        user=_required_option(db_user, "BIGATRADE_DB_USER"),
        password=_required_option(db_password, "BIGATRADE_DB_PASSWORD"),
        database=db_name,
    )


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
    """解析跟踪日期，today 自动映射为最近一个已收盘交易日。"""
    if value.lower() == "today":
        now = _current_china_datetime()
        today = now.date().strftime("%Y-%m-%d")
        trade_dates = _load_trade_dates()
        allow_same_day = now.time() >= TRACK_READY_TIME
        return _latest_closed_trade_date(trade_dates, today, allow_same_day=allow_same_day)
    return value


def _current_china_datetime() -> datetime:
    """返回北京时间，便于统一判断 A 股是否已经收盘。"""
    return datetime.now(CHINA_TIMEZONE)


def _load_trade_dates() -> list[str]:
    """加载 A 股交易日历，避免周末和法定节假日误判。"""
    provider = AkShareProvider()
    raw = provider._ak.tool_trade_date_hist_sina()
    return sorted(raw["trade_date"].astype(str).tolist())


def _latest_closed_trade_date(trade_dates: list[str], today: str, allow_same_day: bool) -> str:
    """从交易日历中选出最近一个已收盘交易日。"""
    for trade_date in reversed(trade_dates):
        if allow_same_day:
            if trade_date <= today:
                return trade_date
        else:
            if trade_date < today:
                return trade_date
    raise typer.BadParameter("交易日历为空，无法解析可追踪交易日")


def _required_option(value: str | None, env_name: str) -> str:
    """读取命令行参数或环境变量，缺失时明确报错。"""
    resolved = value or os.environ.get(env_name)
    if not resolved:
        raise typer.BadParameter(f"缺少参数或环境变量 {env_name}")
    return resolved
