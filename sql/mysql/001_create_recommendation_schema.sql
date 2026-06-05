CREATE DATABASE IF NOT EXISTS `bigatrade`
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE `bigatrade`;

CREATE TABLE IF NOT EXISTS `recommend_runs` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '推荐任务批次ID',
  `run_date` DATE NOT NULL COMMENT '推荐交易日',
  `run_type` VARCHAR(32) NOT NULL DEFAULT 'daily_close' COMMENT '运行类型：daily_close=收盘后推荐',
  `status` VARCHAR(32) NOT NULL DEFAULT 'created' COMMENT '任务状态：created/running/success/failed',
  `strategy_version` VARCHAR(64) NOT NULL DEFAULT 'strong_stock_v1' COMMENT '策略版本',
  `data_source` VARCHAR(64) NOT NULL DEFAULT 'akshare' COMMENT '数据源',
  `scan_limit` INT UNSIGNED NULL COMMENT '限制扫描股票数，NULL表示不限制',
  `scanned_count` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '本次扫描股票数',
  `skipped_risky_count` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '跳过ST/退市等风险股票数',
  `daily_bar_error_count` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '日线行情拉取失败数',
  `empty_bar_count` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '空行情股票数',
  `selected_count` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '最终入选推荐数',
  `output_path` VARCHAR(512) NULL COMMENT '本次推荐CSV/Excel输出路径',
  `started_at` DATETIME NULL COMMENT '任务开始时间',
  `finished_at` DATETIME NULL COMMENT '任务结束时间',
  `remark` VARCHAR(512) NULL COMMENT '备注',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_recommend_runs_date` (`run_date`),
  KEY `idx_recommend_runs_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日推荐任务批次表';

CREATE TABLE IF NOT EXISTS `market_snapshots` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '市场快照ID',
  `run_id` BIGINT UNSIGNED NOT NULL COMMENT '推荐任务批次ID',
  `trade_date` DATE NOT NULL COMMENT '交易日',
  `up_count` INT UNSIGNED NULL COMMENT '上涨家数',
  `down_count` INT UNSIGNED NULL COMMENT '下跌家数',
  `flat_count` INT UNSIGNED NULL COMMENT '平盘家数',
  `limit_up_count` INT UNSIGNED NULL COMMENT '涨停家数',
  `limit_down_count` INT UNSIGNED NULL COMMENT '跌停家数',
  `total_amount` DECIMAL(20,4) NULL COMMENT '全市场成交额',
  `major_index_json` JSON NULL COMMENT '主要指数涨跌幅JSON',
  `hot_sectors_json` JSON NULL COMMENT '热门板块JSON',
  `sentiment_score` DECIMAL(8,4) NULL COMMENT '市场情绪评分，0-100',
  `sentiment_level` VARCHAR(32) NULL COMMENT '市场情绪等级：弱/中性/偏强/强',
  `sentiment_summary` TEXT NULL COMMENT '市场情绪文字总结',
  `raw_json` JSON NULL COMMENT '原始市场快照JSON',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_market_snapshots_run` (`run_id`),
  KEY `idx_market_snapshots_trade_date` (`trade_date`),
  CONSTRAINT `fk_market_snapshots_run`
    FOREIGN KEY (`run_id`) REFERENCES `recommend_runs` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日市场情绪快照表';

CREATE TABLE IF NOT EXISTS `stock_recommendations` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '推荐明细ID',
  `run_id` BIGINT UNSIGNED NOT NULL COMMENT '推荐任务批次ID',
  `recommend_date` DATE NOT NULL COMMENT '推荐交易日',
  `rank_no` INT UNSIGNED NULL COMMENT '本次推荐排名',
  `stock_code` VARCHAR(16) NOT NULL COMMENT '股票代码',
  `stock_name` VARCHAR(64) NOT NULL COMMENT '股票名称',
  `sector_name` VARCHAR(128) NULL COMMENT '所属板块/行业',
  `market_heat` VARCHAR(512) NULL COMMENT '板块或市场热度说明',
  `close_price` DECIMAL(12,4) NOT NULL COMMENT '推荐日收盘价',
  `buy_low` DECIMAL(12,4) NOT NULL COMMENT '建议买入价下限',
  `buy_high` DECIMAL(12,4) NOT NULL COMMENT '建议买入价上限',
  `buy_price` DECIMAL(12,4) NOT NULL COMMENT '回测用买入中位价',
  `target_price` DECIMAL(12,4) NOT NULL COMMENT '目标卖出价',
  `stop_loss_price` DECIMAL(12,4) NOT NULL COMMENT '止损价',
  `target_gain_pct` DECIMAL(8,4) NOT NULL COMMENT '目标涨幅百分比',
  `max_holding_days` INT UNSIGNED NOT NULL DEFAULT 5 COMMENT '最大持有交易日',
  `strength_score` DECIMAL(8,4) NOT NULL COMMENT '强势评分',
  `recommend_reason` TEXT NULL COMMENT '推荐原因',
  `risk_tip` TEXT NULL COMMENT '风险提示',
  `ai_reason` TEXT NULL COMMENT 'AI补充解释',
  `ai_risk` TEXT NULL COMMENT 'AI补充风险',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_stock_recommendations_run_stock` (`run_id`, `stock_code`),
  KEY `idx_stock_recommendations_date` (`recommend_date`),
  KEY `idx_stock_recommendations_code` (`stock_code`),
  KEY `idx_stock_recommendations_sector` (`sector_name`),
  CONSTRAINT `fk_stock_recommendations_run`
    FOREIGN KEY (`run_id`) REFERENCES `recommend_runs` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='每日推荐股票明细表';

