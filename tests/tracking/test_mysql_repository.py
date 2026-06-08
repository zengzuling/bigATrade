from bigatrade.tracking.mysql_repository import MySqlTrackingRepository, _quote_to_row
from bigatrade.tracking.performance import DailyQuote


class FakeCursor:
    """用于捕获 SQL 的游标桩对象。"""

    def __init__(self, rows):
        self.rows = rows
        self.executed_sql = None
        self.executed_params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params):
        self.executed_sql = sql
        self.executed_params = params

    def fetchall(self):
        return self.rows


class FakeConnection:
    """用于模拟 MySQL 连接上下文。"""

    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self._cursor


def test_list_open_recommendations_allows_same_day_rerun(monkeypatch):
    """同一交易日重跑时，应保留候选以便 upsert 修正错误表现数据。"""
    cursor = FakeCursor(rows=[])
    repository = MySqlTrackingRepository(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="secret",
        database="bigatrade",
    )
    monkeypatch.setattr(repository, "_connect", lambda: FakeConnection(cursor))

    repository.list_open_recommendations("2026-06-08")

    assert cursor.executed_params == ("2026-06-08", "2026-06-08")
    assert "q.trade_date <> %s" in cursor.executed_sql
    assert "NOT EXISTS" not in cursor.executed_sql


def test_quote_to_row_contains_gain_from_recommend_pct():
    """每日表现写库参数应包含相对推荐日涨跌幅字段。"""
    quote = DailyQuote(
        recommendation_id=1,
        run_id=2,
        recommend_date="2026-06-05",
        trade_date="2026-06-08",
        stock_code="600000",
        stock_name="测试股",
        open_price=10.0,
        close_price=11.0,
        high_price=11.2,
        low_price=9.9,
        pre_close_price=10.1,
        change_pct=8.9109,
        volume=1000.0,
        amount=11000000.0,
        gain_from_buy_pct=10.0,
        gain_from_close_pct=10.0,
        gain_from_recommend_pct=10.0,
        hit_target=True,
        hit_stop_loss=False,
    )

    row = _quote_to_row(quote)

    assert row[16] == 10.0
    assert row[17] == 1
    assert row[18] == 0
