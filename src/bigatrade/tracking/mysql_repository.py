from __future__ import annotations

import json
from dataclasses import asdict

import pymysql

from bigatrade.tracking.performance import DailyQuote, RecommendationToTrack


class MySqlTrackingRepository:
    """推荐股票每日表现的 MySQL 仓储。"""

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

    def list_open_recommendations(self, trade_date: str) -> list[RecommendationToTrack]:
        """查询指定交易日仍处于观察期的推荐股票，允许同日重跑修正已写入数据。"""
        sql = """
            SELECT
                sr.id,
                sr.run_id,
                sr.recommend_date,
                sr.stock_code,
                sr.stock_name,
                sr.close_price,
                sr.buy_price,
                sr.target_price,
                sr.stop_loss_price,
                sr.max_holding_days
            FROM stock_recommendations sr
            WHERE sr.recommend_date <= %s
              AND (
                  SELECT COUNT(*)
                  FROM stock_recommendation_daily_quotes q
                  WHERE q.recommendation_id = sr.id
                    AND q.trade_date <> %s
              )
              < sr.max_holding_days
            ORDER BY sr.recommend_date, sr.rank_no, sr.id
        """
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (trade_date, trade_date))
                rows = cur.fetchall()
        return [
            RecommendationToTrack(
                recommendation_id=int(row[0]),
                run_id=int(row[1]),
                recommend_date=str(row[2]),
                stock_code=str(row[3]),
                stock_name=str(row[4]),
                recommend_close=float(row[5]),
                buy_price=float(row[6]),
                target_price=float(row[7]),
                stop_loss_price=float(row[8]),
                max_holding_days=int(row[9]),
            )
            for row in rows
        ]

    def save_daily_quotes(self, quotes: list[DailyQuote]) -> int:
        """批量写入每日表现；重复执行同一天时更新原记录。"""
        if not quotes:
            return 0

        sql = """
            INSERT INTO stock_recommendation_daily_quotes (
                recommendation_id, run_id, recommend_date, trade_date, stock_code, stock_name,
                open_price, close_price, high_price, low_price, pre_close_price, change_pct,
                volume, amount, gain_from_buy_pct, gain_from_close_pct, gain_from_recommend_pct, hit_target,
                hit_stop_loss, raw_json
            ) VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s,
                %s, %s
            )
            ON DUPLICATE KEY UPDATE
                open_price = VALUES(open_price),
                close_price = VALUES(close_price),
                high_price = VALUES(high_price),
                low_price = VALUES(low_price),
                pre_close_price = VALUES(pre_close_price),
                change_pct = VALUES(change_pct),
                volume = VALUES(volume),
                amount = VALUES(amount),
                gain_from_buy_pct = VALUES(gain_from_buy_pct),
                gain_from_close_pct = VALUES(gain_from_close_pct),
                gain_from_recommend_pct = VALUES(gain_from_recommend_pct),
                hit_target = VALUES(hit_target),
                hit_stop_loss = VALUES(hit_stop_loss),
                raw_json = VALUES(raw_json)
        """
        values = [_quote_to_row(quote) for quote in quotes]
        with self._connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.executemany(sql, values)
                conn.commit()
            except Exception:
                conn.rollback()
                raise
        return len(quotes)

    def _connect(self):
        """创建 MySQL 连接。"""
        return pymysql.connect(**self._connection_args)


def _quote_to_row(quote: DailyQuote) -> tuple:
    """把每日表现对象转换为 MySQL 写入参数。"""
    return (
        quote.recommendation_id,
        quote.run_id,
        quote.recommend_date,
        quote.trade_date,
        quote.stock_code,
        quote.stock_name,
        quote.open_price,
        quote.close_price,
        quote.high_price,
        quote.low_price,
        quote.pre_close_price,
        quote.change_pct,
        quote.volume,
        quote.amount,
        quote.gain_from_buy_pct,
        quote.gain_from_close_pct,
        quote.gain_from_recommend_pct,
        int(quote.hit_target),
        int(quote.hit_stop_loss),
        json.dumps(asdict(quote), ensure_ascii=False),
    )
