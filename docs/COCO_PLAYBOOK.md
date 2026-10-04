# CoCo playbook: how to show CoCo in every phase

Judges look for CoCo evidence at each stage. The files in this repo are a starting point; **run them, extend them and debug them through CoCo, and capture it** (screen recording or exported session logs). Suggested prompts below. Keep the CLI transcript and take one screenshot per phase.

## 1. Planning
> "Explore the Snowflake account. I'm building a supply chain ontology copilot (Supplier, Part, Plant, Order line, Customer) with canonical metrics OTD, fill rate, days of inventory, landed cost. Propose a data model, ontology and workflow, and list the risks. Don't build yet."

Evidence: the design doc / ontology draft CoCo produced. Save it as `docs/design_from_coco.md`.

## 2. Development
> "Create synthetic, referentially consistent data for this model. Make three source systems define 'on time' differently so teams disagree. Run sql/01_synthetic_data.sql and fix any errors."

> "Review sql/02_pipeline.sql, deploy it, and confirm the dynamic tables refresh."

> "Create the semantic view from sql/04_semantic_view.sql. Add verified queries for the 5 most common questions, then validate it against these natural-language questions: ..."

> "Create the Cortex Search service and Cortex Agent from sql/05_search_agent.sql and test a cross-domain question."

> "Scaffold and deploy the Streamlit app in streamlit_app/ and fix any runtime errors."

## 3. Execution
> "Schedule a task that runs GOVERNANCE.RUN_CONSISTENCY_TESTS() every night and alerts on failures."

> "Insert 50 new late shipments into RAW.LOGISTICS_SHIPMENTS and show the stream and task producing alerts."

Optional: a CoCo scheduled/automated run that runs the test suite and posts the summary to Slack, or opens a Jira ticket via MCP when supplier OTD falls below SLA.

## 4. Testing and validation
> "Run tests/persona_consistency.py and explain any failure."

> "Break the semantic view on purpose (change the OTD formula) and show the nightly test catching it. Then revert."

> "Ask the agent: 'What is our customer satisfaction score?' and confirm it refuses instead of guessing."

## Reusable skill (bonus)
Publish `skills/ontology-semantic-view-builder/` and show another team's schema (e.g. banking) being converted with it in 2 minutes.

## Extra credit checklist
- [ ] MCP: Slack message or Jira ticket on `METRIC_DRIFT` / low supplier OTD
- [ ] Scheduled run visible in CoCo
- [ ] Same solution shown in CLI, Desktop app and Snowsight
- [ ] Guardrail demo (undefined metric, restricted column, ambiguous question)
