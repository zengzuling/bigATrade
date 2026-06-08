USE `bigatrade`;

CREATE TABLE IF NOT EXISTS `stock_recommendation_daily_quotes` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '推荐股票每日表现ID',
  `recommendation_id` BIGINT UNSIGNED NOT NULL COMMENT '推荐明细ID',
  `run_id` BIGINT UNSIGNED NOT NULL COMMENT '推荐批次ID',
  `recommend_date` DATE NOT NULL COMMENT '推荐交易日',
  `trade_date` DATE NOT NULL COMMENT '表现记录交易日',
  `stock_code` VARCHAR(16) NOT NULL COMMENT '股票代码',
  `stock_name` VARCHAR(64) NOT NULL COMMENT '股票名称',
  `open_price` DECIMAL(12,4) NOT NULL COMMENT '开盘价',
  `close_price` DECIMAL(12,4) NOT NULL COMMENT '收盘价',
  `high_price` DECIMAL(12,4) NOT NULL COMMENT '最高价',
  `low_price` DECIMAL(12,4) NOT NULL COMMENT '最低价',
  `pre_close_price` DECIMAL(12,4) NULL COMMENT '前一交易日收盘价',
  `change_pct` DECIMAL(8,4) NULL COMMENT '当日涨跌幅百分比',
  `volume` DECIMAL(20,4) NULL COMMENT '成交量',
  `amount` DECIMAL(20,4) NULL COMMENT '成交额',
  `gain_from_buy_pct` DECIMAL(8,4) NOT NULL COMMENT '相对推荐买入中位价涨幅',
  `gain_from_close_pct` DECIMAL(8,4) NOT NULL COMMENT '相对推荐日收盘价涨幅',
  `gain_from_recommend_pct` DECIMAL(8,4) NOT NULL COMMENT '自推荐写库日起累计涨跌幅',
  `hit_target` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '当日最高价是否达到目标价',
  `hit_stop_loss` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '当日最低价是否跌破止损价',
  `raw_json` JSON NULL COMMENT '原始行情备份',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_daily_quotes_recommendation_date` (`recommendation_id`, `trade_date`),
  KEY `idx_daily_quotes_run` (`run_id`),
  KEY `idx_daily_quotes_trade_date` (`trade_date`),
  KEY `idx_daily_quotes_stock_code` (`stock_code`),
  CONSTRAINT `fk_daily_quotes_recommendation`
    FOREIGN KEY (`recommendation_id`) REFERENCES `stock_recommendations` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_daily_quotes_run`
    FOREIGN KEY (`run_id`) REFERENCES `recommend_runs` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='推荐股票每日收盘表现表';
