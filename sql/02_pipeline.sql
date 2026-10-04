-- ChainTruth | 02_pipeline.sql
-- Raw -> Curated using dynamic tables. One canonical definition of delivery metrics lives HERE.
USE ROLE ACCOUNTADMIN; USE DATABASE SC_ONTOLOGY; USE WAREHOUSE SC_WH;

-- Dimensions (views)
CREATE OR REPLACE VIEW CURATED.DIM_PLANT    AS SELECT plant_id, plant_name, country AS plant_country, region AS plant_region FROM RAW.PLANTS;
CREATE OR REPLACE VIEW CURATED.DIM_CUSTOMER AS SELECT customer_id, customer_name, segment AS customer_segment, customer_region, service_tier FROM RAW.CUSTOMERS;
CREATE OR REPLACE VIEW CURATED.DIM_PART     AS SELECT part_id, part_name, part_category FROM RAW.PARTS;

CREATE OR REPLACE VIEW CURATED.DIM_SUPPLIER AS
SELECT s.supplier_id, s.supplier_name, s.supplier_country, s.supplier_tier, s.supplier_status,
       c.contract_expiry_date,
       DATEDIFF(day, CURRENT_DATE(), c.contract_expiry_date) AS days_to_contract_expiry
FROM RAW.SUPPLIERS s
LEFT JOIN (SELECT supplier_id, MIN(expiry_date) AS contract_expiry_date FROM RAW.CONTRACT_DOCS GROUP BY supplier_id) c
  ON c.supplier_id = s.supplier_id;

-- Canonical order-line fact (incremental refresh)
-- CANONICAL DEFINITIONS
--   delivered_date : carrier proof-of-delivery date (logistics), NOT ERP goods issue
--   on_time        : delivered_date <= promised_date (the date confirmed to the customer)
--   in_full        : qty_shipped >= qty_ordered
--   landed_cost    : line value + freight + duty
CREATE OR REPLACE DYNAMIC TABLE CURATED.DT_ORDER_LINE
  TARGET_LAG = '1 hour' WAREHOUSE = SC_WH
AS
SELECT e.order_id || '-' || e.line_no                         AS order_line_key,
       e.order_id, e.line_no, e.customer_id, e.part_id, e.plant_id, e.supplier_id,
       e.order_date, e.promised_date,
       l.carrier_delivered_ts::DATE                            AS delivered_date,
       e.qty_ordered, l.qty_shipped,
       e.unit_cost::FLOAT                                      AS unit_cost,
       (e.qty_ordered * e.unit_cost)::FLOAT                    AS line_value,
       (e.qty_ordered * e.unit_cost + l.freight_cost + l.duty_cost)::FLOAT AS landed_cost,
       l.freight_cost::FLOAT AS freight_cost, l.duty_cost::FLOAT AS duty_cost,
       IFF(l.carrier_delivered_ts::DATE <= e.promised_date, 1, 0) AS is_on_time,
       IFF(l.qty_shipped >= e.qty_ordered, 1, 0)                  AS is_in_full,
       GREATEST(DATEDIFF(day, e.promised_date, l.carrier_delivered_ts::DATE), 0) AS days_late,
       DATE_TRUNC('month', l.carrier_delivered_ts::DATE)          AS delivery_month,
       l.carrier
FROM RAW.ERP_ORDER_LINES e
JOIN RAW.LOGISTICS_SHIPMENTS l ON l.order_id = e.order_id AND l.line_no = e.line_no;

CREATE OR REPLACE DYNAMIC TABLE CURATED.DT_INVENTORY_LATEST
  TARGET_LAG = '1 hour' WAREHOUSE = SC_WH
AS
SELECT part_id || '-' || plant_id AS inventory_key, snapshot_date, part_id, plant_id, on_hand_qty, avg_daily_usage
FROM RAW.INVENTORY_SNAPSHOTS
QUALIFY snapshot_date = MAX(snapshot_date) OVER ();

