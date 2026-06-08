ALTER TABLE `stock_recommendation_daily_quotes`
ADD COLUMN `gain_from_recommend_pct` DECIMAL(8,4) NOT NULL DEFAULT 0 COMMENT '自推荐写库日起累计涨跌幅'
AFTER `gain_from_close_pct`;

UPDATE `stock_recommendation_daily_quotes`
SET `gain_from_recommend_pct` = `gain_from_close_pct`
WHERE `gain_from_recommend_pct` = 0;
