# ChainTruth

**One supply chain. One definition. One answer.**

ChainTruth gives every team in a supply chain organisation the same trustworthy answer to the same question. Ask in plain English and get the number, the definition behind it, and the contract evidence that goes with it.

<!-- Demo video: add link here -->

> All data in this project is synthetic. No production or personal data is used.

---

## The problem

Supply chain data is scattered across ERP, logistics, supplier and warehouse systems, with inconsistent definitions, so the same question yields different answers across teams. Orders sit in the ERP, deliveries in the transport system, stock in the warehouse system and supplier terms in contract documents, and each system and each team defines the same metric slightly differently.

Take on-time delivery. Planning measures when goods leave the warehouse against the date the customer asked for. Procurement measures when the supplier dispatched against the date the supplier promised. Logistics measures when the carrier delivered against the carrier's own estimate. On the sample data, the same deliveries produce three different answers:

| Team | On-time delivery |
|---|---|
| Planning | 88.5% |
| Procurement | 67.0% |
| Logistics | 43.6% |

That is a 44.9-point spread for one business. The consequences are familiar:

- **Meetings become reconciliation.** Time goes on arguing which number is right instead of acting on it.
- **Nobody can explain the gap.** There is no way to trace the difference between two teams' figures back to its cause.
- **Definitions live in people's heads.** Analysts rewrite the same logic for every report, and it drifts.
- **Performance and contracts are disconnected.** A supplier's delivery record sits in one place and its penalty and renewal terms in a document nobody cross-checks.
- **Answers can't be audited.** Chat-style tools guess when a metric isn't defined and rarely show how they got an answer.

## The solution

ChainTruth defines the business once and makes that definition the only way numbers are produced.

1. **Define once, as an ontology.** The business is described as one shared model: the entities (suppliers, parts, plants, orders and their deliveries, customers, inventory), how they relate, and one written definition, owner and formula for each metric, such as on-time delivery, fill rate or landed cost.
2. **Compute once.** Every figure in the app is calculated from the same cleaned data, using only lines that have actually been delivered. In-transit lines are excluded rather than counted as on time.
3. **Ask in plain English.** Questions about numbers are answered from the governed definitions. Questions about contracts are answered from the contract text. Questions that need both, such as "which weak suppliers have contracts ending soon?", get both in one answer.
4. **Show the proof.** Every answer shows its question, result, the definition used, the exact query and the contract clause with its document id, and comes with a downloadable receipt.
5. **Keep checking.** Automated tests compare every metric against an independent calculation and confirm that roll-ups by supplier, plant or customer add up to the headline number. They run every night.

The result is one on-time delivery figure, 69.0%, that every team sees, with a clear explanation of why each team's old number differed.

## Who it is for

- **Supply chain planners** who need delivery, fill and inventory figures they can rely on
- **Procurement leads** managing supplier performance, landed cost and contract renewals
- **Logistics managers** tracking carrier delivery and delays
- **Operations leaders** who need one trusted number in a review
- **Data and analytics teams** tired of rebuilding the same metric logic for every request

## What it does

- **One governed definition per metric.** On-time delivery, fill rate, in-full %, average days late, days of inventory and landed cost are each defined once and used everywhere.
- **Plain-English questions.** Ask the way you would ask a colleague and get a sourced answer.
- **Explains the gap.** A reconciliation bridge walks from any team's number to the canonical one, step by step, with the query behind each step.
- **Flags supplier risk.** A risk map highlights suppliers with below-average delivery and contracts ending within 90 days.
- **Turns insight into action.** One click records a corrective action with the contract clause attached, and prevents duplicates.
- **Refuses to guess.** Ask for something that isn't defined, such as a customer satisfaction score, and it says so and lists what it can answer.
- **Respects roles.** Planning, Procurement and Logistics see identical shared metrics, while landed cost is hidden from Planning.
- **Proves itself.** Receipts on every answer and nightly consistency tests.

## Example: from question to action

