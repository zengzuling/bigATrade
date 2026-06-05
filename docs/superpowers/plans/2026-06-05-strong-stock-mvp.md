# Strong Stock MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first testable MVP for A股一周强势股捕捉: indicators, scoring, trade plan generation, and a 5-trading-day backtest engine.

**Architecture:** Keep the first version as a small Python package under `src/bigatrade`. Core logic is network-free and tested with synthetic DataFrames; AkShare access is only scaffolded after the strategy and backtest rules are stable.

**Tech Stack:** Python 3.11+, pandas, numpy, typer, pytest, akshare.

---

## File Structure

- Create `pyproject.toml`: package metadata, dependencies, pytest config.
- Create `src/bigatrade/__init__.py`: package marker.
- Create `src/bigatrade/__main__.py`: module entrypoint for `python -m bigatrade`.
- Create `src/bigatrade/cli.py`: Typer CLI shell.
- Create `src/bigatrade/strategy/indicators.py`: moving averages, percentage returns, volume ratios, recent highs.
- Create `src/bigatrade/strategy/strong_stock.py`: rule-based candidate filter and strength score.
- Create `src/bigatrade/strategy/trade_plan.py`: buy range, target, stop loss, and reason generation.
- Create `src/bigatrade/backtest/engine.py`: chronological 5-day backtest.
- Create `tests/strategy/test_indicators.py`: tests for deterministic indicators.
- Create `tests/strategy/test_trade_plan.py`: tests for trading plan math.
- Create `tests/strategy/test_strong_stock.py`: tests for strong/weak sample scoring.
- Create `tests/backtest/test_engine.py`: tests for take-profit, stop-loss, timeout, and no-entry outcomes.

## Task 1: Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/bigatrade/__init__.py`
- Create: `src/bigatrade/__main__.py`
- Create: `src/bigatrade/cli.py`

- [ ] **Step 1: Write the failing CLI smoke test**

Create `tests/test_cli.py`:

```python
from typer.testing import CliRunner

from bigatrade.cli import app


def test_cli_shows_help():
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "recommend" in result.output
    assert "backtest" in result.output
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py -q`

Expected: FAIL because package `bigatrade` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create package files and a Typer app with placeholder commands.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py -q`

Expected: PASS.

## Task 2: Indicator Functions

**Files:**
- Create: `src/bigatrade/strategy/indicators.py`
- Test: `tests/strategy/test_indicators.py`

- [ ] **Step 1: Write failing tests**

```python
import pandas as pd

from bigatrade.strategy.indicators import add_indicators


def test_add_indicators_calculates_moving_averages_and_returns():
    df = pd.DataFrame(
        {
            "close": [10, 11, 12, 13, 14],
            "volume": [100, 110, 120, 130, 260],
            "high": [10.5, 11.5, 12.5, 13.5, 14.5],
            "low": [9.5, 10.5, 11.5, 12.5, 13.5],
        }
    )

    result = add_indicators(df)

    assert result.loc[4, "ma5"] == 12
    assert round(result.loc[4, "return_5d"], 4) == 0.4
    assert round(result.loc[4, "volume_ratio_3_to_10"], 4) == round(510 / 3 / 144, 4)
    assert result.loc[4, "high_20d"] == 14.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/strategy/test_indicators.py -q`

Expected: FAIL because `add_indicators` does not exist.

- [ ] **Step 3: Write minimal implementation**

Implement `add_indicators(df: pd.DataFrame) -> pd.DataFrame` with `ma5`, `ma10`, `ma20`, `return_5d`, `return_10d`, `volume_ma10`, `volume_ratio_3_to_10`, `high_20d`, and `amount_ma20`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/strategy/test_indicators.py -q`

Expected: PASS.

## Task 3: Trade Plan Generation

**Files:**
- Create: `src/bigatrade/strategy/trade_plan.py`
- Test: `tests/strategy/test_trade_plan.py`

- [ ] **Step 1: Write failing tests**

```python
from bigatrade.strategy.trade_plan import build_trade_plan


def test_build_trade_plan_uses_fixed_risk_reward_rules():
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/strategy/test_trade_plan.py -q`

