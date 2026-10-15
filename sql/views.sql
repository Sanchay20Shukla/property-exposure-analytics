CREATE VIEW IF NOT EXISTS v_hazard_exposure AS
SELECT band, COUNT(*) AS properties, SUM(tiv_usd) AS tiv_usd,
       SUM(tiv_usd) / (SELECT SUM(tiv_usd) FROM properties) AS portfolio_share
FROM properties GROUP BY band;
CREATE VIEW IF NOT EXISTS v_top_concentrations AS
SELECT * FROM concentration ORDER BY tiv_usd DESC LIMIT 20;
CREATE VIEW IF NOT EXISTS v_quality_exceptions AS
SELECT rule, COUNT(*) AS affected_rows FROM exceptions GROUP BY rule;