CREATE TABLE IF NOT EXISTS `backtest_results` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '回测结果ID',
  `recommendation_id` BIGINT UNSIGNED NOT NULL COMMENT '推荐明细ID',
  `run_id` BIGINT UNSIGNED NOT NULL COMMENT '推荐任务批次ID',
  `recommend_date` DATE NOT NULL COMMENT '推荐交易日',
  `stock_code` VARCHAR(16) NOT NULL COMMENT '股票代码',
  `entry_date` DATE NULL COMMENT '实际买入日期',
  `exit_date` DATE NULL COMMENT '实际卖出日期',
  `entry_price` DECIMAL(12,4) NULL COMMENT '实际/回测买入价',
  `exit_price` DECIMAL(12,4) NULL COMMENT '实际/回测卖出价',
  `highest_gain_pct` DECIMAL(8,4) NOT NULL DEFAULT 0 COMMENT '持有观察期最高浮盈百分比',
  `hit_target` TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否达到目标涨幅',
  `return_pct` DECIMAL(8,4) NOT NULL DEFAULT 0 COMMENT '实际收益率百分比',
  `exit_reason` VARCHAR(32) NOT NULL COMMENT '退出原因：止盈/止损/到期/未触发买入',
  `holding_days` INT UNSIGNED NULL COMMENT '实际持有交易日',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_backtest_results_recommendation` (`recommendation_id`),
  KEY `idx_backtest_results_run` (`run_id`),
  KEY `idx_backtest_results_date` (`recommend_date`),
  KEY `idx_backtest_results_code` (`stock_code`),
  CONSTRAINT `fk_backtest_results_recommendation`
    FOREIGN KEY (`recommendation_id`) REFERENCES `stock_recommendations` (`id`)
    ON DELETE CASCADE,
  CONSTRAINT `fk_backtest_results_run`
    FOREIGN KEY (`run_id`) REFERENCES `recommend_runs` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='推荐股票未来表现回测结果表';

CREATE TABLE IF NOT EXISTS `job_errors` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '错误日志ID',
  `run_id` BIGINT UNSIGNED NULL COMMENT '推荐任务批次ID',
  `trade_date` DATE NULL COMMENT '交易日',
  `stock_code` VARCHAR(16) NULL COMMENT '相关股票代码',
  `stage` VARCHAR(64) NOT NULL COMMENT '错误阶段：stock_list/daily_bars/sector/market_snapshot/ai/backtest',
  `error_type` VARCHAR(128) NULL COMMENT '错误类型',
  `error_message` TEXT NULL COMMENT '错误摘要',
  `error_detail` MEDIUMTEXT NULL COMMENT '错误详情/堆栈',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_job_errors_run` (`run_id`),
  KEY `idx_job_errors_trade_date` (`trade_date`),
  KEY `idx_job_errors_stock_code` (`stock_code`),
  KEY `idx_job_errors_stage` (`stage`),
  CONSTRAINT `fk_job_errors_run`
    FOREIGN KEY (`run_id`) REFERENCES `recommend_runs` (`id`)
    ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='推荐任务错误日志表';
