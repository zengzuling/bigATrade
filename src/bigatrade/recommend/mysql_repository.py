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
                    run_id = self._find_existing_run_id(
                        cur=cur,
                        run_date=run_date,
                        run_type=run_type,
                        strategy_version=strategy_version,
                        data_source=data_source,
                    )
                    if run_id is None:
                        run_id = self._insert_run(
                            cur=cur,
                            run_date=run_date,
                            run_type=run_type,
                            strategy_version=strategy_version,
                            data_source=data_source,
                            diagnostics=diagnostics,
                            scan_limit=scan_limit,
                            plans=plans,
                            output_path=output_path,
                            remark=remark,
                        )
                    else:
                        self._update_run(
                            cur=cur,
                            run_id=run_id,
                            diagnostics=diagnostics,
                            scan_limit=scan_limit,
                            plans=plans,
                            output_path=output_path,
                            remark=remark,
                        )
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
                        ON DUPLICATE KEY UPDATE
                            recommend_date = VALUES(recommend_date),
                            rank_no = VALUES(rank_no),
                            stock_name = VALUES(stock_name),
                            sector_name = VALUES(sector_name),
                            market_heat = VALUES(market_heat),
                            close_price = VALUES(close_price),
                            buy_low = VALUES(buy_low),
                            buy_high = VALUES(buy_high),
                            buy_price = VALUES(buy_price),
                            target_price = VALUES(target_price),
                            stop_loss_price = VALUES(stop_loss_price),
                            target_gain_pct = VALUES(target_gain_pct),
                            max_holding_days = VALUES(max_holding_days),
                            strength_score = VALUES(strength_score),
                            recommend_reason = VALUES(recommend_reason),
                            risk_tip = VALUES(risk_tip)
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

    def _find_existing_run_id(
        self,
        cur,
        run_date: str,
        run_type: str,
        strategy_version: str,
        data_source: str,
    ) -> int | None:
        """查找同一日期、类型和策略版本的已有推荐批次。"""
        cur.execute(
            """
            SELECT id
            FROM recommend_runs
            WHERE run_date = %s
              AND run_type = %s
              AND strategy_version = %s
              AND data_source = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            (run_date, run_type, strategy_version, data_source),
        )
        row = cur.fetchone()
        return None if row is None else int(row[0])

    def _insert_run(
        self,
        cur,
        run_date: str,
        run_type: str,
        strategy_version: str,
        data_source: str,
        diagnostics: RecommendationDiagnostics,
        scan_limit: int | None,
        plans: list[TradePlan],
        output_path: Path | None,
        remark: str | None,
    ) -> int:
        """插入新的推荐批次。"""
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
        return int(cur.lastrowid)

    def _update_run(
        self,
        cur,
        run_id: int,
        diagnostics: RecommendationDiagnostics,
        scan_limit: int | None,
        plans: list[TradePlan],
        output_path: Path | None,
        remark: str | None,
    ) -> None:
        """更新已有推荐批次的统计信息。"""
        cur.execute(
            """
            UPDATE recommend_runs
            SET status = 'success',
                scan_limit = %s,
                scanned_count = %s,
                skipped_risky_count = %s,
                daily_bar_error_count = %s,
                empty_bar_count = %s,
                selected_count = %s,
                output_path = %s,
                finished_at = NOW(),
                remark = %s
            WHERE id = %s
            """,
            (
                scan_limit,
                diagnostics.scanned_stocks,
                diagnostics.risky_name_stocks,
                diagnostics.daily_bar_errors,
                diagnostics.empty_daily_bars,
                len(plans),
                str(output_path) if output_path else None,
                remark,
                run_id,
            ),
        )


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
