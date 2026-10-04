-- ChainTruth | 01_synthetic_data.sql
-- Fully synthetic, referentially consistent data. Dates are relative to CURRENT_DATE().
-- The three source systems (ERP, procurement/PO, logistics) deliberately define "on time" differently.
USE ROLE ACCOUNTADMIN; USE DATABASE SC_ONTOLOGY; USE WAREHOUSE SC_WH; USE SCHEMA RAW;

-- ---------- Dimensions ----------
CREATE OR REPLACE TABLE RAW.PLANTS AS
SELECT 'PLT-'||LPAD(n::STRING,2,'0') AS plant_id,
       GET(ARRAY_CONSTRUCT('Pune','Chennai','Detroit','Monterrey','Gdansk','Shenzhen','Rotterdam','Singapore'), n-1)::STRING AS plant_name,
       GET(ARRAY_CONSTRUCT('India','India','USA','Mexico','Poland','China','Netherlands','Singapore'), n-1)::STRING AS country,
       GET(ARRAY_CONSTRUCT('APAC','APAC','Americas','Americas','EMEA','APAC','EMEA','APAC'), n-1)::STRING AS region
FROM (SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS n FROM TABLE(GENERATOR(ROWCOUNT=>8)));

CREATE OR REPLACE TABLE RAW.SUPPLIERS AS
SELECT 'SUP-'||LPAD(n::STRING,3,'0') AS supplier_id,
       'Supplier '||GET(ARRAY_CONSTRUCT('Alpha','Bravo','Cobalt','Delta','Ember','Fjord','Granite','Helix','Ion','Juno'), MOD(n,10))::STRING||' '||n AS supplier_name,
       GET(ARRAY_CONSTRUCT('India','China','Germany','Mexico','Vietnam','USA','Taiwan','Poland'), MOD(n,8))::STRING AS supplier_country,
       MOD(n,3)+1 AS supplier_tier,
       GET(ARRAY_CONSTRUCT('Strategic','Preferred','Approved','Probation'), MOD(n,4))::STRING AS supplier_status
FROM (SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS n FROM TABLE(GENERATOR(ROWCOUNT=>60)));

CREATE OR REPLACE TABLE RAW.PARTS AS
SELECT 'PRT-'||LPAD(n::STRING,4,'0') AS part_id,
       GET(ARRAY_CONSTRUCT('Bearing','Valve','Sensor','Gasket','Controller','Fastener Kit','Housing','Cable Harness'), MOD(n,8))::STRING||' '||n AS part_name,
       GET(ARRAY_CONSTRUCT('Mechanical','Electronics','Fasteners','Raw Material','Packaging'), MOD(n,5))::STRING AS part_category,
       'SUP-'||LPAD((MOD(n,60)+1)::STRING,3,'0') AS primary_supplier_id,
       ROUND(UNIFORM(5,500,RANDOM(11))::FLOAT, 2) AS std_unit_cost
FROM (SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS n FROM TABLE(GENERATOR(ROWCOUNT=>200)));

CREATE OR REPLACE TABLE RAW.CUSTOMERS AS
SELECT 'CUS-'||LPAD(n::STRING,3,'0') AS customer_id,
       'Customer '||n AS customer_name,
       GET(ARRAY_CONSTRUCT('Automotive','Industrial','Energy','Healthcare Devices','Consumer'), MOD(n,5))::STRING AS segment,
       GET(ARRAY_CONSTRUCT('APAC','Americas','EMEA'), MOD(n,3))::STRING AS customer_region,
       GET(ARRAY_CONSTRUCT('Platinum','Gold','Silver'), MOD(n,3))::STRING AS service_tier
FROM (SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS n FROM TABLE(GENERATOR(ROWCOUNT=>40)));

