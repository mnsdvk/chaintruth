-- ChainTruth | 09_corrective_actions.sql
-- Table and procedure for supplier corrective actions triggered from the risk quadrant.
USE ROLE ACCOUNTADMIN; USE DATABASE SC_ONTOLOGY; USE WAREHOUSE SC_WH;

CREATE TABLE IF NOT EXISTS GOVERNANCE.CORRECTIVE_ACTIONS (
  action_id STRING DEFAULT UUID_STRING(),
  supplier_id STRING,
  supplier_name STRING,
  otd_pct FLOAT,
  contract_expiry DATE,
  cited_clause STRING,
  created_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  status STRING DEFAULT 'OPEN'
);

CREATE OR REPLACE PROCEDURE GOVERNANCE.CREATE_CORRECTIVE_ACTION(p_supplier_id STRING)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
  existing INTEGER;
  s_name STRING;
  s_otd FLOAT;
  s_expiry DATE;
  s_clause STRING;
BEGIN
  -- Prevent duplicate open actions for the same supplier
  SELECT COUNT(*) INTO :existing
    FROM GOVERNANCE.CORRECTIVE_ACTIONS
    WHERE supplier_id = :p_supplier_id AND status = 'OPEN';
  IF (existing > 0) THEN
    RETURN 'DUPLICATE: an open corrective action already exists for ' || :p_supplier_id;
  END IF;

  -- Look up supplier details
  SELECT supplier_name, days_to_contract_expiry
    INTO :s_name, :s_expiry
    FROM SC_ONTOLOGY.CURATED.DIM_SUPPLIER
    WHERE supplier_id = :p_supplier_id;

  -- Get OTD from the delivered fact
  SELECT ROUND(100*AVG(is_on_time),2) INTO :s_otd
    FROM SC_ONTOLOGY.CURATED.FACT_ORDER_LINE
    WHERE supplier_id = :p_supplier_id;

  -- Get contract expiry date
  SELECT contract_expiry_date INTO :s_expiry
    FROM SC_ONTOLOGY.CURATED.DIM_SUPPLIER
    WHERE supplier_id = :p_supplier_id;

  -- Get top contract clause via SEARCH_PREVIEW
  BEGIN
    LET search_payload STRING := '{"query":"SLA penalty late delivery corrective action","columns":["doc_id","doc_text"],"filter":{"@eq":{"supplier_id":"' || :p_supplier_id || '"}},"limit":1}';
    LET search_result STRING;
    SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW('SC_ONTOLOGY.ONTOLOGY.CONTRACT_SEARCH', :search_payload) INTO :search_result;
    SELECT GET_PATH(PARSE_JSON(:search_result), 'results[0].doc_text')::STRING INTO :s_clause;
  EXCEPTION
    WHEN OTHER THEN
      s_clause := 'No contract clause found';
  END;

  INSERT INTO GOVERNANCE.CORRECTIVE_ACTIONS (supplier_id, supplier_name, otd_pct, contract_expiry, cited_clause)
    VALUES (:p_supplier_id, :s_name, :s_otd, :s_expiry, :s_clause);

  RETURN 'CREATED: corrective action opened for ' || :s_name || ' (' || :p_supplier_id || ')';
END;
$$;

-- Grants
GRANT SELECT, INSERT ON TABLE GOVERNANCE.CORRECTIVE_ACTIONS TO ROLE PLANNER_ROLE;
GRANT SELECT, INSERT ON TABLE GOVERNANCE.CORRECTIVE_ACTIONS TO ROLE PROCUREMENT_ROLE;
GRANT SELECT, INSERT ON TABLE GOVERNANCE.CORRECTIVE_ACTIONS TO ROLE LOGISTICS_ROLE;
GRANT USAGE ON PROCEDURE GOVERNANCE.CREATE_CORRECTIVE_ACTION(STRING) TO ROLE PLANNER_ROLE;
GRANT USAGE ON PROCEDURE GOVERNANCE.CREATE_CORRECTIVE_ACTION(STRING) TO ROLE PROCUREMENT_ROLE;
GRANT USAGE ON PROCEDURE GOVERNANCE.CREATE_CORRECTIVE_ACTION(STRING) TO ROLE LOGISTICS_ROLE;

-- Reset procedure: sets all OPEN actions to CLOSED (does not delete rows)
CREATE OR REPLACE PROCEDURE GOVERNANCE.RESET_CORRECTIVE_ACTIONS()
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
  n INTEGER;
BEGIN
  UPDATE SC_ONTOLOGY.GOVERNANCE.CORRECTIVE_ACTIONS SET status = 'CLOSED' WHERE status = 'OPEN';
  SELECT COUNT(*) INTO :n FROM SC_ONTOLOGY.GOVERNANCE.CORRECTIVE_ACTIONS WHERE status = 'CLOSED';
  RETURN 'Reset complete: ' || :n || ' total closed actions.';
END;
$$;

GRANT USAGE ON PROCEDURE GOVERNANCE.RESET_CORRECTIVE_ACTIONS() TO ROLE PLANNER_ROLE;
GRANT USAGE ON PROCEDURE GOVERNANCE.RESET_CORRECTIVE_ACTIONS() TO ROLE PROCUREMENT_ROLE;
GRANT USAGE ON PROCEDURE GOVERNANCE.RESET_CORRECTIVE_ACTIONS() TO ROLE LOGISTICS_ROLE;

-- Close a single corrective action by action_id
CREATE OR REPLACE PROCEDURE GOVERNANCE.CLOSE_CORRECTIVE_ACTION(p_action_id STRING)
RETURNS STRING
LANGUAGE SQL
EXECUTE AS CALLER
AS
$$
DECLARE
  n INTEGER;
BEGIN
  UPDATE SC_ONTOLOGY.GOVERNANCE.CORRECTIVE_ACTIONS
    SET status = 'CLOSED'
    WHERE action_id = :p_action_id AND status = 'OPEN';
  SELECT COUNT(*) INTO :n
    FROM SC_ONTOLOGY.GOVERNANCE.CORRECTIVE_ACTIONS
    WHERE action_id = :p_action_id AND status = 'CLOSED';
  IF (n = 0) THEN
    RETURN 'NOT FOUND: no open action with id ' || :p_action_id;
  END IF;
  RETURN 'CLOSED: action ' || :p_action_id || ' marked closed.';
END;
$$;
