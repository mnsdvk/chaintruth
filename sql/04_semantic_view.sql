-- ChainTruth | 04_semantic_view.sql
-- The ontology expressed as a governed semantic view. Business meaning (not column names) drives answers.
-- NOTE: if your account's DDL differs slightly, ask CoCo to "fix and validate this semantic view" -- that is a good demo moment.
USE ROLE ACCOUNTADMIN; USE DATABASE SC_ONTOLOGY; USE WAREHOUSE SC_WH;

CREATE OR REPLACE SEMANTIC VIEW SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN
  TABLES (
    order_lines AS SC_ONTOLOGY.CURATED.FACT_ORDER_LINE PRIMARY KEY (order_line_key)
      WITH SYNONYMS = ('shipments','deliveries','orders','order lines')
      COMMENT = 'One row per DELIVERED order line (carrier proof-of-delivery on or before today). In-transit lines excluded.',
    inventory AS SC_ONTOLOGY.CURATED.FACT_INVENTORY PRIMARY KEY (inventory_key)
      WITH SYNONYMS = ('stock','on hand')
      COMMENT = 'Latest on-hand inventory per part and plant.',
    suppliers AS SC_ONTOLOGY.CURATED.DIM_SUPPLIER PRIMARY KEY (supplier_id)
      WITH SYNONYMS = ('vendors')
      COMMENT = 'Suppliers with tier, status and contract expiry.',
    parts AS SC_ONTOLOGY.CURATED.DIM_PART PRIMARY KEY (part_id)
      WITH SYNONYMS = ('items','SKUs','materials')
      COMMENT = 'Parts and their category.',
    plants AS SC_ONTOLOGY.CURATED.DIM_PLANT PRIMARY KEY (plant_id)
      WITH SYNONYMS = ('factories','facilities','sites','warehouses')
      COMMENT = 'Plants and their region.',
    customers AS SC_ONTOLOGY.CURATED.DIM_CUSTOMER PRIMARY KEY (customer_id)
      WITH SYNONYMS = ('buyers','accounts','clients')
      COMMENT = 'Customers and their segment.'
  )
  RELATIONSHIPS (
    lines_to_suppliers AS order_lines (supplier_id) REFERENCES suppliers,
    lines_to_parts     AS order_lines (part_id)     REFERENCES parts,
    lines_to_plants    AS order_lines (plant_id)    REFERENCES plants,
    lines_to_customers AS order_lines (customer_id) REFERENCES customers,
    inventory_to_parts  AS inventory (part_id)  REFERENCES parts,
    inventory_to_plants AS inventory (plant_id) REFERENCES plants
  )
  FACTS (
    order_lines.is_on_time   AS is_on_time,
    order_lines.is_in_full   AS is_in_full,
    order_lines.qty_ordered  AS qty_ordered,
    order_lines.qty_shipped  AS qty_shipped,
    order_lines.days_late    AS days_late,
    order_lines.landed_cost  AS landed_cost,
    inventory.on_hand_qty      AS on_hand_qty,
    inventory.avg_daily_usage  AS avg_daily_usage
  )
  DIMENSIONS (
    order_lines.order_id        AS order_id,
    order_lines.delivered_date  AS delivered_date,
    order_lines.promised_date   AS promised_date,
    order_lines.delivery_month  AS delivery_month WITH SYNONYMS = ('month') COMMENT = 'Month of delivery (carrier proof of delivery).',
    order_lines.carrier         AS carrier WITH SYNONYMS = ('freight carrier','logistics provider'),
    suppliers.supplier_id       AS supplier_id,
    suppliers.supplier_name     AS supplier_name WITH SYNONYMS = ('vendor name'),
    suppliers.supplier_country  AS supplier_country,
    suppliers.supplier_tier     AS supplier_tier COMMENT = '1 = strategic, 3 = transactional',
    suppliers.supplier_status   AS supplier_status,
    suppliers.contract_expiry_date    AS contract_expiry_date WITH SYNONYMS = ('contract end date','contract renewal date'),
    suppliers.days_to_contract_expiry AS days_to_contract_expiry COMMENT = 'Days until the earliest supplier contract expires',
    parts.part_id        AS part_id,
    parts.part_name      AS part_name,
    parts.part_category  AS part_category WITH SYNONYMS = ('category'),
    plants.plant_id      AS plant_id,
    plants.plant_name    AS plant_name,
    plants.plant_country AS plant_country,
    plants.plant_region  AS plant_region,
    customers.customer_id      AS customer_id,
    customers.customer_name    AS customer_name,
    customers.customer_segment AS customer_segment WITH SYNONYMS = ('segment','industry'),
    customers.customer_region  AS customer_region,
    customers.service_tier     AS service_tier
  )
  METRICS (
    order_lines.line_count AS COUNT(order_lines.order_line_key)
      COMMENT = 'Number of order lines',
    order_lines.otd_pct AS 100 * AVG(order_lines.is_on_time)
      WITH SYNONYMS = ('on-time delivery','OTD','on time delivery rate','delivery performance','on-time percentage')
      COMMENT = 'CANONICAL on-time delivery %: delivered lines only (carrier proof of delivery on or before today); in-transit excluded.',
    order_lines.fill_rate_pct AS 100 * SUM(order_lines.qty_shipped) / NULLIF(SUM(order_lines.qty_ordered),0)
      WITH SYNONYMS = ('fill rate','quantity fill rate')
      COMMENT = 'Quantity shipped / quantity ordered, delivered lines only; in-transit excluded.',
    order_lines.in_full_pct AS 100 * AVG(order_lines.is_in_full)
      WITH SYNONYMS = ('in full','line fill rate')
      COMMENT = 'Share of delivered lines shipped in full; in-transit excluded.',
    order_lines.avg_days_late AS SUM(order_lines.days_late) / NULLIF(SUM(1 - order_lines.is_on_time),0)
      WITH SYNONYMS = ('average delay','days late')
      COMMENT = 'Average days past promised date, over late delivered lines only; in-transit excluded.',
    order_lines.total_landed_cost AS SUM(order_lines.landed_cost)
      WITH SYNONYMS = ('landed cost','total landed cost')
      COMMENT = 'Line value + freight + duty, delivered lines only; in-transit excluded. Restricted: masked for Planning.',
    order_lines.avg_landed_cost_per_unit AS SUM(order_lines.landed_cost) / NULLIF(SUM(order_lines.qty_shipped),0)
      WITH SYNONYMS = ('landed cost per unit','unit landed cost')
      COMMENT = 'Landed cost per unit shipped, delivered lines only; in-transit excluded. Restricted: masked for Planning.',
    inventory.days_of_inventory AS SUM(inventory.on_hand_qty) / NULLIF(SUM(inventory.avg_daily_usage),0)
      WITH SYNONYMS = ('DOI','days of supply','inventory cover','days on hand')
      COMMENT = 'On-hand quantity divided by average daily usage (latest snapshot).'
  )
  COMMENT = 'Supply chain ontology: Supplier-Part-Plant-OrderLine-Customer with canonical metrics (OTD, fill rate, days of inventory, landed cost).';

-- Smoke tests
SELECT * FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN METRICS order_lines.otd_pct, order_lines.fill_rate_pct, order_lines.avg_landed_cost_per_unit);
SELECT * FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN DIMENSIONS suppliers.supplier_name METRICS order_lines.otd_pct) ORDER BY otd_pct LIMIT 5;
SELECT * FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN METRICS inventory.days_of_inventory);
