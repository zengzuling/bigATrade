from __future__ import annotations

from pathlib import Path

import pymysql

from bigatrade.recommend.service import RecommendationDiagnostics
from bigatrade.strategy.trade_plan import TradePlan


class MySqlRecommendationRepository:
    """推荐批次和推荐明细的 MySQL 仓储。"""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str = "bigatrade",
    ) -> None:
        self._connection_args = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "charset": "utf8mb4",
            "autocommit": False,
        }

    def save_successful_run(
        self,
        run_date: str,
        plans: list[TradePlan],
        diagnostics: RecommendationDiagnostics,
        scan_limit: int | None,
        output_path: Path | None,
        run_type: str = "daily_close",
        strategy_version: str = "strong_stock_v1",
        data_source: str = "akshare",
        remark: str | None = None,
    ) -> int:
        """保存一次成功推荐任务和对应推荐股票，返回批次 ID。"""
        with self._connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO recommend_runs (
                            run_date, run_type, status, strategy_version, data_source,
                            scan_limit, scanned_count, skipped_risky_count,
                            daily_bar_error_count, empty_bar_count, selected_count,
                            output_path, started_at, finished_at, remark
                        ) VALUES (
                            %s, %s, 'success', %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, NOW(), NOW(), %s
                        )
                        """,
                        (
                            run_date,
                            run_type,
                            strategy_version,
                            data_source,
                            scan_limit,
                            diagnostics.scanned_stocks,
                            diagnostics.risky_name_stocks,
                            diagnostics.daily_bar_errors,
                            diagnostics.empty_daily_bars,
                            len(plans),
                            str(output_path) if output_path else None,
                            remark,
                        ),
                    )
                    run_id = int(cur.lastrowid)
                    cur.executemany(
                        """
                        INSERT INTO stock_recommendations (
                            run_id, recommend_date, rank_no, stock_code, stock_name,
                            sector_name, market_heat, close_price, buy_low, buy_high,
                            buy_price, target_price, stop_loss_price, target_gain_pct,
                            max_holding_days, strength_score, recommend_reason, risk_tip
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s
                        )
                        """,
                        [_plan_to_row(run_id, rank_no, plan) for rank_no, plan in enumerate(plans, start=1)],
                    )
                conn.commit()
                return run_id
            except Exception:
                conn.rollback()
                raise

    def _connect(self):
        """创建 MySQL 连接。"""
        return pymysql.connect(**self._connection_args)


def _plan_to_row(run_id: int, rank_no: int, plan: TradePlan) -> tuple:
    """把推荐交易计划转换为 MySQL 写入参数。"""
    return (
        run_id,
        plan.recommend_date,
        rank_no,
        plan.code,
        plan.name,
        plan.sector_name,
        plan.market_heat,
        plan.close,
        plan.buy_low,
        plan.buy_high,
        plan.buy_price,
        plan.target_price,
        plan.stop_loss_price,
        plan.target_gain_pct,
        plan.max_holding_days,
        plan.strength_score,
        "; ".join(plan.reasons),
        "; ".join(plan.risks),
    )