Expected: FAIL because `build_trade_plan` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create a `TradePlan` dataclass and `build_trade_plan`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/strategy/test_trade_plan.py -q`

Expected: PASS.

## Task 4: Strong Stock Strategy

**Files:**
- Create: `src/bigatrade/strategy/strong_stock.py`
- Test: `tests/strategy/test_strong_stock.py`

- [ ] **Step 1: Write failing tests**

```python
import pandas as pd

from bigatrade.strategy.strong_stock import score_latest_stock


def test_score_latest_stock_accepts_clear_strong_sample():
    df = pd.DataFrame(
        {
            "close": list(range(10, 40)),
            "high": [price + 0.5 for price in range(10, 40)],
            "low": [price - 0.5 for price in range(10, 40)],
            "volume": [100] * 27 + [180, 190, 220],
            "amount": [10_000_000] * 30,
        }
    )

    result = score_latest_stock("600000", "测试股票", df)

    assert result is not None
    assert result.score >= 70
    assert any("均线" in reason for reason in result.reasons)


def test_score_latest_stock_rejects_st_stock():
    df = pd.DataFrame(
        {
            "close": list(range(10, 40)),
            "high": [price + 0.5 for price in range(10, 40)],
            "low": [price - 0.5 for price in range(10, 40)],
            "volume": [100] * 30,
            "amount": [10_000_000] * 30,
        }
    )

    assert score_latest_stock("600001", "ST测试", df) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/strategy/test_strong_stock.py -q`

Expected: FAIL because `score_latest_stock` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create a `StockScore` dataclass. Apply filters for ST, data length, liquidity, moving-average trend, positive 5-day return, volume expansion, and 20-day high proximity.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/strategy/test_strong_stock.py -q`

Expected: PASS.

## Task 5: Backtest Engine

**Files:**
- Create: `src/bigatrade/backtest/engine.py`
- Test: `tests/backtest/test_engine.py`

- [ ] **Step 1: Write failing tests**

```python
import pandas as pd

from bigatrade.backtest.engine import backtest_trade_plan
from bigatrade.strategy.trade_plan import build_trade_plan


def make_plan():
    return build_trade_plan(
        recommend_date="2026-06-05",
        code="600000",
        name="浦发银行",
        close=10.0,
        strength_score=80.0,
        reasons=["强势突破"],
        risks=["跌破止损则退出"],
    )


def test_backtest_takes_profit_after_entry():
    future = pd.DataFrame(
        {
            "date": ["2026-06-08", "2026-06-09"],
            "open": [10.0, 10.8],
            "high": [10.3, 11.2],
            "low": [9.95, 10.7],
            "close": [10.2, 11.1],
        }
    )

    result = backtest_trade_plan(make_plan(), future)

    assert result.exit_reason == "止盈"
    assert result.hit_target is True
    assert round(result.return_pct, 2) == 10.0


def test_backtest_uses_conservative_stop_loss_when_same_day_hits_both():
    future = pd.DataFrame(
        {
            "date": ["2026-06-08"],
            "open": [10.0],
            "high": [11.2],
            "low": [9.4],
            "close": [10.5],
        }
    )

    result = backtest_trade_plan(make_plan(), future)

    assert result.exit_reason == "止损"
    assert result.hit_target is False
    assert round(result.return_pct, 2) == -5.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/backtest/test_engine.py -q`

Expected: FAIL because `backtest_trade_plan` does not exist.

- [ ] **Step 3: Write minimal implementation**

Create a `BacktestResult` dataclass and chronological scan from actual entry day.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/backtest/test_engine.py -q`

Expected: PASS.

## Task 6: Full Test Suite

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Run full tests**

Run: `pytest -q`

Expected: all tests pass.

- [ ] **Step 2: Update README**

Document the MVP purpose and commands:

```markdown
# bigATrade

A股一周强势股捕捉与回测工具。

第一版使用 AkShare + pandas + 自写 5 日回测，目标是验证一周内冲击 10% 的强势股策略。
```

- [ ] **Step 3: Run full tests again**

Run: `pytest -q`

Expected: all tests pass.
