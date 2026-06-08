from __future__ import annotations

import pymysql

from bigatrade.hotspot.service import HotspotBoard


class MySqlHotspotRepository:
    """市场热点版本 MySQL 仓储。"""

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

    def save_version(self, trade_date: str, boards: list[HotspotBoard], source: str) -> int:
        """保存热点版本和板块明细，返回版本 ID。"""
        with self._connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO market_hotspot_versions (trade_date, source, status)
                        VALUES (%s, %s, 'success')
                        """,
                        (trade_date, source),
                    )
                    version_id = int(cur.lastrowid)
                    cur.executemany(
                        """
                        INSERT INTO market_hotspot_boards (
                            version_id, rank_no, board_type, board_name, change_pct,
                            turnover_rate, rise_count, fall_count, leading_stock,
                            leading_stock_change_pct, bonus_score
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s
                        )
                        """,
                        [
                            _board_to_row(version_id, rank_no, board)
                            for rank_no, board in enumerate(boards, start=1)
                        ],
                    )
                conn.commit()
                return version_id
            except Exception:
                conn.rollback()
                raise

    def _connect(self):
        """创建 MySQL 连接。"""
        return pymysql.connect(**self._connection_args)


def _board_to_row(version_id: int, rank_no: int, board: HotspotBoard) -> tuple:
    """把热点板块转换为 MySQL 写入参数。"""
    return (
        version_id,
        rank_no,
        board.board_type,
        board.board_name,
        board.change_pct,
        board.turnover_rate,
        board.rise_count,
        board.fall_count,
        board.leading_stock,
        board.leading_stock_change_pct,
        _bonus_score(rank_no, board),
    )


def _bonus_score(rank_no: int, board: HotspotBoard) -> float:
    """计算存库展示用加分；概念板块第一版不参与个股行业精确加分。"""
    if board.board_type != "industry":
        return 0.0
    return max(2.0, round(10.0 - (rank_no - 1) * 0.5, 2))
