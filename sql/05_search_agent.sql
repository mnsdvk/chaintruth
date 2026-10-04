-- ChainTruth | 05_search_agent.sql
-- Cortex Search over contracts/SLAs + a Cortex Agent that orchestrates Analyst (numbers) and Search (clauses).
USE ROLE ACCOUNTADMIN; USE DATABASE SC_ONTOLOGY; USE WAREHOUSE SC_WH;

CREATE OR REPLACE CORTEX SEARCH SERVICE ONTOLOGY.CONTRACT_SEARCH
  ON doc_text
  ATTRIBUTES doc_id, supplier_id, supplier_name, doc_type, expiry_date
  WAREHOUSE = SC_WH
  TARGET_LAG = '1 day'
AS (
  SELECT doc_id, supplier_id, supplier_name, doc_type, expiry_date::STRING AS expiry_date, doc_text
  FROM RAW.CONTRACT_DOCS
);

CREATE OR REPLACE AGENT APP.SUPPLY_CHAIN_AGENT
  COMMENT = 'Governed supply chain copilot: canonical metrics via semantic view + contract evidence via search.'
  PROFILE = '{"display_name": "ChainTruth Copilot"}'
  FROM SPECIFICATION
  $$
  models:
    orchestration: auto
  instructions:
    response: >
      RESPONSE RULES (follow strictly):

      1. Be concise: at most 3 bullet points, each backed by a number shown in the result table.
      2. State which canonical metric definition you used (e.g. "OTD = delivered on or before promised date").
      3. When citing contract text, cite the document id from the doc_id attribute (e.g. DOC-SUP-012-SLA).
         NEVER cite the internal search record id (cs_... or similar). Include the SLA %, the penalty clause and the expiry date.
      4. If a number is NULL, explain it is restricted for the user's role. Do not guess.
      5. State only facts derived from the returned rows or retrieved contract text.
         Do NOT add benchmarks, targets, industry norms or generalisations (such as "well below typical
         targets", "every contract lapses before X") unless you computed them from the data.
      6. When comparing performance to a target, use the SLA percentage from the retrieved contract for
         that supplier, not an assumed number.
      7. Never end with an offer like "Would you like me to...", "If you'd like, I can...",
         "Shall I pull...", or "Let me know if you want...". The answer must be self-contained.
      8. Never invent a metric, number or clause.
    orchestration: >
      TOOL ROUTING RULES (follow strictly):

      1. NUMBERS ONLY — Use SupplyChainAnalyst for every numeric question about delivery, fill rate,
         inventory or landed cost where the user does NOT mention contracts, SLAs, penalties, renewals,
         or expiry.

      2. CONTRACTS ONLY — Use ContractSearch for questions that are purely about contract terms, SLAs,
         penalties, renewals, or expiry clauses for a named supplier. Do NOT call SupplyChainAnalyst.

      3. CROSS-DOMAIN (MANDATORY) — If the question combines supplier performance with contract status,
         OR mentions both a metric AND any of: contracts, SLAs, penalties, renewals, expiry,
         OR the result lists suppliers and the question mentions contracts, SLAs or expiry,
         you MUST execute BOTH tools in sequence, never just one:
           Step A: Call SupplyChainAnalyst to get the quantitative result.
           Step B: Immediately call ContractSearch for EACH of the top 3 suppliers from Step A.
                   Do NOT ask permission. Do NOT offer to search later. Do NOT skip this step.
           Step C: Combine both results into ONE answer.

      4. UNDEFINED METRIC — If the question uses a metric not defined in the semantic view, say so,
         list the six defined metrics (on-time delivery, fill rate, in-full %, average days late,
         days of inventory, landed cost) and ask which one the user means.

      5. AMBIGUOUS — If the question is ambiguous (no time window, unclear metric), ask one clarifying
         question rather than guessing.

      6. NEVER end an answer with an offer to search or pull more data. Execute all needed tool calls
         in this turn.
  tools:
    - tool_spec:
        type: "cortex_analyst_text_to_sql"
        name: "SupplyChainAnalyst"
        description: "Answers quantitative supply chain questions using governed canonical metrics over suppliers, parts, plants, order lines, customers and inventory."
    - tool_spec:
        type: "cortex_search"
        name: "ContractSearch"
        description: "Searches supplier supply agreements and SLA addenda for terms, penalties, renewal and expiry clauses."
  tool_resources:
    SupplyChainAnalyst:
      semantic_view: "SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN"
      execution_environment:
        type: "warehouse"
        warehouse: "SC_WH"
    ContractSearch:
      search_service: "SC_ONTOLOGY.ONTOLOGY.CONTRACT_SEARCH"
      max_results: "5"
  $$;

-- Optional: register the agent with Snowflake Intelligence so it shows up in the UI
-- CREATE SNOWFLAKE INTELLIGENCE IF NOT EXISTS SNOWFLAKE_INTELLIGENCE_OBJECT_DEFAULT;
-- ALTER SNOWFLAKE INTELLIGENCE SNOWFLAKE_INTELLIGENCE_OBJECT_DEFAULT ADD AGENT SC_ONTOLOGY.APP.SUPPLY_CHAIN_AGENT;
