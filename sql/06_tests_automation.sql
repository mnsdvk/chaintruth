-- ChainTruth | 06_tests_automation.sql
-- Consistency harness (runs inside Snowflake) + nightly drift task.
USE ROLE ACCOUNTADMIN; USE DATABASE SC_ONTOLOGY; USE WAREHOUSE SC_WH;

CREATE TABLE IF NOT EXISTS GOVERNANCE.CONSISTENCY_RESULTS (
  run_id STRING, run_ts TIMESTAMP_NTZ, test_name STRING, metric STRING,
  semantic_value FLOAT, golden_value FLOAT, passed BOOLEAN, detail STRING);

CREATE OR REPLACE PROCEDURE GOVERNANCE.RUN_CONSISTENCY_TESTS()
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
  rid STRING DEFAULT UUID_STRING();
  fail_count INTEGER DEFAULT 0;
  total INTEGER DEFAULT 0;
BEGIN
  -- Test 1: every canonical metric via the semantic view == independently computed golden value
  -- Golden values use FACT_ORDER_LINE (the delivered-population view), NOT DT_ORDER_LINE.
  INSERT INTO GOVERNANCE.CONSISTENCY_RESULTS
  SELECT :rid, CURRENT_TIMESTAMP(), 'semantic_vs_golden', t.metric, t.sv, t.gold,
         ABS(COALESCE(t.sv,0) - COALESCE(t.gold,0)) < 0.000001,
         'Semantic view value equals independently computed value'
  FROM (
    SELECT 'otd_pct' AS metric,
      (SELECT otd_pct FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN METRICS order_lines.otd_pct)) AS sv,
      (SELECT 100*AVG(is_on_time) FROM SC_ONTOLOGY.CURATED.FACT_ORDER_LINE) AS gold
    UNION ALL SELECT 'fill_rate_pct',
      (SELECT fill_rate_pct FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN METRICS order_lines.fill_rate_pct)),
      (SELECT 100*SUM(qty_shipped)/SUM(qty_ordered) FROM SC_ONTOLOGY.CURATED.FACT_ORDER_LINE)
    UNION ALL SELECT 'in_full_pct',
      (SELECT in_full_pct FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN METRICS order_lines.in_full_pct)),
      (SELECT 100*AVG(is_in_full) FROM SC_ONTOLOGY.CURATED.FACT_ORDER_LINE)
    UNION ALL SELECT 'avg_days_late',
      (SELECT avg_days_late FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN METRICS order_lines.avg_days_late)),
      (SELECT SUM(days_late)/SUM(1-is_on_time) FROM SC_ONTOLOGY.CURATED.FACT_ORDER_LINE)
    UNION ALL SELECT 'avg_landed_cost_per_unit',
      (SELECT avg_landed_cost_per_unit FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN METRICS order_lines.avg_landed_cost_per_unit)),
      (SELECT SUM(landed_cost)/SUM(qty_shipped) FROM SC_ONTOLOGY.CURATED.FACT_ORDER_LINE)
    UNION ALL SELECT 'days_of_inventory',
      (SELECT days_of_inventory FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN METRICS inventory.days_of_inventory)),
      (SELECT SUM(on_hand_qty)/SUM(avg_daily_usage) FROM SC_ONTOLOGY.CURATED.DT_INVENTORY_LATEST)
  ) t;

  -- Test 2: slice-and-roll-up. Whatever lens a persona uses (supplier / plant / customer),
  -- the weighted roll-up must equal the single canonical OTD.
  INSERT INTO GOVERNANCE.CONSISTENCY_RESULTS
  SELECT :rid, CURRENT_TIMESTAMP(), r.lens, 'otd_pct', r.v, g.v, ABS(r.v - g.v) < 0.01,
         'Weighted roll-up of OTD by ' || r.lens || ' equals the canonical OTD'
  FROM (
    SELECT 'rollup_by_supplier' AS lens, SUM(otd_pct*line_count)/SUM(line_count) AS v
      FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN DIMENSIONS suppliers.supplier_id METRICS order_lines.otd_pct, order_lines.line_count)
    UNION ALL SELECT 'rollup_by_plant', SUM(otd_pct*line_count)/SUM(line_count)
      FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN DIMENSIONS plants.plant_id METRICS order_lines.otd_pct, order_lines.line_count)
    UNION ALL SELECT 'rollup_by_customer', SUM(otd_pct*line_count)/SUM(line_count)
      FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN DIMENSIONS customers.customer_id METRICS order_lines.otd_pct, order_lines.line_count)
  ) r,
  (SELECT 100*AVG(is_on_time) AS v FROM SC_ONTOLOGY.CURATED.FACT_ORDER_LINE) g;

  SELECT COUNT(*), COUNT_IF(NOT passed) INTO :total, :fail_count
    FROM GOVERNANCE.CONSISTENCY_RESULTS WHERE run_id = :rid;

  IF (fail_count > 0) THEN
    INSERT INTO GOVERNANCE.ALERTS (alert_type, detail)
      SELECT 'METRIC_DRIFT', :fail_count || ' of ' || :total || ' consistency tests failed (run ' || :rid || ')';
  END IF;

  RETURN 'run ' || rid || ': ' || (total - fail_count) || '/' || total || ' passed';
END;
$$;

CALL GOVERNANCE.RUN_CONSISTENCY_TESTS();
SELECT test_name, metric, semantic_value, golden_value, passed
FROM GOVERNANCE.CONSISTENCY_RESULTS QUALIFY run_ts = MAX(run_ts) OVER () ORDER BY test_name, metric;

-- Nightly drift detection (also schedule the equivalent from CoCo to show "unattended runs")
CREATE OR REPLACE TASK GOVERNANCE.T_NIGHTLY_CONSISTENCY
  WAREHOUSE = SC_WH SCHEDULE = 'USING CRON 0 2 * * * UTC'
AS CALL GOVERNANCE.RUN_CONSISTENCY_TESTS();
ALTER TASK GOVERNANCE.T_NIGHTLY_CONSISTENCY RESUME;
