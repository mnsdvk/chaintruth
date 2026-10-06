"""Headless render of streamlit_app/app.py with Streamlit AppTest against the real account.
Checks every tab renders without error panels, and that Create / Reset / Run tests show fresh data.
Usage: python tests/app_smoke_test.py"""
import os, re, sys, time
os.environ.setdefault("SNOWFLAKE_DEFAULT_CONNECTION_NAME", "IEVOOOP-FS85291")
from streamlit.testing.v1 import AppTest

APP = os.path.join(os.path.dirname(__file__), "..", "streamlit_app", "app.py")


def all_md(at):
    return " ".join(m.value for m in at.markdown)


def errors(at):
    md = all_md(at)
    bad = re.findall(r"Could not load ([^.<]+)\.", md)
    return bad + [e.value for e in at.exception] + [e.value for e in at.error]


def ca_rows(at):
    """(open_rows, closed_caption) as rendered in the Overview corrective-actions section."""
    open_df = next((d.value for d in at.dataframe
                    if "STATUS" in d.value.columns and (d.value["STATUS"] == "OPEN").all() and len(d.value)), None)
    closed = next((c.value for c in at.caption if "earlier action" in c.value), "")
    return (0 if open_df is None else len(open_df)), closed


t0 = time.time()
# Same session context SiS gives the app (it runs inside SC_ONTOLOGY.APP on SC_WH).
# app.py calls get_active_session() first, so it picks up this session.
from snowflake.snowpark import Session
Session.builder.config("connection_name", "IEVOOOP-FS85291").config("database", "SC_ONTOLOGY") \
    .config("schema", "APP").config("warehouse", "SC_WH").create()
at = AppTest.from_file(APP, default_timeout=300)
at.run()
print(f"first render: {time.time()-t0:.1f}s, tabs={[t.label for t in at.tabs]}")
print("errors on load:", errors(at) or "none")
md = all_md(at)
for label, pat in [("canonical OTD hero", r"ct-cn-num\">([\d.]+)%"),
                   ("KPI values", r"ct-kpi-v\">([\d.]+)"),
                   ("tests chip", r"(\d+/\d+) tests passing")]:
    print(f"  {label}: {re.findall(pat, md)}")
print("  in-transit caption:", next((c.value for c in at.caption if "in transit" in c.value), "-"))

t1 = time.time(); at.run()
print(f"cached rerun: {time.time()-t1:.1f}s")

# Create corrective action for the selected risk-zone supplier
print("\nbefore create:", ca_rows(at))
next(b for b in at.button if b.key == "ca_btn").click().run()
print("after create: ", ca_rows(at), "| msg:", [s.value for s in at.success] + [w.value for w in at.warning])
next(b for b in at.button if b.key == "ca_btn").click().run()
print("create again: ", ca_rows(at), "| msg:", [w.value for w in at.warning])
next(b for b in at.button if b.key == "ca_reset").click().run()
print("after reset:  ", ca_rows(at), "| msg:", [i.value for i in at.info if "Reset" in i.value])
print("errors after CA actions:", errors(at) or "none")

# Run tests now
before_run = next((m.value for m in at.metric if m.label == "Last run"), None)
next(b for b in at.button if b.key == "trust_go").click().run()
after_run = next((m.value for m in at.metric if m.label == "Last run"), None)
print(f"\nTrust 'Last run': {before_run} -> {after_run} | msg: {[s.value for s in at.success if 'passed' in s.value]}")
print("tests chip after run:", re.findall(r"(\d+/\d+) tests passing", all_md(at)))
print("errors after Run tests:", errors(at) or "none")
