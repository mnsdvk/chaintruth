# ChainTruth

Governed supply chain ontology + copilot on Snowflake, built for the CoCo CLI Hackathon (Supply Chain Ontology track).

## What's inside
| Path | Purpose |
|---|---|
| `sql/00-07` | Setup, synthetic data, pipelines, ontology + governance, semantic view, search + agent, tests + tasks, grants |
| `streamlit_app/` | Streamlit in Snowflake app (problem view, ask, persona check, ontology, trust) |
| `tests/persona_consistency.py` | Runs metrics under each persona role |
| `skills/ontology-semantic-view-builder/` | Reusable CoCo skill |
| `docs/` | CoCo playbook, architecture, submission deck content |

## Run order
```bash
# Prereqs: Snowflake CLI configured (snow connection add), ACCOUNTADMIN, Cortex enabled in your region
./deploy.sh <connection_name>
```
or step by step: `snow sql -c <conn> -f sql/00_setup.sql` ... `07_grants.sql`, then `snow streamlit deploy --replace`.

**Do it through CoCo** (the hackathon requires CoCo across the lifecycle): use the prompts in `docs/COCO_PLAYBOOK.md`.

## Known things to check on first run
- Cortex Agent / Semantic View DDL evolves quickly; if a statement errors, paste the error to CoCo ("fix and validate"). Keep that in your demo.
- Cortex Analyst, Agents and Cortex Search must be available in your account region.
- `07_grants.sql` must run after the semantic view, search service and agent exist.
- The Streamlit "Ask" and "personas" tabs work only inside Snowsight (they use the `_snowflake` API).
