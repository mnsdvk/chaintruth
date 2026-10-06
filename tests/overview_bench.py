"""Time the Overview render path's queries, using the SQL catalog read from app.py.
Usage: python tests/overview_bench.py before|after"""
import ast, json, os, sys, time
from snowflake.snowpark import Session

APP = os.path.join(os.path.dirname(__file__), "..", "streamlit_app", "app.py")
tree = ast.parse(open(APP, encoding="utf-8").read())
SQL = next(ast.literal_eval(n.value) for n in tree.body
           if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "SQL")
SEARCH = "SC_ONTOLOGY.ONTOLOGY.CONTRACT_SEARCH"
risk_search = ("SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW('%s','%s') AS r" % (SEARCH, json.dumps({
    "query": "SLA penalty late delivery corrective action",
    "columns": ["doc_id", "doc_type", "supplier_name", "doc_text", "expiry_date"],
    "filter": {"@eq": {"supplier_id": "SUP-024"}}, "limit": 3})))

mode = sys.argv[1]
if mode == "before":
    cold = ["header_metrics", "header_tests", "header_role", "hero_legacy", "kpi_main", "kpi_doi",
            "in_transit", "trend", "worst", "bridge_planning", "scatter_suppliers", "canonical_otd",
            risk_search, "corrective_actions"]
    every_rerun = [risk_search]                      # uncached today
else:
    cold = ["ov_core", "hero_legacy", "trend", "worst", "bridge_planning", "scatter_suppliers",
            risk_search, "corrective_actions"]
    every_rerun = ["corrective_actions"]             # run_nocache: must be fresh

s = Session.builder.config("connection_name", "IEVOOOP-FS85291").create()
s.sql("USE WAREHOUSE SC_WH").collect()
s.sql("ALTER SESSION SET USE_CACHED_RESULT = FALSE").collect()  # measure real execution, not result cache
s.sql("SELECT 1").collect()  # warm the connection
for label, keys in (("cold first load", cold), ("cached rerun", every_rerun)):
    t0 = time.time()
    for k in keys:
        s.sql(SQL.get(k, k)).collect()
    print(f"{mode:6s} {label:16s} {len(keys):2d} queries  {time.time()-t0:5.2f} s")
