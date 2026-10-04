# ChainTruth

**One supply chain. One definition. One answer.**

A governed supply chain ontology and conversational analytics copilot built on Snowflake, using CoCo CLI across the full lifecycle.

Team Singularity | Manasa Devarakonda | Snowflake CoCo CLI Hackathon, GCC Edition
Problem statement: Supply Chain Ontology and Governed Conversational Analytics

<!-- Demo video: add link here -->

> All data is fully synthetic. No production or personal data is used.

---

## The problem

Supply chain data lives in ERP, logistics, procurement and inventory systems, and each defines "on time" differently. On our dataset the same deliveries give **88.5%** (Planning), **67.0%** (Procurement) and **43.6%** (Logistics) on-time delivery, a **44.9-point spread**. Decisions stall while teams reconcile.

## What ChainTruth does

Defines the business once, as a governed Snowflake semantic view, and lets anyone ask questions in plain English.

- **One canonical answer.** On-time delivery is defined once (carrier proof of delivery on or before the date promised to the customer), giving **69.0%**, the same for every persona.
- **Structured plus unstructured.** A Cortex Agent combines Cortex Analyst (numbers) with Cortex Search (supplier contracts and SLAs), so answers carry contract clauses with document ids.
- **Governed.** Masking policies hide landed cost from Planning, and persona roles see identical shared metrics.
- **Honest.** Undefined metrics (for example "customer satisfaction") are refused instead of guessed.
- **Provable.** Every answer shows its SQL, the metric definition used and a downloadable receipt. Nine automated consistency tests run nightly.

## The app (Streamlit in Snowflake)

| Tab | What it shows |
|---|---|
| Overview | Four conflicting team numbers vs the canonical one, KPI cards, trend, worst suppliers, reconciliation bridge, supplier risk quadrant, corrective actions |
| Ask | Plain-English questions with a proof receipt, contract evidence and a refusal for undefined metrics |
| Personas | The same metric asked three ways returns the same number |
| Governance | What each role sees, with restricted values shown as restricted |
| Ontology | Entity graph, metric glossary and a lineage view from source to agent |
| Trust | Live consistency test results and alerts |

## Architecture

```
ERP / Logistics / Inventory (structured)      Contracts and SLAs (unstructured)
            |                                              |
   RAW  ->  dynamic tables (canonical metrics,      Cortex Search service
            delivered lines only, incremental)              |
            |                                               |
   masking policies + tags + persona roles                  |
            |                                               |
     Semantic view (the ontology) -----> Cortex Agent <-----+
                                              |
                                        Streamlit app
```

Two scheduled tasks run unattended: a nightly consistency test and a 15-minute late-shipment alert. Diagram source: `docs/ARCHITECTURE.mmd`.

## Repository layout

| Path | Purpose |
|---|---|
| `sql/00_setup.sql` | Database, schemas, warehouse, persona roles and grants |
| `sql/01_synthetic_data.sql` | Referentially consistent synthetic data, with deliberately inconsistent source definitions |
| `sql/02_pipeline.sql` | Dynamic tables, canonical fact (delivered lines only), legacy comparison view, stream and alert task |
| `sql/03_ontology_governance.sql` | Ontology tables, tags and masking policies |
| `sql/04_semantic_view.sql` | The semantic view (entities, relationships, metrics, synonyms) |
| `sql/05_search_agent.sql` | Cortex Search service and Cortex Agent |
| `sql/06_tests_automation.sql` | Consistency test procedure and nightly task |
| `sql/07_grants.sql` | Persona role grants |
| `sql/08_role_snapshot.sql` | Captured per-role visibility snapshot used by the Governance tab |
| `sql/09_corrective_actions.sql` | Corrective-action table and procedures |
| `streamlit_app/` | The Streamlit in Snowflake app |
| `tests/persona_consistency.py` | Runs metrics under each persona role |
| `skills/ontology-semantic-view-builder/` | Reusable CoCo skill: schema to ontology and semantic view |
| `docs/` | Design document produced with CoCo, architecture diagram, playbook |

## How CoCo CLI was used

- **Plan:** explored the account, drafted the ontology and design, flagged syntax risks (`docs/design_from_coco.md`).
- **Build:** ran the SQL, semantic view, search service, agent and app, and fixed errors along the way.
- **Run:** scheduled tasks for nightly consistency tests and late-shipment alerts.
- **Test:** consistency tests, persona and masking checks, refusal and agent tests.
- **Reuse:** authored the `ontology-semantic-view-builder` skill.

## Run it yourself

**Prerequisites:** a Snowflake account (ACCOUNTADMIN) in a region with Cortex Analyst, Cortex Agents and Cortex Search available, with cross-region inference enabled if your region needs it, and the [Snowflake CLI](https://docs.snowflake.com/en/developer-guide/snowflake-cli/index) with a configured connection.

**macOS, Linux or WSL:**

```bash
./deploy.sh <connection_name>
```

**Windows PowerShell:**

```powershell
Get-ChildItem sql\0*.sql | Sort-Object Name | ForEach-Object { snow sql -c <connection_name> -f $_.FullName }
snow streamlit deploy --replace -c <connection_name>
```

Run the SQL files in order (`00` to `09`), then deploy the app. `07_grants.sql` must run after the semantic view, search service and agent exist. If a statement fails because Snowflake syntax has moved on, paste the error into CoCo and ask it to fix and validate.

**Optional checks:**

- `python tests/persona_consistency.py` (uses your Snowflake CLI connection).
- In Snowsight, run `CALL SC_ONTOLOGY.GOVERNANCE.RUN_CONSISTENCY_TESTS();`.

**Cost control:** the warehouse is X-Small and suspends after 60 seconds. To stop all background spend, suspend the warehouse `SC_WH` and the tasks in `SC_ONTOLOGY.GOVERNANCE`.

## Results on the synthetic dataset (4 Oct 2026)

| Measure | Value |
|---|---|
| Team on-time delivery (Planning / Procurement / Logistics) | 88.5% / 67.0% / 43.6% |
| Canonical on-time delivery | 69.0% |
| Fill rate / in-full / days of inventory | 97.2% / 87.9% / 32.3 days |
| Delivered lines / in-transit lines (excluded) | 18,785 / 1,215 |
| Consistency tests | 9 of 9 passing |
| On-time delivery under Planner, Procurement, Logistics roles | 68.99% in all three |
| Landed cost | Masked for Planning only |

Delivery metrics use the current date to separate delivered from in-transit lines, so figures shift slightly each day.

## Limitations

- The Streamlit app runs inside Snowflake and needs a Snowflake login, so it is not publicly accessible. The deployment steps above reproduce it in any suitable account.
- The app runs with the owner's rights, so the Governance tab shows a captured snapshot of each role's view instead of live role switching.
- No formal agent accuracy test set has been run yet.
- Slack and Jira alerts via MCP are planned, not built.
- The reusable skill has not yet been run on a second domain.

## Next steps

Real ERP and TMS feeds, Slack or Jira alerts via MCP, a formal accuracy evaluation set, and running the skill on additional domains.