-- Thin views are what the semantic view and masking policies attach to.
-- FACT_ORDER_LINE filters to the DELIVERED population only: lines whose carrier
-- proof-of-delivery date is on or before today.  In-transit lines (future dates)
-- are excluded so every delivery-performance metric uses the same population.
-- The filter lives HERE (not in the DT) because CURRENT_DATE() is non-deterministic
-- and would force DT_ORDER_LINE to do a FULL refresh on every cycle.
CREATE OR REPLACE VIEW CURATED.FACT_ORDER_LINE AS
SELECT * FROM CURATED.DT_ORDER_LINE WHERE delivered_date <= CURRENT_DATE();

CREATE OR REPLACE VIEW CURATED.FACT_INVENTORY  AS SELECT * FROM CURATED.DT_INVENTORY_LATEST;

-- The "before" picture: what each team computes today from its own system.
-- ALL four rows are restricted to the same DELIVERED population (carrier proof-of-delivery
-- date on or before today) so comparisons are apples-to-apples.
CREATE OR REPLACE VIEW CURATED.VW_LEGACY_OTD_BY_TEAM AS
SELECT 'Planning (ERP goods issue <= requested date)' AS team_definition,
       ROUND(100*AVG(IFF(e.goods_issue_date <= e.requested_date,1,0)),1) AS otd_pct
FROM RAW.ERP_ORDER_LINES e
JOIN RAW.LOGISTICS_SHIPMENTS l ON l.order_id = e.order_id AND l.line_no = e.line_no
WHERE l.carrier_delivered_ts::DATE <= CURRENT_DATE()
UNION ALL
SELECT 'Procurement (supplier dispatch <= supplier committed date)',
       ROUND(100*AVG(IFF(e.supplier_dispatch_date <= e.supplier_committed_date,1,0)),1)
FROM RAW.ERP_ORDER_LINES e
JOIN RAW.LOGISTICS_SHIPMENTS l ON l.order_id = e.order_id AND l.line_no = e.line_no
WHERE l.carrier_delivered_ts::DATE <= CURRENT_DATE()
UNION ALL
SELECT 'Logistics (carrier delivered <= carrier ETA)',
       ROUND(100*AVG(IFF(l.carrier_delivered_ts::DATE <= l.carrier_eta_date,1,0)),1)
FROM RAW.LOGISTICS_SHIPMENTS l
WHERE l.carrier_delivered_ts::DATE <= CURRENT_DATE()
UNION ALL
SELECT 'CANONICAL (delivered <= promised to customer)',
       ROUND(100*AVG(is_on_time),1)
FROM CURATED.FACT_ORDER_LINE;

-- Stream + task: new shipments trigger late-delivery alerts incrementally
CREATE TABLE IF NOT EXISTS GOVERNANCE.ALERTS (
  alert_ts TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(), alert_type STRING, supplier_id STRING,
  order_id STRING, detail STRING, ticket_status STRING DEFAULT 'NEW');

CREATE OR REPLACE STREAM RAW.STRM_NEW_SHIPMENTS ON TABLE RAW.LOGISTICS_SHIPMENTS APPEND_ONLY = TRUE;

CREATE OR REPLACE TASK GOVERNANCE.T_LATE_SHIPMENT_ALERTS
  WAREHOUSE = SC_WH SCHEDULE = '15 MINUTE'
  WHEN SYSTEM$STREAM_HAS_DATA('SC_ONTOLOGY.RAW.STRM_NEW_SHIPMENTS')
AS
INSERT INTO GOVERNANCE.ALERTS (alert_type, supplier_id, order_id, detail)
SELECT 'LATE_DELIVERY', e.supplier_id, s.order_id,
       'Delivered '||DATEDIFF(day, e.promised_date, s.carrier_delivered_ts::DATE)||' day(s) after promised date'
FROM RAW.STRM_NEW_SHIPMENTS s
JOIN RAW.ERP_ORDER_LINES e ON e.order_id = s.order_id AND e.line_no = s.line_no
WHERE s.carrier_delivered_ts::DATE > e.promised_date;

ALTER TASK GOVERNANCE.T_LATE_SHIPMENT_ALERTS RESUME;

-- Proof of the problem (use this on slide 1 of the demo)
SELECT * FROM CURATED.VW_LEGACY_OTD_BY_TEAM;
