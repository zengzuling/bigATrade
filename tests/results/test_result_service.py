from bigatrade.results.service import (
    DailyReviewRow,
    FiveDaySummary,
    QuoteForSettlement,
    RecommendationForSettlement,
    SettlementService,
    render_five_day_summary,
    render_review,
)


class FakeResultRepository:
    """测试用结果仓储，记录结算写入。"""

    def __init__(self):
        self.saved_results = []

    def list_settlement_candidates(self, as_of_date: str):
        return [
            RecommendationForSettlement(
                recommendation_id=1,
                run_id=2,
                recommend_date="2026-06-05",
                stock_code="600000",
                stock_name="测试股",
                close_price=10.0,
                buy_low=9.9,
                buy_high=10.2,
                buy_price=10.05,
                target_price=11.06,
                stop_loss_price=9.55,
                target_gain_pct=10.0,
                max_holding_days=5,
                strength_score=88.0,
                recommend_reason="站上均线",
                risk_tip="跌破止损退出",
            )
        ]

    def list_quotes(self, recommendation_id: int):
        return [
            QuoteForSettlement(
                trade_date="2026-06-08",
                open_price=10.0,
                high_price=10.5,
                low_price=9.95,
                close_price=10.3,
                change_pct=3.0,
                gain_from_recommend_pct=3.0,
                amount=10000000,
                hit_target=False,
                hit_stop_loss=False,
            ),
            QuoteForSettlement(
                trade_date="2026-06-09",
                open_price=10.4,
                high_price=11.2,
                low_price=10.3,
                close_price=11.1,
                change_pct=7.7,
                gain_from_recommend_pct=11.0,
                amount=20000000,
                hit_target=True,
                hit_stop_loss=False,
            ),
        ]

    def save_backtest_results(self, results):
        self.saved_results.extend(results)
        return len(results)


def test_settlement_service_saves_target_hit_result():
    """结算服务应把已命中目标的每日表现转换为回测结果。"""
    repository = FakeResultRepository()
    service = SettlementService(repository)

    result = service.settle("2026-06-09")

    assert result.candidate_count == 1
    assert result.settled_count == 1
    saved = repository.saved_results[0]
    assert saved.recommendation_id == 1
    assert saved.result.exit_reason == "止盈"
    assert saved.result.holding_days == 2


def test_render_review_outputs_wechat_sections():
    """复盘文案应输出标题、海报、今日复盘和明日计划。"""
    content = render_review(
        "2026-06-09",
        [
            DailyReviewRow(
                stock_code="600000",
                stock_name="测试股",
                close_price=11.1,
                change_pct=7.7,
                gain_from_recommend_pct=11.0,
                amount=200000000,
                hit_target=True,
                hit_stop_loss=False,
                recommend_reason="站上均线",
                risk_tip="跌破止损退出",
            )
        ],
    )

    assert "1. 标题" in content
    assert "2. 海报文案" in content
    assert "3. 今日复盘" in content
    assert "4. 明日计划" in content
    assert "测试股" in content


def test_render_five_day_summary_formats_core_metrics():
    """5 日总结应展示命中率、正收益占比和收益区间。"""
    content = render_five_day_summary(
        "2026-06-09",
        FiveDaySummary(
            result_count=4,
            hit_target_count=1,
            positive_count=3,
            average_return_pct=2.5,
            worst_return_pct=-5.0,
            best_return_pct=10.0,
        ),
    )

    assert "已结算 4 条推荐" in content
    assert "命中率 25.00%" in content
    assert "平均收益 2.50%" in content
