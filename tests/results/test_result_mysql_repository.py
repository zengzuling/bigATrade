from bigatrade.results.mysql_repository import MySqlResultRepository


class FakeCursor:
    """捕获结果仓储查询 SQL 的测试游标。"""

    def __init__(self):
        self.executed_sql = ""
        self.executed_params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.executed_sql = sql
        self.executed_params = params

    def fetchall(self):
        return []


class FakeConnection:
    """模拟 MySQL 连接上下文。"""

    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor


def test_list_settlement_candidates_includes_existing_backtest_results(monkeypatch):
    """每日结算候选不应排除已写过结果的推荐，便于按当天 upsert。"""
    cursor = FakeCursor()
    repository = MySqlResultRepository(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="secret",
    )
    monkeypatch.setattr(repository, "_connect", lambda: FakeConnection(cursor))

    repository.list_settlement_candidates("2026-06-09")

    assert "LEFT JOIN backtest_results" not in cursor.executed_sql
    assert "br.id IS NULL" not in cursor.executed_sql
    assert "stock_recommendation_daily_quotes" in cursor.executed_sql
    assert cursor.executed_params == ("2026-06-09", "2026-06-09")
