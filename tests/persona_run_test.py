"""Drive streamlit_app/personas.py exactly as the app does. Usage: python tests/persona_run_test.py"""
import os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "streamlit_app"))
from snowflake.snowpark import Session
import personas as P

session = Session.builder.config("connection_name", "IEVOOOP-FS85291").create()
session.sql("USE WAREHOUSE SC_WH").collect()

ORDERS = {
    "default": P.PERSONAS,
    "reversed": list(reversed(P.PERSONAS)),
    "logistics-first": [P.PERSONAS[2], P.PERSONAS[0], P.PERSONAS[1]],
}
mode = sys.argv[1] if len(sys.argv) > 1 else "default"
runs = int(sys.argv[2]) if len(sys.argv) > 2 else 1
for n in range(runs):
    t0 = time.time()
    res, conc = P.run_all(session, ORDERS[mode])
    ok, msg = P.verdict(res)
    print(f"[{mode} run {n+1}] total {time.time()-t0:.1f}s concurrent={conc} -> {msg}")
    for name, r in res.items():
        v = f"{r['value']:.4f}" if r["value"] is not None else "-"
        print(f"   {name:12s} {v:>9s}  {r['secs']:5.1f}s  retried={r.get('retried', False)}  {r['reason']}")
        if r["error"]:
            print("      " + r["error"].strip().splitlines()[-1])
