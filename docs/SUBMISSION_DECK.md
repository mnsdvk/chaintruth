# ChainTruth: submission deck content

Paste into your template. Anything in [brackets] must come from YOUR run; do not submit placeholders.

---
## Slide 1: Title
**ChainTruth: one supply chain, one definition, one answer**
Snowflake CoCo CLI Hackathon | Supply Chain Ontology track | Team [name]

---
## Slide 2: Problem brief

**Business problem.** Supply chain data lives in ERP, logistics, supplier and inventory systems, each with its own definition of core metrics. Ask "what's our on-time delivery?" and Planning, Procurement and Logistics each get a different number, so meetings turn into reconciliation and decisions stall.

**Target personas.**
- Supply chain planner (OTD, fill rate, days of inventory)
- Procurement lead (supplier performance, landed cost, contract risk)
- Logistics manager (carrier performance, delays)
- Plus the VP Operations who needs one trusted number

**Current pain point.**
- Same metric, different answers: in our dataset the four existing definitions of OTD give [X% / Y% / Z% / W%] (see `VW_LEGACY_OTD_BY_TEAM`), a spread of [N] points
- Analysts rebuild the same SQL per team; definitions live in people's heads
- Contract and SLA context sits in documents, disconnected from performance data

**How ChainTruth improves it.** A governed ontology (Supplier, Part, Plant, Order line, Customer, Inventory) encoded as a Snowflake semantic view. Canonical metrics are defined once; a Cortex Agent answers numeric questions through that layer and contract questions through search, so every persona gets the same answer with evidence.

**Industry/domain.** Manufacturing and distribution supply chain; the pattern applies to any metric-heavy domain.

---
## Slide 3: Architecture diagram
Use `docs/ARCHITECTURE.mmd` (render at mermaid.live or in Snowsight/Notion) and annotate:

**Data flow.** Raw ERP, logistics, inventory and contract documents -> dynamic tables compute canonical metrics once -> masking policies and tags -> semantic view (the ontology) -> Cortex Agent (Analyst + Search) -> Streamlit app, Snowsight, Slack.

**Data sources.** Structured: ERP order lines, logistics shipments, inventory (synthetic). Unstructured: supplier agreements and SLA addenda (Cortex Search).

**CoCo skills and how they connect.**
| Phase | CoCo used for | Artifact |
|---|---|---|
| Plan | Explore data, draft ontology and design | `docs/design_from_coco.md` |
| Build | Synthetic data, pipelines, semantic view, agent, app | `sql/`, `streamlit_app/` |
| Run | Scheduled consistency task, stream-driven alerts | `T_NIGHTLY_CONSISTENCY`, `T_LATE_SHIPMENT_ALERTS` |
| Test | Persona and roll-up consistency, guardrail checks | `tests/`, `RUN_CONSISTENCY_TESTS` |
| Reuse | Published skill `ontology-semantic-view-builder` | `skills/` |

**Modularity.** Each layer is swappable: replace RAW with real sources, add metrics by adding a row to `ONT_METRIC` plus one semantic view metric, add domains by running the skill on a new schema, add channels (Slack, Jira) via MCP without touching the data layer.

**Guardrails.** Undefined metric -> refuses and lists defined ones; ambiguous question -> asks to clarify; restricted columns masked by role; generated SQL checked read-only; every answer shows its SQL and metric definition.

---
## Slide 4: Impact statement

**Measurable outcomes (fill from your demo run).**
- Conflicting OTD definitions: **4 -> 1** (from `VW_LEGACY_OTD_BY_TEAM`)
- Persona consistency: [N/N] shared-metric checks identical across 3 personas (`persona_consistency.py`)
- Roll-up consistency: [N/N] lenses (supplier, plant, customer) reconcile to the headline number
- Governance: [N/N] restricted-metric checks masked correctly per role
- Drift detection: deliberately broke a metric, nightly test caught it in [time]
- Time to answer a cross-domain question (late suppliers with expiring contracts): [seconds] vs [minutes] writing SQL plus reading contracts manually. Time it on camera.

**Scalability.**
- Snowflake-native: dynamic tables refresh incrementally; Cortex Search and Analyst scale with the warehouse
- Adding a metric or entity is a row plus one semantic view line
- Governance (masking, tags, roles) is enforced in the platform, not the app

**Beyond the demo.**
- Replace synthetic RAW with SAP/Oracle/TMS feeds via Snowpipe or Openflow
- Add more personas (finance, sales) and domains using the reusable skill
- Close the loop with MCP: open Jira tickets for chronic suppliers, post drift alerts to Slack
- Extend to forecasting and scenario analysis on the same governed layer

---
## Slide 5 (optional): Demo flow
1. Four teams, four numbers (Problem tab)
2. Ontology graph and canonical definitions
3. Same question, three personas, one answer
4. "Which suppliers causing late shipments also have expiring contracts?"
5. "What's our customer satisfaction score?" -> refuses safely
6. Trust tab: tests green; break a metric, rerun, red
7. CoCo across the lifecycle + published skill
