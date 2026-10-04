"""Runs the same canonical metrics under each persona role and asserts:
   1) shared metrics are identical across Planning / Procurement / Logistics
   2) restricted metrics are masked for the wrong persona (governance holds)
Usage:  SNOWFLAKE_CONNECTION_NAME=<your snow cli connection> python tests/persona_consistency.py
"""
import json, os, sys
import snowflake.connector

PERSONAS = ["PLANNER_ROLE", "PROCUREMENT_ROLE", "LOGISTICS_ROLE"]
SV = "SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN"
SHARED = {
    "otd_pct": "order_lines.otd_pct",
    "fill_rate_pct": "order_lines.fill_rate_pct",
    "in_full_pct": "order_lines.in_full_pct",
    "avg_days_late": "order_lines.avg_days_late",
    "days_of_inventory": "inventory.days_of_inventory",
}
RESTRICTED = {  # metric -> roles that may see it
    "avg_landed_cost_per_unit": ("order_lines.avg_landed_cost_per_unit", {"PROCUREMENT_ROLE", "LOGISTICS_ROLE"}),
}

conn = snowflake.connector.connect(connection_name=os.getenv("SNOWFLAKE_CONNECTION_NAME", "default"))
cur = conn.cursor()


def metric(role, expr):
    cur.execute(f"USE ROLE {role}")
    cur.execute("USE SECONDARY ROLES NONE")
    cur.execute("USE WAREHOUSE SC_WH")
    cur.execute(f"SELECT * FROM SEMANTIC_VIEW({SV} METRICS {expr})")
    v = cur.fetchone()[0]
    return None if v is None else float(v)


results, failed = [], 0
for name, expr in SHARED.items():
    vals = {r: metric(r, expr) for r in PERSONAS}
    ok = len({round(v, 6) for v in vals.values() if v is not None}) == 1 and None not in vals.values()
    failed += not ok
    results.append({"test": "shared_metric_identical", "metric": name, "values": vals, "passed": ok})

for name, (expr, allowed) in RESTRICTED.items():
    vals = {r: metric(r, expr) for r in PERSONAS}
    ok = all((vals[r] is not None) == (r in allowed) for r in PERSONAS)
    failed += not ok
    results.append({"test": "restricted_metric_masked", "metric": name, "values": vals, "passed": ok})

print(f"{'test':28} {'metric':26} result")
for r in results:
    print(f"{r['test']:28} {r['metric']:26} {'PASS' if r['passed'] else 'FAIL'}  {r['values']}")
print(f"\n{len(results) - failed}/{len(results)} passed")

os.makedirs("tests", exist_ok=True)
json.dump(results, open("tests/last_run.json", "w"), indent=2)
sys.exit(1 if failed else 0)
