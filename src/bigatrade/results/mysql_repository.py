from __future__ import annotations

import pymysql

from bigatrade.results.service import (
    DailyReviewRow,
    FiveDaySummary,
    QuoteForSettlement,
    RecommendationForSettlement,
    SettledBacktestResult,
)


class MySqlResultRepository:
    """推荐结算、5 日总结和复盘数据的 MySQL 仓储。"""

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

    def list_settlement_candidates(self, as_of_date: str) -> list[RecommendationForSettlement]:
        """查询尚未结算且可能满足退出条件的推荐股票。"""
        sql = """
            SELECT
                sr.id, sr.run_id, sr.recommend_date, sr.stock_code, sr.stock_name,
                sr.close_price, sr.buy_low, sr.buy_high, sr.buy_price,
                sr.target_price, sr.stop_loss_price, sr.target_gain_pct,
                sr.max_holding_days, sr.strength_score,
                COALESCE(sr.recommend_reason, ''), COALESCE(sr.risk_tip, '')
            FROM stock_recommendations sr
            LEFT JOIN backtest_results br ON br.recommendation_id = sr.id
            WHERE br.id IS NULL
              AND sr.recommend_date < %s
            ORDER BY sr.recommend_date, sr.rank_no, sr.id
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (as_of_date,))
                rows = cur.fetchall()
        return [_recommendation_from_row(row) for row in rows]

    def list_quotes(self, recommendation_id: int) -> list[QuoteForSettlement]:
        """查询单条推荐的已跟踪每日表现。"""
        sql = """
            SELECT
                trade_date, open_price, high_price, low_price, close_price,
                change_pct, gain_from_recommend_pct, amount,
                hit_target, hit_stop_loss
            FROM stock_recommendation_daily_quotes
            WHERE recommendation_id = %s
            ORDER BY trade_date
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (recommendation_id,))
                rows = cur.fetchall()
        return [_quote_from_row(row) for row in rows]

    def save_backtest_results(self, results: list[SettledBacktestResult]) -> int:
        """保存回测结算结果；重复结算时更新原记录。"""
        if not results:
            return 0
        sql = """
            INSERT INTO backtest_results (
                recommendation_id, run_id, recommend_date, stock_code,
                entry_date, exit_date, entry_price, exit_price,
                highest_gain_pct, hit_target, return_pct, exit_reason,
                holding_days
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s
            )
            ON DUPLICATE KEY UPDATE
                entry_date = VALUES(entry_date),
                exit_date = VALUES(exit_date),
                entry_price = VALUES(entry_price),
                exit_price = VALUES(exit_price),
                highest_gain_pct = VALUES(highest_gain_pct),
                hit_target = VALUES(hit_target),
                return_pct = VALUES(return_pct),
                exit_reason = VALUES(exit_reason),
                holding_days = VALUES(holding_days)
        """
        with self._connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.executemany(sql, [_result_to_row(result) for result in results])
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return len(results)

    def list_daily_review_rows(self, trade_date: str) -> list[DailyReviewRow]:
        """查询指定交易日的复盘行。"""
        sql = """
            SELECT
                q.stock_code, q.stock_name, q.close_price, q.change_pct,
                q.gain_from_recommend_pct, q.amount, q.hit_target, q.hit_stop_loss,
                COALESCE(sr.recommend_reason, ''), COALESCE(sr.risk_tip, '')
            FROM stock_recommendation_daily_quotes q
            JOIN stock_recommendations sr ON sr.id = q.recommendation_id
            WHERE q.trade_date = %s
            ORDER BY q.gain_from_recommend_pct DESC, q.amount DESC
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (trade_date,))
                rows = cur.fetchall()
        return [_review_row_from_row(row) for row in rows]

    def load_five_day_summary(self, as_of_date: str) -> FiveDaySummary:
        """读取截至指定日期已结算推荐的整体表现。"""
        sql = """
            SELECT
                COUNT(*),
                COALESCE(SUM(hit_target), 0),
                COALESCE(SUM(CASE WHEN return_pct > 0 THEN 1 ELSE 0 END), 0),
                COALESCE(AVG(return_pct), 0),
                COALESCE(MIN(return_pct), 0),
                COALESCE(MAX(return_pct), 0)
            FROM backtest_results
            WHERE recommend_date <= %s
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (as_of_date,))
                row = cur.fetchone()
        return FiveDaySummary(
            result_count=int(row[0]),
            hit_target_count=int(row[1]),
            positive_count=int(row[2]),
            average_return_pct=float(row[3]),
            worst_return_pct=float(row[4]),
            best_return_pct=float(row[5]),
        )

    def _connect(self):
        """创建 MySQL 连接。"""
        return pymysql.connect(**self._connection_args)


def _recommendation_from_row(row: tuple) -> RecommendationForSettlement:
    """把数据库行转换为待结算推荐。"""
    return RecommendationForSettlement(
        recommendation_id=int(row[0]),
        run_id=int(row[1]),
        recommend_date=str(row[2]),
        stock_code=str(row[3]),
        stock_name=str(row[4]),
        close_price=float(row[5]),
        buy_low=float(row[6]),
        buy_high=float(row[7]),
        buy_price=float(row[8]),
        target_price=float(row[9]),
        stop_loss_price=float(row[10]),
        target_gain_pct=float(row[11]),
        max_holding_days=int(row[12]),
        strength_score=float(row[13]),
        recommend_reason=str(row[14]),
        risk_tip=str(row[15]),
    )


def _quote_from_row(row: tuple) -> QuoteForSettlement:
    """把数据库行转换为结算行情。"""
    return QuoteForSettlement(
        trade_date=str(row[0]),
        open_price=float(row[1]),
        high_price=float(row[2]),
        low_price=float(row[3]),
        close_price=float(row[4]),
        change_pct=float(row[5]) if row[5] is not None else None,
        gain_from_recommend_pct=float(row[6]),
        amount=float(row[7] or 0),
        hit_target=bool(row[8]),
        hit_stop_loss=bool(row[9]),
    )


def _review_row_from_row(row: tuple) -> DailyReviewRow:
    """把数据库行转换为复盘数据。"""
    return DailyReviewRow(
        stock_code=str(row[0]),
        stock_name=str(row[1]),
        close_price=float(row[2]),
        change_pct=float(row[3]) if row[3] is not None else None,
        gain_from_recommend_pct=float(row[4]),
        amount=float(row[5] or 0),
        hit_target=bool(row[6]),
        hit_stop_loss=bool(row[7]),
        recommend_reason=str(row[8]),
        risk_tip=str(row[9]),
    )


def _result_to_row(result: SettledBacktestResult) -> tuple:
    """把结算结果转换为 MySQL 写入参数。"""
    backtest = result.result
    return (
        result.recommendation_id,
        result.run_id,
        backtest.recommend_date,
        backtest.code,
        backtest.entry_date,
        backtest.exit_date,
        backtest.entry_price,
        backtest.exit_price,
        backtest.highest_gain_pct,
        int(backtest.hit_target),
        backtest.return_pct,
        backtest.exit_reason,
        backtest.holding_days,
    )
