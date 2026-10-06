"""Agent behaviour test: personas via run_all, sample chips via app.py's own Ask functions.
Usage: python tests/agent_rules_test.py"""
import ast, json, os, sys, time
HERE = os.path.dirname(__file__)
APP_DIR = os.path.join(HERE, "..", "streamlit_app")
sys.path.insert(0, APP_DIR)
from snowflake.snowpark import Session
import personas as P

session = Session.builder.config("connection_name", "IEVOOOP-FS85291").create()
session.sql("USE WAREHOUSE SC_WH").collect()

# Load the Ask-path functions from app.py itself (no copies).
src = open(os.path.join(APP_DIR, "app.py"), encoding="utf-8").read()
tree = ast.parse(src)
wanted = {"ask_agent", "parse_agent_response", "compute_badge", "run_nocache", "strip_narration"}
ns = {"json": json, "re": __import__("re"), "session": session, "AGENT": P.AGENT, "MASKED_COLS": set()}
for node in tree.body:
    is_fn = isinstance(node, ast.FunctionDef) and node.name in wanted
    is_rx = isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in ("_NARRATION", "_SENT")
    if is_fn or is_rx:
        exec(compile(ast.Module([node], []), "app.py", "exec"), ns)

print("=== 1. Personas via run_all, 3 runs ===")
for n in range(0 if "--chips-only" in sys.argv else 3):
    t0 = time.time()
    res, conc = P.run_all(session)
    ok, msg = P.verdict(res)
    print(f"run {n+1}: {time.time()-t0:.1f}s  {msg}")
    for name, r in res.items():
        v = f"{r['value']:.4f}" if r["value"] is not None else "-"
        print(f"   {name:12s} {v:>9s} {r['secs']:5.1f}s retried={r.get('retried', False)} {r['reason']}")

CHIPS = [
    "Which 5 suppliers have the lowest on-time delivery and a contract expiring within 90 days?",
    "What penalty applies to late deliveries for Supplier Cobalt 12?",
    "What is our customer satisfaction score?",
    "What is our on-time delivery rate by plant region?",
    "What is days of inventory by part category?",
]
print("\n=== 2/3. Sample chips via app.py ask_agent + parse_agent_response ===")
for qn in CHIPS:
    t0 = time.time()
    resp = ns["ask_agent"](qn)
    parsed = ns["parse_agent_response"](resp)
    badge = ns["compute_badge"](parsed, None)
    text = " ".join(parsed["texts"])
    asked = (not parsed["sql"]) and ("?" in text) and badge[0] != "ref"
    print(f"\nQ: {qn}\n   {time.time()-t0:.1f}s tools={sorted(parsed['tools'])} sql={'yes' if parsed['sql'] else 'no'} "
          f"badge={badge[1]!r} clarifying_question={asked}")
    print("   answer: " + text.replace("\n", " ")[:330])
    # same steps as the app: join with blank lines, strip narration, show first 2 blocks
    shown = ns["strip_narration"]("\n\n".join(parsed["texts"]))
    lines = [l for l in shown.splitlines() if l.strip()][:2]
    print("   displayed line 1: " + (lines[0] if lines else "(empty)"))
    print("   displayed line 2: " + (lines[1] if len(lines) > 1 else "(none)"))
