USE `bigatrade`;

ALTER TABLE `backtest_results`
DROP INDEX `uk_backtest_results_recommendation`;

ALTER TABLE `backtest_results`
ADD UNIQUE KEY `uk_backtest_results_recommendation_exit` (`recommendation_id`, `exit_date`);