**Question:** *Which suppliers have the lowest on-time delivery and a contract expiring within 90 days?*

**Answer:** the matching suppliers with their delivery rate, days to contract expiry and order volume, charted against the canonical average. For Supplier Ember 24, the app also shows the contract evidence:

> **DOC-SUP-024-SLA:** on-time delivery commitment of 95%; a late-delivery credit of 1.5% of line value per late line, capped at 10% of monthly spend; a corrective action plan within 15 days if the supplier is below SLA for two consecutive months.
>
> **DOC-SUP-024-SA:** the supply agreement expires on 2026-11-12 and renews automatically unless notice is given 60 days ahead.

**Action:** one click records a corrective action for the supplier, citing that clause, so procurement can open the renewal conversation with evidence.

## Using the app

| Tab | What you can do |
|---|---|
| **Overview** | See the conflicting team numbers beside the canonical one, KPI cards, monthly trend, worst suppliers, the reconciliation bridge, the supplier risk map and corrective actions |
| **Ask** | Click a sample question or type your own. Each answer shows the question, result, chart, contract evidence and a proof receipt |
| **Personas** | Ask the same question three ways, as Planning, Procurement and Logistics would, and confirm the number is identical |
| **Governance** | Compare what each role can see. Restricted values are marked as restricted |
| **Ontology** | Browse the entities and relationships, read each metric's definition, and trace its lineage from source data to answer |
| **Trust** | See the latest consistency test results, rerun them, and view open alerts |

**Questions to try**

- Which suppliers have the lowest on-time delivery and a contract expiring within 90 days?
- What penalty applies to late deliveries for Supplier Cobalt 12?
- What is our on-time delivery rate by plant region?
- What is days of inventory by part category?
- What is our customer satisfaction score? *(it should refuse)*

## Metrics

| Metric | Definition |
|---|---|
| On-time delivery % | Share of delivered order lines that arrived on or before the date promised to the customer |
| Fill rate % | Quantity shipped divided by quantity ordered |
| In-full % | Share of delivered lines where shipped quantity met ordered quantity |
| Average days late | Average days past the promised date, across late lines only |
| Days of inventory | On-hand quantity divided by average daily usage, latest snapshot |
| Landed cost per unit | (Line value + freight + duty) divided by units shipped. Hidden from Planning |

## Sample results

Measured on the synthetic dataset on 4 Oct 2026.

| Measure | Value |
|---|---|
| Team on-time delivery (Planning / Procurement / Logistics) | 88.5% / 67.0% / 43.6% |
| Canonical on-time delivery | 69.0% |
| Fill rate / in-full / days of inventory | 97.2% / 87.9% / 32.3 days |
| Delivered / in-transit lines | 18,785 / 1,215 |
| Consistency tests | 9 of 9 passing |
| On-time delivery under all three roles | 68.99% |

Delivery figures shift slightly each day as in-transit lines are delivered.

## Quick start

Setup is fully scripted. The database scripts in `sql/` run in numeric order (`00` to `09`) and the app lives in `streamlit_app/`.

```bash
./deploy.sh <connection_name>
```

On Windows, run `deploy.sh` from Git Bash or WSL. To check consistency across roles, run `python tests/persona_consistency.py`.

## Project layout

| Path | Contents |
|---|---|
| `sql/` | Numbered setup scripts: data, metric pipeline, definitions, governance, question answering, tests, corrective actions |
| `streamlit_app/` | The app |
| `tests/` | Persona consistency test |
| `skills/` | A reusable skill that turns a data schema into a governed set of metric definitions |
| `docs/` | Design notes and architecture diagram |

## Limitations

- The app runs in a private workspace, so there is no public live link.
- The Governance tab shows a captured snapshot of each role's view rather than switching roles live.
- No formal accuracy test set has been run yet for the question answering.
- Slack and Jira alerts are planned, not built.

## Roadmap

Connect real ERP and transport feeds, add Slack and Jira alerts, build a formal accuracy evaluation set, and extend the approach to other domains.