-- ---------- Simulation base (dropped at the end) ----------
CREATE OR REPLACE TEMPORARY TABLE RAW._SIM AS
WITH base AS (
  SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS n,
         UNIFORM(1,5000,RANDOM(21)) AS order_no,
         UNIFORM(1,200,RANDOM(22))  AS part_n,
         UNIFORM(1,8,RANDOM(23))    AS plant_n,
         UNIFORM(1,40,RANDOM(24))   AS cust_n,
         UNIFORM(1,180,RANDOM(25))  AS age_days,
         UNIFORM(10,500,RANDOM(26)) AS qty_ordered,
         UNIFORM(0,99,RANDOM(27))   AS r_sup_late,
         UNIFORM(1,6,RANDOM(28))    AS sup_delay,
         UNIFORM(0,99,RANDOM(29))   AS r_carrier_late,
         UNIFORM(1,5,RANDOM(30))    AS carrier_delay,
         UNIFORM(0,99,RANDOM(31))   AS r_short,
         UNIFORM(2,7,RANDOM(32))    AS transit_days
  FROM TABLE(GENERATOR(ROWCOUNT=>20000))
), keyed AS (
  SELECT b.*, 'PRT-'||LPAD(part_n::STRING,4,'0') AS part_id,
         'PLT-'||LPAD(plant_n::STRING,2,'0') AS plant_id,
         'CUS-'||LPAD(cust_n::STRING,3,'0') AS customer_id
  FROM base b
), joined AS (
  SELECT k.*, p.primary_supplier_id AS supplier_id, p.std_unit_cost,
         -- each supplier has a stable "bad actor" bias (ground truth for the simulation only)
         MOD(ABS(HASH(p.primary_supplier_id)),100) AS sup_bias
  FROM keyed k JOIN RAW.PARTS p ON p.part_id = k.part_id
), dated AS (
  SELECT j.*,
         DATEADD(day, -age_days, CURRENT_DATE()) AS order_date,
         DATEADD(day, UNIFORM(7,21,RANDOM(33)), DATEADD(day,-age_days,CURRENT_DATE())) AS requested_date
  FROM joined j
), stepped AS (
  SELECT d.*,
         DATEADD(day, UNIFORM(0,3,RANDOM(34)), requested_date)            AS promised_date,
         DATEADD(day, UNIFORM(3,8,RANDOM(35)), order_date)                AS supplier_committed_date
  FROM dated d
), shipped AS (
  SELECT s.*,
         DATEADD(day, CASE WHEN r_sup_late < LEAST(70, 8 + sup_bias*0.5) THEN sup_delay ELSE -UNIFORM(0,2,RANDOM(36)) END, supplier_committed_date) AS supplier_dispatch_date
  FROM stepped s
), issued AS (
  SELECT h.*, DATEADD(day, UNIFORM(1,3,RANDOM(37)), supplier_dispatch_date) AS goods_issue_date FROM shipped h
)
SELECT i.*,
       DATEADD(hour, UNIFORM(0,20,RANDOM(38)),
         DATEADD(day, transit_days + CASE WHEN r_carrier_late < 18 THEN carrier_delay ELSE 0 END, goods_issue_date)::TIMESTAMP_NTZ) AS carrier_delivered_ts,
       DATEADD(day, 4, goods_issue_date) AS carrier_eta_date,
       CASE WHEN r_short < 12 THEN FLOOR(qty_ordered * UNIFORM(60,95,RANDOM(39))/100) ELSE qty_ordered END AS qty_shipped,
       GET(ARRAY_CONSTRUCT('BlueLine','OceanX','SkyFreight','RoadRunner','TransPac'), MOD(n,5))::STRING AS carrier
FROM issued i;

-- ---------- Source system 1: ERP ----------
CREATE OR REPLACE TABLE RAW.ERP_ORDER_LINES AS
SELECT 'SO-'||LPAD(order_no::STRING,5,'0') AS order_id,
       n AS line_no, customer_id, part_id, plant_id, supplier_id,
       qty_ordered, std_unit_cost AS unit_cost,
       order_date, requested_date, promised_date,
       supplier_committed_date, supplier_dispatch_date, goods_issue_date
FROM RAW._SIM;

-- ---------- Source system 2: logistics / TMS ----------
CREATE OR REPLACE TABLE RAW.LOGISTICS_SHIPMENTS AS
SELECT 'SHP-'||LPAD(n::STRING,6,'0') AS shipment_id,
       'SO-'||LPAD(order_no::STRING,5,'0') AS order_id,
       n AS line_no, carrier, carrier_eta_date, carrier_delivered_ts, qty_shipped,
       ROUND(qty_shipped * UNIFORM(0.2,2.5,RANDOM(40)), 2) AS freight_cost,
       ROUND(qty_shipped * std_unit_cost * UNIFORM(0,8,RANDOM(41))/100, 2) AS duty_cost
