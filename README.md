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

## 验证

```powershell
python -m pytest -q
```
