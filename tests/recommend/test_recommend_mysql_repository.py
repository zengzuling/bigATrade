from bigatrade.recommend.mysql_repository import MySqlRecommendationRepository
from bigatrade.recommend.service import RecommendationDiagnostics
from bigatrade.strategy.trade_plan import build_trade_plan


class FakeCursor:
    """捕获推荐入库 SQL 的测试游标。"""

    def __init__(self):
        self.statements = []
        self.lastrowid = 9

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.statements.append((sql, params))

    def executemany(self, sql, values):
        self.statements.append((sql, values))

    def fetchone(self):
        return (7,)


class FakeConnection:
    """模拟 MySQL 连接上下文。"""

    def __init__(self, cursor):
        self.cursor_obj = cursor
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_save_successful_run_updates_existing_run_and_upserts_plans(monkeypatch):
    """同日推荐重跑时应更新已有批次，避免重复新增已落库推荐。"""
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    repository = MySqlRecommendationRepository(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="secret",
    )
    monkeypatch.setattr(repository, "_connect", lambda: connection)

    run_id = repository.save_successful_run(
        run_date="2026-06-08",
        plans=[
            build_trade_plan(
                recommend_date="2026-06-08",
                code="600000",
                name="测试股",
                close=10.0,
                strength_score=88.0,
                reasons=["站上均线"],
                risks=["跌破止损退出"],
            )
        ],
        diagnostics=RecommendationDiagnostics(scanned_stocks=1, output_plans=1),
        scan_limit=None,
        output_path=None,
    )

    sql_text = "\n".join(statement[0] for statement in cursor.statements)
    assert run_id == 7
    assert "UPDATE recommend_runs" in sql_text
    assert "INSERT INTO recommend_runs" not in sql_text
    assert "ON DUPLICATE KEY UPDATE" in sql_text
    assert connection.committed is True