FROM RAW._SIM;

-- ---------- Source system 3: warehouse inventory ----------
CREATE OR REPLACE TABLE RAW.INVENTORY_SNAPSHOTS AS
SELECT DATEADD(week, -w.k, CURRENT_DATE()) AS snapshot_date,
       p.part_id, pl.plant_id,
       UNIFORM(0,4000,RANDOM(42)) AS on_hand_qty,
       ROUND(UNIFORM(5,120,RANDOM(43))::FLOAT, 1) AS avg_daily_usage
FROM RAW.PARTS p CROSS JOIN RAW.PLANTS pl
CROSS JOIN (SELECT SEQ4() AS k FROM TABLE(GENERATOR(ROWCOUNT=>4))) w;

-- ---------- Unstructured: supplier contracts / SLAs ----------
CREATE OR REPLACE TABLE RAW.CONTRACT_DOCS AS
WITH s AS (SELECT s.*, ROW_NUMBER() OVER (ORDER BY supplier_id) AS n FROM RAW.SUPPLIERS s), docs AS (
  SELECT s.supplier_id, s.supplier_name, t.doc_type, s.n,
         -- ~25% of contracts expire within the next 90 days
         CASE WHEN MOD(s.n,4)=0 THEN DATEADD(day, UNIFORM(10,90,RANDOM(44)), CURRENT_DATE())
              ELSE DATEADD(day, UNIFORM(120,700,RANDOM(45)), CURRENT_DATE()) END AS expiry_date,
         CASE WHEN s.supplier_tier=1 THEN 95 WHEN s.supplier_tier=2 THEN 92 ELSE 88 END AS otd_sla_pct
  FROM s CROSS JOIN (SELECT 'Supply Agreement' AS doc_type UNION ALL SELECT 'SLA Addendum') t
)
SELECT 'DOC-'||supplier_id||'-'||IFF(doc_type='Supply Agreement','SA','SLA') AS doc_id,
       supplier_id, supplier_name, doc_type, expiry_date,
       CASE WHEN doc_type='Supply Agreement' THEN
         'SUPPLY AGREEMENT between Acme Manufacturing and '||supplier_name||' ('||supplier_id||'). '||
         'Term: this agreement expires on '||TO_CHAR(expiry_date,'YYYY-MM-DD')||' and renews automatically for 12 months unless either party gives 60 days written notice. '||
         'Pricing: unit prices are fixed for the term; price revisions require written approval from Procurement. '||
         'Termination: Acme may terminate for cause if the supplier misses the delivery SLA in three consecutive months.'
       ELSE
         'SLA ADDENDUM for '||supplier_name||' ('||supplier_id||'). '||
         'On-time delivery commitment: '||otd_sla_pct||'% measured monthly against the confirmed promised date. '||
         'Remedy: a late-delivery credit of 1.5% of line value applies per late line, capped at 10% of monthly spend. '||
         'Chronic underperformance (below SLA for two consecutive months) triggers a corrective action plan within 15 days. '||
         'This addendum expires on '||TO_CHAR(expiry_date,'YYYY-MM-DD')||'.' END AS doc_text
FROM docs;

DROP TABLE IF EXISTS RAW._SIM;

-- Quick sanity checks
SELECT 'ERP lines' AS what, COUNT(*) AS n FROM RAW.ERP_ORDER_LINES
UNION ALL SELECT 'Shipments', COUNT(*) FROM RAW.LOGISTICS_SHIPMENTS
UNION ALL SELECT 'Contracts', COUNT(*) FROM RAW.CONTRACT_DOCS
UNION ALL SELECT 'Orphan shipments (must be 0)', COUNT(*) FROM RAW.LOGISTICS_SHIPMENTS s
  WHERE NOT EXISTS (SELECT 1 FROM RAW.ERP_ORDER_LINES e WHERE e.order_id=s.order_id AND e.line_no=s.line_no);
