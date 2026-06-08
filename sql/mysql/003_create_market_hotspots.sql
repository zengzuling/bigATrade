USE `bigatrade`;

CREATE TABLE IF NOT EXISTS `market_hotspot_versions` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '市场热点版本ID',
  `trade_date` DATE NOT NULL COMMENT '热点生成交易日',
  `source` VARCHAR(64) NOT NULL DEFAULT 'akshare_eastmoney' COMMENT '热点数据源',
  `status` VARCHAR(32) NOT NULL DEFAULT 'success' COMMENT '版本状态',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_hotspot_versions_trade_date` (`trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='推荐前市场热点版本表';

CREATE TABLE IF NOT EXISTS `market_hotspot_boards` (
  `id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '市场热点板块ID',
  `version_id` BIGINT UNSIGNED NOT NULL COMMENT '热点版本ID',
  `rank_no` INT UNSIGNED NOT NULL COMMENT '版本内排序',
  `board_type` VARCHAR(32) NOT NULL COMMENT '板块类型：industry/concept',
  `board_name` VARCHAR(128) NOT NULL COMMENT '板块名称',
  `change_pct` DECIMAL(8,4) NOT NULL DEFAULT 0 COMMENT '板块涨跌幅',
  `turnover_rate` DECIMAL(8,4) NOT NULL DEFAULT 0 COMMENT '板块换手率',
  `rise_count` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '上涨家数',
  `fall_count` INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '下跌家数',
  `leading_stock` VARCHAR(64) NULL COMMENT '领涨股票',
  `leading_stock_change_pct` DECIMAL(8,4) NOT NULL DEFAULT 0 COMMENT '领涨股票涨跌幅',
  `bonus_score` DECIMAL(8,4) NOT NULL DEFAULT 0 COMMENT '推荐加分',
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_hotspot_boards_version_type_name` (`version_id`, `board_type`, `board_name`),
  KEY `idx_hotspot_boards_name` (`board_name`),
  CONSTRAINT `fk_hotspot_boards_version`
    FOREIGN KEY (`version_id`) REFERENCES `market_hotspot_versions` (`id`)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='推荐前市场热点板块明细表';
