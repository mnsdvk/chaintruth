---
name: ontology-semantic-view-builder
description: Generate a business ontology (entities, relationships, canonical metrics) and a governed Snowflake semantic view from an existing schema, then validate it with consistency tests. Use when a user wants natural-language analytics that return one consistent answer across teams.
---

# Ontology + Semantic View Builder

Turns a messy schema into a governed ontology and a validated semantic view. Reusable for any domain (supply chain, finance, healthcare).

## Inputs to confirm with the user
1. Database and schema(s) holding the source or curated tables
2. The core business entities (or let the skill infer them)
3. The 3-8 metrics that teams argue about (e.g. on-time delivery, fill rate)
4. Which columns are sensitive (pricing, PII) and which roles may see them

## Steps
1. **Discover.** Query `INFORMATION_SCHEMA.TABLES/COLUMNS/TABLE_CONSTRAINTS` and sample rows. List candidate entities, primary keys, and foreign-key-like columns (matching names/values).
2. **Detect metric conflicts.** For each requested metric, find every column combination that plausibly defines it across systems. Compute each variant and show the spread. Ask the user to choose one canonical definition.
3. **Write the ontology tables.** Create `ONT_ENTITY`, `ONT_RELATIONSHIP`, `ONT_METRIC` (definition, formula, owner persona, sensitivity, legacy variants) and populate them.
4. **Conform the data.** Build a canonical fact (dynamic table) where the chosen definitions are computed once as columns (e.g. `is_on_time`).
5. **Generate the semantic view.** Emit `CREATE SEMANTIC VIEW` with TABLES (+ primary keys, synonyms, comments), RELATIONSHIPS, FACTS, DIMENSIONS, METRICS. Metrics reference the conformed columns only, never raw system columns.
6. **Govern.** Apply masking policies and tags to sensitive columns; grant persona roles SELECT on the semantic view.
7. **Validate.** Create a procedure that, for every metric, (a) compares the semantic view value to an independent golden query and (b) rolls up by every dimension lens and checks the weighted result equals the headline number. Log to a results table.
8. **Test in natural language.** Ask each metric in 3 phrasings through Cortex Analyst; assert identical values. Add misses as synonyms.
9. **Report.** Summarise entities, metrics, conflicts found, tests passed/failed, and open risks.

## Guardrails
- Never invent a metric definition; if two definitions conflict, stop and ask.
- Never expose raw sensitive columns in the semantic view without a masking policy.
- If any validation test fails, fix and rerun; do not report success.
- Use synthetic or de-identified data only.

## Outputs
`sql/` scripts, ontology tables, the semantic view, a test procedure, and a short markdown summary of decisions.
