from bigatrade.strategy.trade_plan import build_trade_plan


def test_build_trade_plan_uses_fixed_risk_reward_rules():
    """交易计划应由固定风控规则生成，而不是由 AI 猜价格。"""
    plan = build_trade_plan(
        recommend_date="2026-06-05",
        code="600000",
        name="浦发银行",
        close=10.0,
        strength_score=88.0,
        reasons=["站上多条均线"],
        risks=["若放量长阴则趋势失效"],
    )

    assert plan.buy_low == 9.9
    assert plan.buy_high == 10.2
    assert plan.buy_price == 10.05
    assert plan.target_price == 11.06
    assert plan.stop_loss_price == 9.55
    assert plan.target_gain_pct == 10.0
    assert plan.max_holding_days == 5


def test_build_trade_plan_keeps_sector_and_market_heat():
    """交易计划应携带所属板块和市场热度，供 CSV 输出复核。"""
    plan = build_trade_plan(
        recommend_date="2026-06-05",
        code="600000",
        name="浦发银行",
        close=10.0,
        strength_score=88.0,
        reasons=["站上多条均线"],
        risks=["若放量长阴则趋势失效"],
        sector_name="银行",
        market_heat="涨跌幅 2.15%，上涨占比 80.00%，排名 12",
    )

    assert plan.sector_name == "银行"
    assert plan.market_heat == "涨跌幅 2.15%，上涨占比 80.00%，排名 12"
