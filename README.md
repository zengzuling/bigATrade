# bigATrade

A股一周强势股捕捉与回测工具。

第一版使用 AkShare + pandas + 自写 5 日回测，目标是验证一周内冲击 10% 的强势股策略。

## 当前能力

- 计算均线、涨幅、量能比、20 日高点等基础指标。
- 按强势规则给最新交易日评分。
- 生成固定风控交易计划：买入区间、10% 目标价、5% 止损价。
- 使用 AkShare 免费数据生成指定日期的推荐 CSV。
- 按实际买入日后的时间顺序做 5 日回测。

## 命令

```powershell
python -m bigatrade recommend --date 2026-06-05 --top 30 --scan-limit 100 --output outputs/recommend_2026-06-05.csv
python -m bigatrade backtest --start 2025-01-01 --end 2026-06-05
```

按价格分层筛选示例：

```powershell
python -m bigatrade recommend --date 2026-06-05 --scan-limit 2000 --top 2000 --price-buckets "0-10:2,10-20:2,20-50:1" --output outputs/recommend_2026-06-05_bucket.csv
```

全市场快照预筛示例：

```powershell
python -m bigatrade recommend --date 2026-06-05 --scan-limit all --top 2000 --price-buckets "0-10:2,10-20:2,20-50:1" --prefilter-per-bucket "0-10:120,10-20:120,20-50:80" --output outputs/recommend_2026-06-05_all_prefilter.csv
```

这个命令会先用 AkShare 全市场快照过滤价格桶，再按成交额和涨跌幅从每个价格桶挑候选，只对候选池拉日线。默认会把日线缓存到 `data/cache/`，后续重复跑同一日期范围会减少 AkShare 请求。

带市场热点版本加分的周度推荐示例：

```powershell
python -m bigatrade recommend --date 2026-06-05 --scan-limit all --top 2000 --price-buckets "0-10:2,10-20:2,20-50:1" --prefilter-per-bucket "0-10:120,10-20:120,20-50:80" --hotspot-db-host 47.110.235.19 --hotspot-db-port 33066 --hotspot-db-user zzl --hotspot-db-password "Abc@123456" --hotspot-top-industry 20 --hotspot-top-concept 20 --output outputs/recommend_2026-06-05_hotspot.csv
```

该命令会在推荐前先生成一版市场热点，写入 `market_hotspot_versions` 和 `market_hotspot_boards`，再把命中行业热点的股票加入强势评分。命中热点时，推荐原因会出现“热点板块加分”。

收盘后自动流水线示例：

```powershell
python -m bigatrade daily-run --date today --scan-limit all --top 30 --price-buckets "0-10:2,10-20:2,20-50:1" --prefilter-per-bucket "0-10:120,10-20:120,20-50:80" --db-host 47.110.235.19 --db-port 33066 --db-user zzl --db-password "Abc@123456"
```

该命令会先跟踪旧推荐在当日的收盘表现，再刷新市场热点，生成当天推荐 CSV，并把推荐批次和推荐明细写入 MySQL。

每日结果结算和复盘示例：

```powershell
python -m bigatrade settle-results --date today --db-host 47.110.235.19 --db-port 33066 --db-user zzl --db-password "Abc@123456"
python -m bigatrade five-day-summary --date today --db-host 47.110.235.19 --db-port 33066 --db-user zzl --db-password "Abc@123456"
python -m bigatrade review --date today --db-host 47.110.235.19 --db-port 33066 --db-user zzl --db-password "Abc@123456"
```

`settle-results` 会把满足目标、触发止损或观察满 5 个交易日的推荐写入 `backtest_results`。`five-day-summary` 输出已结算推荐的命中率和收益统计。`review` 基于 `stock_recommendation_daily_quotes` 生成公众号复盘初稿。

## 验证

```powershell
python -m pytest -q
```
