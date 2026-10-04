-- ChainTruth | 03_ontology_governance.sql
-- Ontology metadata (entities, relationships, canonical metrics) + governance (masking, tags).
USE ROLE ACCOUNTADMIN; USE DATABASE SC_ONTOLOGY; USE WAREHOUSE SC_WH;

CREATE OR REPLACE TABLE ONTOLOGY.ONT_ENTITY (
  entity STRING, description STRING, source_object STRING, primary_key STRING, hierarchy STRING);
INSERT INTO ONTOLOGY.ONT_ENTITY VALUES
 ('Supplier','Company that supplies parts','CURATED.DIM_SUPPLIER','supplier_id','Tier 1 > Tier 2 > Tier 3'),
 ('Part','Purchasable / sellable item','CURATED.DIM_PART','part_id','Category > Part'),
 ('Plant','Facility that stores and ships parts','CURATED.DIM_PLANT','plant_id','Region > Country > Plant'),
 ('Customer','Buyer of parts','CURATED.DIM_CUSTOMER','customer_id','Region > Segment > Customer'),
 ('OrderLine','One ordered part, shipped from a plant to a customer, with its delivery outcome','CURATED.FACT_ORDER_LINE','order_line_key','Order > Line'),
 ('Inventory','Latest on-hand stock of a part at a plant','CURATED.FACT_INVENTORY','inventory_key','Part x Plant');

CREATE OR REPLACE TABLE ONTOLOGY.ONT_RELATIONSHIP (
  from_entity STRING, relationship STRING, to_entity STRING, cardinality STRING, join_key STRING);
INSERT INTO ONTOLOGY.ONT_RELATIONSHIP VALUES
 ('OrderLine','SOURCED_FROM','Supplier','many-to-one','supplier_id'),
 ('OrderLine','CONTAINS','Part','many-to-one','part_id'),
 ('OrderLine','SHIPPED_FROM','Plant','many-to-one','plant_id'),
 ('OrderLine','DELIVERED_TO','Customer','many-to-one','customer_id'),
 ('Inventory','STOCKS','Part','many-to-one','part_id'),
 ('Inventory','HELD_AT','Plant','many-to-one','plant_id'),
 ('Supplier','SUPPLIES','Part','one-to-many','primary_supplier_id');

CREATE OR REPLACE TABLE ONTOLOGY.ONT_METRIC (
  metric_name STRING, display_name STRING, canonical_definition STRING, formula_sql STRING,
  owner_persona STRING, unit STRING, sensitivity STRING, legacy_variants STRING);
INSERT INTO ONTOLOGY.ONT_METRIC VALUES
 ('otd_pct','On-time delivery %','Share of delivered order lines (carrier proof of delivery on or before today) that arrived on or before the date promised to the customer. In-transit lines excluded.',
  '100 * AVG(is_on_time)','Shared (Planning, Procurement, Logistics)','percent','Internal',
  'Planning: ERP goods issue vs requested date | Procurement: supplier dispatch vs supplier committed date | Logistics: delivered vs carrier ETA'),
 ('fill_rate_pct','Fill rate %','Quantity shipped divided by quantity ordered, delivered lines only; in-transit lines excluded.','100 * SUM(qty_shipped)/SUM(qty_ordered)','Planning','percent','Internal','ERP counts line fill; logistics counts shipment fill'),
 ('in_full_pct','In-full %','Share of delivered order lines where shipped quantity >= ordered quantity; in-transit lines excluded.','100 * AVG(is_in_full)','Planning','percent','Internal',NULL),
 ('days_of_inventory','Days of inventory','On-hand quantity divided by average daily usage (latest snapshot).','SUM(on_hand_qty)/SUM(avg_daily_usage)','Planning','days','Internal','Finance uses average inventory value over COGS'),
 ('avg_landed_cost_per_unit','Landed cost per unit','(Line value + freight + duty) divided by units shipped, delivered lines only; in-transit lines excluded.','SUM(landed_cost)/SUM(qty_shipped)','Procurement / Logistics','currency','Restricted (masked for Planning)','Procurement excludes duty'),
 ('avg_days_late','Average days late','Average days past promised date across late delivered lines only; in-transit lines excluded.','SUM(days_late)/SUM(1 - is_on_time)','Logistics','days','Internal',NULL);

-- ---------- Governance ----------
CREATE TAG IF NOT EXISTS GOVERNANCE.METRIC_OWNER;
CREATE TAG IF NOT EXISTS GOVERNANCE.DATA_SENSITIVITY;

-- Supplier pricing is visible to Procurement only; landed cost to Procurement + Logistics.
CREATE OR REPLACE MASKING POLICY GOVERNANCE.MASK_PRICE AS (val FLOAT) RETURNS FLOAT ->
  CASE WHEN IS_ROLE_IN_SESSION('PROCUREMENT_ROLE') OR IS_ROLE_IN_SESSION('ACCOUNTADMIN') THEN val ELSE NULL END;

CREATE OR REPLACE MASKING POLICY GOVERNANCE.MASK_LANDED AS (val FLOAT) RETURNS FLOAT ->
  CASE WHEN IS_ROLE_IN_SESSION('PROCUREMENT_ROLE') OR IS_ROLE_IN_SESSION('LOGISTICS_ROLE')
         OR IS_ROLE_IN_SESSION('ACCOUNTADMIN') THEN val ELSE NULL END;

ALTER VIEW CURATED.FACT_ORDER_LINE MODIFY COLUMN unit_cost   SET MASKING POLICY GOVERNANCE.MASK_PRICE;
ALTER VIEW CURATED.FACT_ORDER_LINE MODIFY COLUMN line_value  SET MASKING POLICY GOVERNANCE.MASK_PRICE;
ALTER VIEW CURATED.FACT_ORDER_LINE MODIFY COLUMN landed_cost SET MASKING POLICY GOVERNANCE.MASK_LANDED;

ALTER VIEW CURATED.FACT_ORDER_LINE MODIFY COLUMN unit_cost   SET TAG GOVERNANCE.DATA_SENSITIVITY = 'restricted';
ALTER VIEW CURATED.FACT_ORDER_LINE MODIFY COLUMN landed_cost SET TAG GOVERNANCE.DATA_SENSITIVITY = 'restricted';
ALTER VIEW CURATED.FACT_ORDER_LINE MODIFY COLUMN is_on_time  SET TAG GOVERNANCE.METRIC_OWNER = 'shared';
ALTER VIEW CURATED.FACT_ORDER_LINE MODIFY COLUMN is_in_full  SET TAG GOVERNANCE.METRIC_OWNER = 'planning';
