"""ChainTruth — One supply chain. One definition. One answer."""
import json, time, traceback, re, hashlib, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import answer_cache as AC
import pandas as pd
import streamlit as st

try:
    from snowflake.snowpark.context import get_active_session
    session = get_active_session()
except Exception:
    session = st.connection("snowflake").session()

SV = "SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN"
SEARCH = "SC_ONTOLOGY.ONTOLOGY.CONTRACT_SEARCH"
AGENT = "SC_ONTOLOGY.APP.SUPPLY_CHAIN_AGENT"

# ---------------------------------------------------------------------------
# CSS design system
# ---------------------------------------------------------------------------
st.set_page_config(page_title="ChainTruth", layout="wide")
st.markdown("""<style>
:root{--ink:#1a1d21;--surface:#faf9f7;--card:#fff;--teal:#0d7377;--teal-bg:#e6f5f5;
  --orange:#c2410c;--orange-bg:#fff3eb;--muted:#71717a;--border:#e4e4e7;
  --green:#15803d;--green-bg:#e8f5e9;--red:#b91c1c;--red-bg:#fde8e8;}
@media(prefers-color-scheme:dark){:root{--ink:#e4e4e7;--surface:#18181b;--card:#27272a;
  --teal:#5eead4;--teal-bg:#042f2e;--orange:#fb923c;--orange-bg:#431407;--muted:#a1a1aa;
  --border:#3f3f46;--green:#4ade80;--green-bg:#052e16;--red:#f87171;--red-bg:#450a0a;}}

/* kill Streamlit chrome + top gap */
header[data-testid="stHeader"]{display:none!important;}
[data-testid="stAppViewBlockContainer"]{padding-top:0!important;}
[data-testid="stMainBlockContainer"]{padding-top:0!important;}
.block-container{padding-top:0.4rem!important;margin-top:0!important;}
section.main>div{padding-top:0!important;margin-top:-1rem!important;}

.ct-hdr{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;
  padding:8px 0 6px;margin-bottom:2px;border-bottom:1px solid var(--border);}
.ct-hdr-l{display:flex;flex-direction:column;gap:0;justify-content:center;padding-bottom:10px;}
.ct-brand{font-family:Georgia,'Iowan Old Style','Palatino Linotype',Cambria,serif;
  font-size:2.2rem;font-weight:600;letter-spacing:-.01em;line-height:1;color:var(--ink);}
.ct-tag{font-size:.8rem;letter-spacing:.06em;color:var(--muted);margin-top:2px;}
.ct-chips{display:flex;gap:6px;flex-wrap:nowrap;align-items:center;}
.ct-chip{font-size:.7rem;font-weight:600;letter-spacing:.04em;text-transform:uppercase;
  padding:2px 9px;border-radius:4px;border:1px solid var(--border);color:var(--muted);
  font-variant-numeric:tabular-nums;}
.ct-chip-ok{border-color:var(--teal);color:var(--teal);background:var(--teal-bg);}
.ct-sl{font-size:.7rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  color:var(--muted);margin:14px 0 8px;}
.ct-cf-row{display:flex;gap:28px;flex-wrap:wrap;align-items:flex-start;margin-bottom:18px;}
.ct-cf-item{flex:1;min-width:130px;}
.ct-cf-num{font-size:2.5rem;font-weight:700;letter-spacing:-.03em;
  font-variant-numeric:tabular-nums;color:var(--orange);line-height:1;}
.ct-cf-lbl{font-size:.76rem;color:var(--muted);margin-top:3px;line-height:1.25;}
.ct-cn-block{display:flex;align-items:baseline;gap:14px;padding:12px 0;border-top:2px solid var(--teal);}
.ct-cn-num{font-size:3.2rem;font-weight:800;letter-spacing:-.03em;
  font-variant-numeric:tabular-nums;color:var(--teal);line-height:1;}
.ct-cn-meta{font-size:.8rem;color:var(--muted);} .ct-cn-meta strong{color:var(--teal);}
.ct-spread{display:inline-block;font-size:.76rem;font-weight:700;color:var(--orange);
  background:var(--orange-bg);padding:2px 9px;border-radius:4px;margin-top:6px;}
.ct-kpis{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0;}
.ct-kpi{flex:1;min-width:140px;padding:14px 16px;border:1px solid var(--border);
  border-radius:6px;background:var(--card);}
.ct-kpi-l{font-size:.66rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  color:var(--muted);margin-bottom:3px;}
.ct-kpi-v{font-size:1.9rem;font-weight:700;letter-spacing:-.02em;
  font-variant-numeric:tabular-nums;color:var(--ink);line-height:1.1;}
.ct-kpi-u{font-size:.8rem;color:var(--muted);font-weight:400;}
.ct-rtbl{width:100%;border-collapse:collapse;font-size:.83rem;margin:6px 0;}
.ct-rtbl th{text-align:left;font-size:.66rem;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;color:var(--muted);padding:5px 8px;border-bottom:2px solid var(--border);}
.ct-rtbl td{padding:7px 8px;border-bottom:1px solid var(--border);color:var(--ink);
  font-variant-numeric:tabular-nums;} .ct-rw{color:var(--orange);font-weight:700;}
.ct-badge{display:inline-block;font-size:.7rem;font-weight:700;letter-spacing:.04em;
  text-transform:uppercase;padding:3px 9px;border-radius:4px;margin:3px 4px 3px 0;}
.ct-b-gov{background:var(--teal-bg);color:var(--teal);}
.ct-b-res{background:var(--orange-bg);color:var(--orange);}
.ct-b-ref{background:var(--red-bg);color:var(--red);}
.ct-defn{border-left:3px solid var(--teal);padding:5px 11px;margin:5px 0;
  background:var(--teal-bg);font-size:.83rem;color:var(--ink);border-radius:0 4px 4px 0;}
.ct-doc{border-left:3px solid var(--muted);padding:5px 11px;margin:5px 0;
  font-size:.82rem;color:var(--ink);border-radius:0 4px 4px 0;}
.ct-doc-id{font-weight:700;color:var(--teal);}
.ct-per{border:1px solid var(--border);border-radius:6px;padding:14px 16px;
  background:var(--card);text-align:center;}
.ct-per-n{font-size:.66rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  color:var(--muted);margin-bottom:6px;}
.ct-per-q{font-size:.83rem;color:var(--ink);font-style:italic;margin-bottom:10px;}
.ct-per-v{font-size:2.2rem;font-weight:800;letter-spacing:-.03em;
  font-variant-numeric:tabular-nums;color:var(--teal);line-height:1;}
.ct-per-v.ct-null{color:var(--muted);}
.ct-pill{display:inline-block;font-size:.76rem;font-weight:700;padding:3px 12px;
  border-radius:4px;margin:6px 0;}
.ct-pill-ok{background:var(--green-bg);color:var(--green);}
.ct-pill-bad{background:var(--red-bg);color:var(--red);}
.ct-gg{width:100%;border-collapse:collapse;font-size:.83rem;}
.ct-gg th{font-size:.66rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
  color:var(--muted);padding:7px 10px;border-bottom:2px solid var(--border);text-align:center;}
.ct-gg th:first-child{text-align:left;}
.ct-gg td{padding:7px 10px;border-bottom:1px solid var(--border);text-align:center;
  font-variant-numeric:tabular-nums;color:var(--ink);}
.ct-gg td:first-child{text-align:left;font-weight:600;}
.ct-masked{color:var(--orange);font-weight:700;font-size:.76rem;letter-spacing:.04em;text-transform:uppercase;}
.ct-tc{display:inline-block;width:16px;height:16px;border-radius:3px;margin:2px;}
.ct-tp{background:var(--green);} .ct-tf{background:var(--red);}
.ct-err{border:1px solid var(--border);border-radius:6px;padding:12px 16px;margin:6px 0;
  background:var(--orange-bg);font-size:.85rem;color:var(--orange);}
.ct-tl{font-size:.78rem;color:var(--muted);margin:6px 0;font-variant-numeric:tabular-nums;}
.ct-tl b{color:var(--teal);}
.ct-glos{width:100%;border-collapse:collapse;font-size:.83rem;}
.ct-glos th{text-align:left;font-size:.66rem;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;color:var(--muted);padding:6px 10px;border-bottom:2px solid var(--border);}
.ct-glos td{padding:8px 10px;border-bottom:1px solid var(--border);color:var(--ink);
  vertical-align:top;line-height:1.35;}
.ct-glos-legacy{font-size:.78rem;color:var(--orange);}
.ct-fn{font-size:.72rem;color:var(--muted);font-style:italic;margin-top:4px;}
.ct-echo{border:1px solid var(--border);border-radius:6px;padding:10px 14px;margin:8px 0;
  background:var(--card);font-size:.85rem;}
.ct-echo-q{font-weight:600;color:var(--ink);} .ct-echo-t{font-size:.72rem;color:var(--muted);margin-top:2px;}
.ct-hl{display:flex;gap:12px;flex-wrap:wrap;margin:8px 0;padding:10px 14px;
  border:1px solid var(--border);border-radius:6px;background:var(--teal-bg);font-size:.82rem;}
.ct-hl-item{flex:1;min-width:140px;} .ct-hl-label{font-size:.66rem;font-weight:700;
  letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:2px;}
.ct-hl-val{font-weight:700;color:var(--ink);font-variant-numeric:tabular-nums;}
.ct-hl-note{font-size:.68rem;color:var(--muted);font-style:italic;margin-top:2px;}
.ct-restbl{width:100%;border-collapse:collapse;font-size:.83rem;margin:6px 0;}
.ct-restbl th{text-align:left;font-size:.66rem;font-weight:700;letter-spacing:.06em;
  text-transform:uppercase;color:var(--muted);padding:5px 8px;border-bottom:2px solid var(--border);}
.ct-restbl td{padding:7px 8px;border-bottom:1px solid var(--border);color:var(--ink);
  font-variant-numeric:tabular-nums;}
.ct-restbl td.num{text-align:right;}
.ct-formula-ok{font-size:.8rem;color:var(--green);font-weight:600;}
.ct-formula-warn{font-size:.8rem;color:var(--orange);font-weight:600;}
.ct-formula-na{font-size:.8rem;color:var(--muted);}
.ct-wf{position:relative;height:220px;display:flex;gap:4px;margin:10px 0 6px;}
.ct-wf-bar{flex:1;position:relative;min-width:0;}
.ct-wf-rect{position:absolute;left:10%;width:80%;border-radius:3px 3px 0 0;}
.ct-wf-val{position:absolute;width:100%;text-align:center;font-size:.72rem;font-weight:700;font-variant-numeric:tabular-nums;}
.ct-wf-lbl{position:absolute;bottom:0;width:100%;text-align:center;font-size:.66rem;color:var(--muted);line-height:1.2;}
.ct-wf-up{background:var(--teal);} .ct-wf-down{background:var(--orange);}
.ct-wf-start{background:var(--border);} .ct-wf-end{background:var(--teal);}
.ct-rcpt{border:1px solid var(--border);border-radius:6px;padding:12px 16px;margin:10px 0;
  background:var(--card);font-size:.82rem;color:var(--ink);}
.ct-rcpt-row{display:flex;gap:18px;flex-wrap:wrap;padding:3px 0;border-bottom:1px solid var(--border);}
.ct-rcpt-row:last-child{border-bottom:none;}
.ct-rcpt-k{font-size:.66rem;font-weight:700;letter-spacing:.06em;text-transform:uppercase;
  color:var(--muted);min-width:120px;}
.ct-rcpt-v{font-variant-numeric:tabular-nums;flex:1;}
</style>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@st.cache_data(ttl=1800, show_spinner=False)
def q(sql):
    return session.sql(sql).to_pandas()

def run_nocache(sql):
    return session.sql(sql).to_pandas()

@st.cache_data(ttl=1800, show_spinner=False)
def search_preview(supplier_id, query, limit):
    """Contract clauses for one supplier via SEARCH_PREVIEW, cached per (supplier, query, limit)."""
    payload = json.dumps({"query": query,
        "columns": ["doc_id","doc_type","supplier_name","doc_text","expiry_date"],
        "filter": {"@eq": {"supplier_id": supplier_id}}, "limit": limit}).replace("'","''")
    raw = session.sql(f"SELECT SNOWFLAKE.CORTEX.SEARCH_PREVIEW('{SEARCH}','{payload}') AS r").to_pandas().iloc[0]["R"]
    return json.loads(raw).get("results", [])

def safe_select(sql):
    s = sql.strip().lower()
    banned = ("insert","update","delete","drop","alter","create","grant","truncate","merge","call")
    return s.startswith(("select","with")) and not any(b+" " in s for b in banned)

def safe_section(label):
    class _Ctx:
        def __enter__(self): return self
        def __exit__(self, et, ev, tb):
            if et is None:
                return False
            # re-raise Streamlit control-flow exceptions (RerunException, StopException)
            name = type(ev).__name__
            if "Rerun" in name or "Stop" in name or "RerunData" in name:
                return False  # propagate
            st.markdown(f'<div class="ct-err">Could not load {label}.</div>', unsafe_allow_html=True)
            with st.expander("Diagnostic"):
                st.code(traceback.format_exc(), language="text")
            return True
    return _Ctx()

MASKED_COLS = {"UNIT_COST","LINE_VALUE","LANDED_COST","AVG_LANDED_COST_PER_UNIT","TOTAL_LANDED_COST"}

def ask_agent(question):
    escaped = question.replace("\\","\\\\").replace("'","\\'").replace('"','\\"')
    sql = (f"SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN('{AGENT}',"
           f"'{{\"messages\":[{{\"role\":\"user\",\"content\":[{{\"type\":\"text\",\"text\":\"{escaped}\"}}]}}]}}',"
           f"TRUE) AS resp")
    raw = run_nocache(sql).iloc[0]["RESP"]
    return json.loads(raw)

def parse_agent_response(resp):
    content = resp.get("content",[])
    texts, tools_used, tool_steps, sql_stmts, search_results = [], [], [], [], []
    for item in content:
        t = item.get("type","")
        if t=="text" and item.get("text","").strip():
            texts.append(item["text"].strip())
        elif t=="tool_use":
            tu = item.get("tool_use",{})
            name = tu.get("name","")
            if name and name != "system_execute_sql":
                tools_used.append(name)
                tool_steps.append(name)
        elif t=="tool_result":
            tr = item.get("tool_result",{})
            name = tr.get("name","")
            if name=="system_execute_sql":
                for ci in tr.get("content",[]):
                    j = ci.get("json",{})
                    if "sql" in j:
                        sql_stmts.append(j["sql"])
            elif name=="ContractSearch":
                for ci in tr.get("content",[]):
                    j = ci.get("json",{})
                    # agent returns search_results (not results), with text (not doc_text) and id (not doc_id)
                    sr = j.get("results", j.get("search_results", []))
                    if isinstance(sr,list):
                        for hit in sr:
                            normalized = {
                                "doc_id": hit.get("doc_id", ""),
                                "doc_text": hit.get("doc_text", hit.get("text", "")),
                                "doc_type": hit.get("doc_type", ""),
                                "supplier_name": hit.get("supplier_name", ""),
                                "expiry_date": hit.get("expiry_date", ""),
                            }
                            search_results.append(normalized)
    return {"texts":texts, "tools":set(tools_used), "tool_steps":tool_steps,
            "sql":sql_stmts[-1] if sql_stmts else None, "search_results":search_results}

# Leading sentences that narrate the agent's plan, rules or tool choice (display only;
# the Proof panel keeps the full text).
_NARRATION = re.compile(
    r"\brules?\b|\binstructions?\b|\bI'll\b|\bI will\b|\blet me\b|\bI need to\b|"
    r"\bSupplyChainAnalyst\b|\bContractSearch\b|\b(call|calling|use|using|query|querying|search|searching)\s+(the\s+)?(tool|analyst|search)",
    re.IGNORECASE)
_SENT = re.compile(r"^(.*?[.!?:])(\s+|$)", re.DOTALL)
def strip_narration(text):
    t = text.lstrip()
    while t:
        first_line, _, rest_lines = t.partition("\n")
        m = _SENT.match(first_line)
        sent = m.group(1) if m else first_line
        if not _NARRATION.search(sent):
            break
        remainder = first_line[len(m.group(0)):] if m else ""
        t = (remainder + ("\n" + rest_lines if rest_lines else "")).lstrip()
    return t

def compute_badge(parsed, result_df=None):
    has_analyst = "SupplyChainAnalyst" in parsed["tools"]
    has_search = "ContractSearch" in parsed["tools"]
    gen_sql = parsed["sql"]
    is_refusal = not gen_sql and not has_search
    if is_refusal:
        return "ref", "Not defined: refused"
    has_masked = False
    if result_df is not None and not result_df.empty:
        for c in result_df.columns:
            if c.upper() in MASKED_COLS and result_df[c].isna().any():
                has_masked = True
                break
    if has_masked:
        return "res", "Restricted for your role"
    if has_analyst and has_search:
        return "gov", "Governed metric + contract evidence"
    if has_analyst:
        return "gov", "Governed metric"
    if has_search:
        return "gov", "Contract search"
    return "gov", "Governed metric"

def build_timeline(parsed, elapsed):
    steps = []
    step_num = 0
    search_count = sum(1 for t in parsed["tool_steps"] if t=="ContractSearch")
    for t in parsed["tool_steps"]:
        step_num += 1
        if t == "SupplyChainAnalyst":
            steps.append(f"<b>{step_num}</b> Governed metrics queried (SupplyChainAnalyst)")
        elif t == "ContractSearch" and search_count > 0:
            steps.append(f"<b>{step_num}</b> Contracts searched for {search_count} supplier{'s' if search_count>1 else ''} (ContractSearch)")
            search_count = 0  # only show once
    if steps:
        step_num += 1
        steps.append(f"<b>{step_num}</b> Answer composed")
    trail = " → ".join(steps)
    return f'<div class="ct-tl">{trail} · {elapsed:.1f}s</div>' if trail else ""

def extract_otd_from_agent(resp):
    content = resp.get("content",[])
    for item in content:
        if item.get("type")=="tool_result":
            tr = item.get("tool_result",{})
            if tr.get("name")=="system_execute_sql":
                for ci in tr.get("content",[]):
                    j = ci.get("json",{})
                    rs = j.get("result_set",{})
                    data = rs.get("data",[])
                    meta = rs.get("resultSetMetaData",{}).get("rowType",[])
                    if data and meta:
                        for idx, col in enumerate(meta):
                            if "otd" in col.get("name","").lower():
                                try: return float(data[0][idx])
                                except: pass
                        try: return float(data[0][0])
                        except: pass
    return None

def fetch_contract_evidence(supplier_ids, limit_per=2):
    results = []
    seen_doc_ids = set()
    for sid in supplier_ids[:3]:
        try:
            for hit in search_preview(sid, "late delivery penalty SLA expiry", limit_per):
                did = hit.get("doc_id","")
                if did and did not in seen_doc_ids:
                    seen_doc_ids.add(did)
                    results.append(hit)
        except Exception:
            pass
    return results

def normalize_formula(s):
    return re.sub(r'\s+','',s.lower().replace('order_lines.','').replace('inventory.',''))

def check_formula(gen_sql, ont_metrics):
    if not gen_sql: return []
    results = []
    sql_norm = normalize_formula(gen_sql)
    for _,m in ont_metrics.iterrows():
        mn = m["METRIC_NAME"]
        if mn in gen_sql.lower() or mn.replace("_","") in gen_sql.lower().replace("_",""):
            expected = normalize_formula(m.get("FORMULA_SQL","") or "")
            if not expected:
                results.append((m["DISPLAY_NAME"],"na","Not checked"))
            elif expected in sql_norm or sql_norm.find(expected)>=0:
                results.append((m["DISPLAY_NAME"],"ok","Formula matches canonical definition"))
            else:
                results.append((m["DISPLAY_NAME"],"warn","Formula differs: review"))
    return results

# ---------------------------------------------------------------------------
# SQL catalog
# ---------------------------------------------------------------------------
SQL = {
  "header_metrics":"SELECT COUNT(*) AS n FROM SC_ONTOLOGY.ONTOLOGY.ONT_METRIC",
  "header_tests":"""SELECT COUNT(*) AS total, COUNT_IF(passed) AS passed, MAX(run_ts) AS last_run
      FROM SC_ONTOLOGY.GOVERNANCE.CONSISTENCY_RESULTS
      WHERE run_id=(SELECT run_id FROM SC_ONTOLOGY.GOVERNANCE.CONSISTENCY_RESULTS ORDER BY run_ts DESC LIMIT 1)""",
  "header_role":"SELECT CURRENT_ROLE() AS r",
  "hero_legacy":"SELECT team_definition, otd_pct FROM SC_ONTOLOGY.CURATED.VW_LEGACY_OTD_BY_TEAM",
  "kpi_main":"""SELECT otd_pct, fill_rate_pct, in_full_pct
      FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN
           METRICS order_lines.otd_pct, order_lines.fill_rate_pct, order_lines.in_full_pct)""",
  "kpi_doi":"SELECT days_of_inventory FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN METRICS inventory.days_of_inventory)",
  "trend":"""SELECT delivery_month, otd_pct, line_count
      FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN
           DIMENSIONS order_lines.delivery_month METRICS order_lines.otd_pct, order_lines.line_count)
      ORDER BY delivery_month""",
  "worst":"""SELECT o.SUPPLIER_NAME, o.SUPPLIER_ID, o.OTD_PCT, o.LINE_COUNT,
         d.contract_expiry_date, d.days_to_contract_expiry
  FROM (SELECT SUPPLIER_NAME, SUPPLIER_ID, OTD_PCT, LINE_COUNT
        FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN
             DIMENSIONS suppliers.supplier_name, suppliers.supplier_id
             METRICS order_lines.otd_pct, order_lines.line_count)
        ORDER BY OTD_PCT ASC LIMIT 5) o
  JOIN SC_ONTOLOGY.CURATED.DIM_SUPPLIER d ON d.supplier_id = o.SUPPLIER_ID
  ORDER BY o.OTD_PCT ASC""",
  "ont_rel":"SELECT from_entity, relationship, to_entity FROM SC_ONTOLOGY.ONTOLOGY.ONT_RELATIONSHIP",
  "ont_metric_full":"""SELECT display_name, canonical_definition, legacy_variants, owner_persona, sensitivity
      FROM SC_ONTOLOGY.ONTOLOGY.ONT_METRIC ORDER BY display_name""",
  "ont_metric_all":"SELECT metric_name, display_name, canonical_definition FROM SC_ONTOLOGY.ONTOLOGY.ONT_METRIC",
  "ont_metric_formulas":"SELECT metric_name, display_name, canonical_definition, formula_sql FROM SC_ONTOLOGY.ONTOLOGY.ONT_METRIC",
  "canonical_otd":"SELECT otd_pct FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN METRICS order_lines.otd_pct)",
  "gov_snap":"""SELECT captured_at, role_name, metric_name, metric_value, is_masked
      FROM SC_ONTOLOGY.GOVERNANCE.ROLE_VISIBILITY_SNAPSHOT ORDER BY metric_name, role_name""",
  "trust_results":"""SELECT run_id, run_ts, test_name, metric, ROUND(semantic_value,6) AS semantic_value,
      ROUND(golden_value,6) AS golden_value, passed
      FROM SC_ONTOLOGY.GOVERNANCE.CONSISTENCY_RESULTS
      WHERE run_id=(SELECT run_id FROM SC_ONTOLOGY.GOVERNANCE.CONSISTENCY_RESULTS ORDER BY run_ts DESC LIMIT 1)
      ORDER BY test_name, metric""",
  "alerts":"""SELECT alert_ts, alert_type, supplier_id, order_id, detail, ticket_status
      FROM SC_ONTOLOGY.GOVERNANCE.ALERTS ORDER BY alert_ts DESC LIMIT 50""",
  "in_transit":"""SELECT COUNT(*) AS n FROM SC_ONTOLOGY.CURATED.DT_ORDER_LINE
      WHERE delivered_date > CURRENT_DATE()""",
  # One round trip for the header + Overview KPIs: replaces kpi_main, kpi_doi, in_transit,
  # canonical_otd, data_freshness and header_tests (same expressions, same values).
  "ov_core":"""SELECT k.otd_pct, k.fill_rate_pct, k.in_full_pct,
      (SELECT days_of_inventory FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN METRICS inventory.days_of_inventory)) AS days_of_inventory,
      (SELECT COUNT(*) FROM SC_ONTOLOGY.CURATED.DT_ORDER_LINE WHERE delivered_date > CURRENT_DATE()) AS n_transit,
      (SELECT MAX(delivered_date) FROM SC_ONTOLOGY.CURATED.FACT_ORDER_LINE) AS latest,
      t.total, t.passed, t.last_run
    FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN
           METRICS order_lines.otd_pct, order_lines.fill_rate_pct, order_lines.in_full_pct) k,
         (SELECT COUNT(*) AS total, COUNT_IF(passed) AS passed, MAX(run_ts) AS last_run
            FROM SC_ONTOLOGY.GOVERNANCE.CONSISTENCY_RESULTS
            WHERE run_id=(SELECT run_id FROM SC_ONTOLOGY.GOVERNANCE.CONSISTENCY_RESULTS ORDER BY run_ts DESC LIMIT 1)) t""",
  "bridge_planning":"""SELECT
      ROUND(100*AVG(IFF(e.goods_issue_date <= e.requested_date,1,0)),4) AS step0,
      ROUND(100*AVG(IFF(l.carrier_delivered_ts::DATE <= e.requested_date,1,0)),4) AS step1,
      ROUND(100*AVG(IFF(l.carrier_delivered_ts::DATE <= e.promised_date,1,0)),4) AS step2
    FROM SC_ONTOLOGY.RAW.ERP_ORDER_LINES e
    JOIN SC_ONTOLOGY.RAW.LOGISTICS_SHIPMENTS l ON l.order_id=e.order_id AND l.line_no=e.line_no
    WHERE l.carrier_delivered_ts::DATE<=CURRENT_DATE()""",
  "bridge_procurement":"""SELECT
      ROUND(100*AVG(IFF(e.supplier_dispatch_date <= e.supplier_committed_date,1,0)),4) AS step0,
      ROUND(100*AVG(IFF(e.supplier_dispatch_date <= e.promised_date,1,0)),4) AS step1,
      ROUND(100*AVG(IFF(l.carrier_delivered_ts::DATE <= e.promised_date,1,0)),4) AS step2
    FROM SC_ONTOLOGY.RAW.ERP_ORDER_LINES e
    JOIN SC_ONTOLOGY.RAW.LOGISTICS_SHIPMENTS l ON l.order_id=e.order_id AND l.line_no=e.line_no
    WHERE l.carrier_delivered_ts::DATE<=CURRENT_DATE()""",
  "bridge_logistics":"""SELECT
      ROUND(100*AVG(IFF(l.carrier_delivered_ts::DATE <= l.carrier_eta_date,1,0)),4) AS step0,
      ROUND(100*AVG(IFF(l.carrier_delivered_ts::DATE <= e.promised_date,1,0)),4) AS step1
    FROM SC_ONTOLOGY.RAW.ERP_ORDER_LINES e
    JOIN SC_ONTOLOGY.RAW.LOGISTICS_SHIPMENTS l ON l.order_id=e.order_id AND l.line_no=e.line_no
    WHERE l.carrier_delivered_ts::DATE<=CURRENT_DATE()""",
  "scatter_suppliers":"""SELECT o.SUPPLIER_NAME, o.SUPPLIER_ID, o.OTD_PCT, o.LINE_COUNT,
      d.days_to_contract_expiry
    FROM (SELECT SUPPLIER_NAME, SUPPLIER_ID, OTD_PCT, LINE_COUNT
          FROM SEMANTIC_VIEW(SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN
               DIMENSIONS suppliers.supplier_name, suppliers.supplier_id
               METRICS order_lines.otd_pct, order_lines.line_count)) o
    JOIN SC_ONTOLOGY.CURATED.DIM_SUPPLIER d ON d.supplier_id = o.SUPPLIER_ID""",
  "data_freshness":"SELECT MAX(delivered_date) AS latest FROM SC_ONTOLOGY.CURATED.FACT_ORDER_LINE",
  "corrective_actions":"""SELECT action_id, supplier_id, supplier_name, ROUND(otd_pct,1) AS otd_pct,
      contract_expiry, status, created_at
    FROM SC_ONTOLOGY.GOVERNANCE.CORRECTIVE_ACTIONS ORDER BY created_at DESC""",
  "lineage_metrics":"""SELECT metric_name, display_name, formula_sql, owner_persona
    FROM SC_ONTOLOGY.ONTOLOGY.ONT_METRIC ORDER BY display_name""",
  "lineage_entities":"""SELECT entity, source_object FROM SC_ONTOLOGY.ONTOLOGY.ONT_ENTITY ORDER BY entity""",
}

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
with safe_section("header"):
    st.markdown('<div class="ct-hdr-l"><span class="ct-brand">ChainTruth</span>'
                '<span class="ct-tag">One supply chain. One definition. One answer.</span></div>',
                unsafe_allow_html=True)
    st.markdown('<div style="border-bottom:1px solid var(--border);margin:-8px 0 2px;"></div>', unsafe_allow_html=True)

tabs = st.tabs(["Overview","Ask","Personas","Governance","Ontology","Trust"])

# ===== TAB 1: OVERVIEW =====
with tabs[0]:
    with safe_section("hero"):
        legacy = q(SQL["hero_legacy"])
        nc = legacy[~legacy["TEAM_DEFINITION"].str.startswith("CANONICAL")]
        cr = legacy[legacy["TEAM_DEFINITION"].str.startswith("CANONICAL")]
        cv = float(cr.iloc[0]["OTD_PCT"]) if not cr.empty else 0
        spread = float(nc["OTD_PCT"].max() - nc["OTD_PCT"].min())
        labels={"Planning":"ERP goods issue vs requested date","Procurement":"Supplier dispatch vs committed date","Logistics":"Carrier delivered vs carrier ETA"}
        items=""
        for _,r in nc.iterrows():
            short=r["TEAM_DEFINITION"].split("(")[0].strip()
            items+=f'<div class="ct-cf-item"><div class="ct-cf-num">{r["OTD_PCT"]:.1f}%</div><div class="ct-cf-lbl"><strong>{short}</strong><br>{labels.get(short,"")}</div></div>'
        st.markdown(f'<div class="ct-sl">The problem: three teams, three numbers</div>'
            f'<div class="ct-cf-row">{items}</div>'
            f'<div class="ct-cn-block"><div class="ct-cn-num">{cv:.1f}%</div>'
            f'<div class="ct-cn-meta"><strong>Canonical OTD</strong><br>Delivered (carrier proof of delivery) on or before the date promised to the customer.</div></div>'
            f'<div class="ct-spread">{spread:.1f}-point spread replaced by one governed definition</div>', unsafe_allow_html=True)

    with safe_section("KPI cards"):
        kpis=q(SQL["ov_core"]); doi=kpis
        def fv(df,col,fmt=".1f"): return f"{df.iloc[0][col]:{fmt}}" if not df.empty and pd.notna(df.iloc[0][col]) else "—"
        st.markdown(f'<div class="ct-kpis">'
            f'<div class="ct-kpi"><div class="ct-kpi-l">On-time delivery</div><div class="ct-kpi-v">{fv(kpis,"OTD_PCT")}<span class="ct-kpi-u">%</span></div></div>'
            f'<div class="ct-kpi"><div class="ct-kpi-l">Fill rate</div><div class="ct-kpi-v">{fv(kpis,"FILL_RATE_PCT")}<span class="ct-kpi-u">%</span></div></div>'
            f'<div class="ct-kpi"><div class="ct-kpi-l">In-full</div><div class="ct-kpi-v">{fv(kpis,"IN_FULL_PCT")}<span class="ct-kpi-u">%</span></div></div>'
            f'<div class="ct-kpi"><div class="ct-kpi-l">Days of inventory</div><div class="ct-kpi-v">{fv(doi,"DAYS_OF_INVENTORY")}<span class="ct-kpi-u"> days</span></div></div>'
            f'</div>', unsafe_allow_html=True)

    with safe_section("in-transit note"):
        itr = q(SQL["ov_core"])
        n_transit = int(itr.iloc[0]["N_TRANSIT"]) if not itr.empty else 0
        if n_transit > 0:
            st.caption(f"{n_transit:,} order lines still in transit (future delivery date), excluded from all delivery-performance metrics above.")

    c_left, c_right = st.columns([3,2])
    with c_left:
        with safe_section("OTD trend"):
            st.markdown('<div class="ct-sl">OTD trend by delivery month</div>', unsafe_allow_html=True)
            trend = q(SQL["trend"])
            if not trend.empty:
                import altair as alt
                trend["DELIVERY_MONTH"] = pd.to_datetime(trend["DELIVERY_MONTH"])
                chart = alt.Chart(trend).mark_line(color="#0d7377", strokeWidth=2, point=alt.OverlayMarkDef(color="#0d7377",size=40)).encode(
                    x=alt.X("yearmonth(DELIVERY_MONTH):O", title="Month", axis=alt.Axis(format="%b", labelAngle=0)),
                    y=alt.Y("OTD_PCT:Q", title="OTD %", scale=alt.Scale(domain=[0,100]),
                            axis=alt.Axis(grid=True, gridColor="#e4e4e7", gridOpacity=0.6)),
                    tooltip=[alt.Tooltip("yearmonth(DELIVERY_MONTH):O",title="Month"),
                             alt.Tooltip("OTD_PCT:Q",title="OTD %",format=".1f"),
                             alt.Tooltip("LINE_COUNT:Q",title="Lines")]
                ).properties(height=250).configure_view(strokeWidth=0)
                st.altair_chart(chart, use_container_width=True)
                st.markdown('<div class="ct-fn">First and last months are partial.</div>', unsafe_allow_html=True)

    with c_right:
        with safe_section("worst suppliers"):
            st.markdown('<div class="ct-sl">Worst suppliers + contract risk</div>', unsafe_allow_html=True)
            worst=q(SQL["worst"])
            if not worst.empty:
                rows_html=""
                for _,r in worst.iterrows():
                    exp=int(r["DAYS_TO_CONTRACT_EXPIRY"]) if pd.notna(r["DAYS_TO_CONTRACT_EXPIRY"]) else 999
                    cls=' class="ct-rw"' if exp<=90 else ""
                    exp_txt=f"{exp}d" if exp<999 else "—"
                    rows_html+=f'<tr><td>{r["SUPPLIER_NAME"]}</td><td>{r["OTD_PCT"]:.1f}%</td><td{cls}>{exp_txt}</td></tr>'
                st.markdown(f'<table class="ct-rtbl"><tr><th>Supplier</th><th>OTD</th><th>Contract</th></tr>{rows_html}</table>', unsafe_allow_html=True)

    # --- Reconciliation Bridge ---
    with safe_section("bridge"):
        st.markdown('<div class="ct-sl">Reconciliation bridge</div>', unsafe_allow_html=True)
        BRIDGE_META = {
            "Planning": {
                "key": "bridge_planning",
                "steps": [
                    ("Start", "ERP goods-issue ≤ requested date"),
                    ("Hypothetical", "Swap timing: use carrier delivery date instead of goods-issue date"),
                    ("Canonical", "Swap target: use promised date instead of requested date"),
                ],
            },
            "Procurement": {
                "key": "bridge_procurement",
                "steps": [
                    ("Start", "Supplier dispatch ≤ supplier committed date"),
                    ("Hypothetical", "Swap target: use promised date instead of supplier committed date"),
                    ("Canonical", "Swap timing: use carrier delivery date instead of supplier dispatch"),
                ],
            },
            "Logistics": {
                "key": "bridge_logistics",
                "steps": [
                    ("Start", "Carrier delivered ≤ carrier ETA"),
                    ("Canonical", "Swap target: use promised date instead of carrier ETA"),
                ],
            },
        }
        bridge_persona = st.selectbox("Starting definition", list(BRIDGE_META.keys()), key="bridge_sel")
        bm = BRIDGE_META[bridge_persona]
        bdata = q(SQL[bm["key"]])
        if not bdata.empty:
            raw_vals = [float(bdata.iloc[0][c]) for c in bdata.columns]
            step_labels = bm["steps"]
            # largest-remainder rounding: fix start and final, round deltas so they sum exactly
            import math
            disp_start = round(raw_vals[0], 1)
            disp_final = round(raw_vals[-1], 1)
            disp_gap = round(disp_final - disp_start, 1)
            raw_deltas = [raw_vals[i] - raw_vals[i-1] for i in range(1, len(raw_vals))]
            floored = [math.floor(d * 10) / 10 for d in raw_deltas]
            remainders = [round(d * 10 - math.floor(d * 10), 6) for d in raw_deltas]
            residual = round((disp_gap - sum(floored)) * 10)
            indices = sorted(range(len(remainders)), key=lambda k: -remainders[k])
            disp_deltas = list(floored)
            for j in range(max(0, int(residual))):
                disp_deltas[indices[j]] = round(disp_deltas[indices[j]] + 0.1, 1)
            # running totals for bar heights
            running = [disp_start]
            for d in disp_deltas:
                running.append(round(running[-1] + d, 1))
            # build waterfall bars — absolute pixel positions inside a 220px container
            chart_h = 190  # pixel budget for bars (leave room for labels)
            pad_top = 20   # space for value labels above bars
            lo = min(running) - 3; hi = max(running) + 3
            span = hi - lo if hi != lo else 1
            def _y(v): return pad_top + int((hi - v) / span * chart_h)
            bars_html = ""
            for i, v in enumerate(running):
                if i == 0:
                    # start bar: bottom of chart up to value
                    top_px = _y(v); bot_px = _y(lo)
                    h_px = max(bot_px - top_px, 4)
                    cls = "ct-wf-start"; val_txt = f"{disp_start:.1f}%"; clr = "--muted"
                elif i == len(running) - 1:
                    # final bar: bottom of chart up to value
                    top_px = _y(v); bot_px = _y(lo)
                    h_px = max(bot_px - top_px, 4)
                    cls = "ct-wf-end"; val_txt = f"{disp_final:.1f}%"; clr = "--teal"
                else:
                    # delta bar: floats between prev and current running total
                    d = disp_deltas[i - 1]
                    prev_v = running[i - 1]
                    bar_top = max(v, prev_v); bar_bot = min(v, prev_v)
                    top_px = _y(bar_top); bot_px = _y(bar_bot)
                    h_px = max(bot_px - top_px, 4)
                    cls = "ct-wf-up" if d >= 0 else "ct-wf-down"
                    val_txt = f"{'+' if d >= 0 else ''}{d:.1f} pp"
                    clr = "--teal" if d >= 0 else "--orange"
                lbl = step_labels[i][0] if i < len(step_labels) else ""
                val_top = max(top_px - 16, 0)
                bars_html += (f'<div class="ct-wf-bar">'
                              f'<div class="ct-wf-val" style="top:{val_top}px;color:var({clr})">{val_txt}</div>'
                              f'<div class="ct-wf-rect {cls}" style="top:{top_px}px;height:{h_px}px"></div>'
                              f'<div class="ct-wf-lbl">{lbl}</div></div>')
            st.markdown(f'<div class="ct-wf">{bars_html}</div>', unsafe_allow_html=True)
            for i, (name, desc) in enumerate(step_labels):
                if i == 0:
                    st.caption(f"**{name}**: {desc} → {disp_start:.1f}%")
                elif i < len(running):
                    d = disp_deltas[i - 1]
                    st.caption(f"**{name}**: {desc} → {'+' if d >= 0 else ''}{d:.1f} pp → {running[i]:.1f}%")
            st.caption(f"**Total gap**: {'+' if disp_gap >= 0 else ''}{disp_gap:.1f} pp.  Method: sequential substitution — swap one definition component at a time. Intermediate bars show a hypothetical mixed definition, not any team's real figure. Step ordering is arbitrary; reversing it changes intermediate values but not the total gap.")
            with st.expander("Show SQL"):
                st.code(SQL[bm["key"]], language="sql")

    # --- Risk Quadrant ---
    with safe_section("risk quadrant"):
        st.markdown('<div class="ct-sl">Supplier risk quadrant</div>', unsafe_allow_html=True)
        import altair as alt
        scat_df = q(SQL["scatter_suppliers"])
        canon_otd_rq = float(q(SQL["ov_core"]).iloc[0]["OTD_PCT"])
        if not scat_df.empty:
            scat_df["OTD_PCT"] = scat_df["OTD_PCT"].astype(float)
            scat_df["DAYS_TO_CONTRACT_EXPIRY"] = scat_df["DAYS_TO_CONTRACT_EXPIRY"].astype(float)
            scat_df["LINE_COUNT"] = scat_df["LINE_COUNT"].astype(float)
            otd_min = scat_df["OTD_PCT"].min(); otd_max = scat_df["OTD_PCT"].max()
            x_lo = math.floor(otd_min / 4) * 4 - 2; x_hi = math.ceil(otd_max / 4) * 4 + 2
            # shaded "Renegotiate now" zone
            zone = alt.Chart(pd.DataFrame({"x":[x_lo],"x2":[canon_otd_rq],"y":[0],"y2":[90]})).mark_rect(
                color="#c2410c", opacity=0.07
            ).encode(x="x:Q",x2="x2:Q",y="y:Q",y2="y2:Q")
            zone_lbl = alt.Chart(pd.DataFrame({"x":[(x_lo+canon_otd_rq)/2],"y":[80],"t":["Renegotiate now"]})).mark_text(
                fontSize=10, fontWeight="bold", color="#c2410c", opacity=0.5
            ).encode(x="x:Q",y="y:Q",text="t:N")
            points = alt.Chart(scat_df).mark_circle(opacity=0.8).encode(
                x=alt.X("OTD_PCT:Q", title="On-time delivery %",
                         scale=alt.Scale(domain=[x_lo, x_hi]),
                         axis=alt.Axis(values=list(range(int(x_lo), int(x_hi)+1, 4)), grid=False)),
                y=alt.Y("DAYS_TO_CONTRACT_EXPIRY:Q", title="Days to contract expiry",
                         scale=alt.Scale(domain=[0, max(scat_df["DAYS_TO_CONTRACT_EXPIRY"].max()+20, 200)]),
                         axis=alt.Axis(grid=True, gridColor="#9ca3af", gridOpacity=0.15)),
                size=alt.Size("LINE_COUNT:Q", title="Order lines", scale=alt.Scale(range=[30,400])),
                color=alt.condition(
                    (alt.datum.OTD_PCT < canon_otd_rq) & (alt.datum.DAYS_TO_CONTRACT_EXPIRY <= 90),
                    alt.value("#c2410c"), alt.value("#0d7377")),
                tooltip=[alt.Tooltip("SUPPLIER_NAME:N",title="Supplier"),
                         alt.Tooltip("OTD_PCT:Q",title="OTD %",format=".1f"),
                         alt.Tooltip("DAYS_TO_CONTRACT_EXPIRY:Q",title="Days to expiry"),
                         alt.Tooltip("LINE_COUNT:Q",title="Lines")]
            )
            ref_line = alt.Chart(pd.DataFrame({"x":[canon_otd_rq]})).mark_rule(
                strokeDash=[4,4], color="#71717a", strokeWidth=1
            ).encode(x="x:Q")
            chart_rq = (zone + zone_lbl + points + ref_line).properties(height=300).configure_view(strokeWidth=0)
            st.altair_chart(chart_rq, use_container_width=True)
            st.caption(f"Low OTD = below the canonical average ({canon_otd_rq:.1f}%). Point size = order line volume. Orange zone: renegotiate now (low OTD + contract expiring within 90 days).")

            # Supplier contract lookup
            risk_sups = scat_df[(scat_df["OTD_PCT"] < canon_otd_rq) & (scat_df["DAYS_TO_CONTRACT_EXPIRY"] <= 90)].sort_values("OTD_PCT")
            if not risk_sups.empty:
                st.markdown('<div class="ct-sl">At-risk suppliers</div>', unsafe_allow_html=True)
                sel_sup = st.selectbox("Select a supplier", risk_sups["SUPPLIER_NAME"].tolist(), key="rq_sup")
                sel_id = risk_sups[risk_sups["SUPPLIER_NAME"] == sel_sup].iloc[0]["SUPPLIER_ID"]
                # fetch contract clauses (cached per supplier)
                try:
                    for hit in search_preview(sel_id, "SLA penalty late delivery corrective action", 3):
                        did = hit.get("doc_id",""); dtxt = hit.get("doc_text","")
                        if did or dtxt:
                            st.markdown(f'<div class="ct-doc"><span class="ct-doc-id">{did}</span> {dtxt}</div>', unsafe_allow_html=True)
                except Exception:
                    st.caption("Could not fetch contract clauses.")

                # corrective action button
                if st.button(f"Create corrective action for {sel_sup}", key="ca_btn", type="primary"):
                    with st.spinner("Creating..."):
                        ca_result = run_nocache(f"CALL SC_ONTOLOGY.GOVERNANCE.CREATE_CORRECTIVE_ACTION('{sel_id}')").iloc[0][0]
                    if "DUPLICATE" in ca_result:
                        st.warning(ca_result)
                    else:
                        st.success(ca_result)

            # open corrective actions (always read fresh)
            if st.session_state.get("ca_close_msg"):
                st.success(st.session_state.pop("ca_close_msg"))
            ca_all = run_nocache(SQL["corrective_actions"])
            ca_open = ca_all[ca_all["STATUS"] == "OPEN"] if not ca_all.empty else ca_all
            ca_closed = ca_all[ca_all["STATUS"] == "CLOSED"] if not ca_all.empty else ca_all
            if not ca_open.empty:
                st.markdown('<div class="ct-sl">Open corrective actions</div>', unsafe_allow_html=True)
                st.dataframe(ca_open[["SUPPLIER_ID","SUPPLIER_NAME","OTD_PCT","CONTRACT_EXPIRY","STATUS","CREATED_AT"]],
                             use_container_width=True, hide_index=True)
            n_open = len(ca_open)
            if st.button("Close all open actions", key="ca_close_all", type="secondary",
                         disabled=(n_open == 0)):
                close_r = run_nocache("CALL SC_ONTOLOGY.GOVERNANCE.RESET_CORRECTIVE_ACTIONS()").iloc[0][0]
                st.session_state["ca_close_msg"] = f"{n_open} action{'s' if n_open != 1 else ''} closed."
                st.rerun()
            n_closed = len(ca_closed)
            if n_closed > 0:
                with st.expander("Action history"):
                    ca_hist = ca_closed.drop(columns=["ACTION_ID"], errors="ignore").head(5)
                    st.dataframe(ca_hist, use_container_width=True, hide_index=True)

# ===== TAB 2: ASK =====
with tabs[1]:
    with safe_section("Ask tab"):
        st.markdown('<div class="ct-sl">Ask a question</div>', unsafe_allow_html=True)
        SAMPLES=[
            ("Low-OTD + expiring contracts", "Which 5 suppliers have the lowest on-time delivery and a contract expiring within 90 days?"),
            ("Penalty for Cobalt 12", "What penalty applies to late deliveries for Supplier Cobalt 12?"),
            ("Customer satisfaction score", "What is our customer satisfaction score?"),
            ("OTD by plant region", "What is our on-time delivery rate by plant region?"),
            ("DOI by part category", "What is days of inventory by part category?"),
        ]

        # --- session state: ask_box is the widget key, ask_pending flags a run ---
        if "ask_pending" not in st.session_state:
            st.session_state["ask_pending"] = False
        if "ask_last_q" not in st.session_state:
            st.session_state["ask_last_q"] = None
        if "ask_last_ts" not in st.session_state:
            st.session_state["ask_last_ts"] = None

        def _chip(full):
            st.session_state["ask_box"] = full
            st.session_state["ask_pending"] = True
            st.session_state["ask_last_q"] = None

        def _clear():
            st.session_state["ask_box"] = ""
            st.session_state["ask_pending"] = False
            st.session_state["ask_last_q"] = None
            st.session_state["ask_last_ts"] = None

        cols = st.columns(len(SAMPLES) + 1)
        for i, (short, full) in enumerate(SAMPLES):
            cols[i].button(short, key=f"s{i}", on_click=_chip, args=(full,), help=full)
        cols[-1].button("Clear", key="clr", on_click=_clear)

        st.text_input("Question", key="ask_box", label_visibility="collapsed",
                      placeholder="Type a supply-chain question...")

        def _go():
            st.session_state["ask_pending"] = True
            st.session_state["ask_last_q"] = None

        st.button("Ask ChainTruth", type="primary", key="ask_go", on_click=_go)

        box_val = st.session_state.get("ask_box", "").strip()
        question = box_val if st.session_state.get("ask_pending") and box_val else None

        if question:
            st.session_state["ask_pending"] = False
            run_ts = time.strftime("%Y-%m-%d %H:%M:%S")
            st.session_state["ask_last_q"] = question
            st.session_state["ask_last_ts"] = run_ts

            # --- cache lookup ---
            ask_from_cache = False
            try:
                ask_dv = AC.data_version(session)
            except Exception:
                ask_dv = None
            cache_hit = None
            if ask_dv:
                try:
                    cache_hit = AC.lookup(session, question, ask_dv)
                except Exception:
                    cache_hit = None

            if cache_hit:
                # ---- SERVE FROM CACHE ----
                ask_from_cache = True
                elapsed = cache_hit["ELAPSED_SECONDS"]
                saved_hhmi = cache_hit["SAVED_HHMI"]
                gen_sql = cache_hit["SQL_TEXT"] or None
                answer_full = cache_hit["ANSWER_TEXT"]
                cached_tools_str = cache_hit.get("TOOLS", "")
                cached_tools = set(cached_tools_str.split(",")) if cached_tools_str else set()
                cached_evidence = cache_hit.get("EVIDENCE", {})

                # re-execute saved SQL for fresh result_df
                result_df = None
                if gen_sql and safe_select(gen_sql):
                    try:
                        result_df = run_nocache(gen_sql)
                    except Exception:
                        result_df = None

                # rebuild parsed-like structure for badge computation
                is_refusal = not gen_sql and "ContractSearch" not in cached_tools
                parsed = {"texts": [answer_full], "tools": cached_tools, "tool_steps": [],
                          "sql": gen_sql, "search_results": []}

                # contract evidence from cache
                all_evidence = []
                if isinstance(cached_evidence, list):
                    all_evidence = cached_evidence
                elif isinstance(cached_evidence, dict) and cached_evidence:
                    all_evidence = [cached_evidence]
                app_fetched = False

                badge_cls, badge_txt = compute_badge(parsed, result_df)
                if all_evidence and "SupplyChainAnalyst" in cached_tools:
                    badge_cls, badge_txt = "gov", "Governed metric + contract evidence"

                # no fake timeline for cached answers
                tl_html = ""

                answer_display = strip_narration(answer_full)
                blocks = re.split(r'\n{2,}', answer_display.strip())
                short_blocks = blocks[:2] if blocks else []
                long_blocks = blocks[2:] if len(blocks) > 2 else []
                short_answer = "\n\n".join(short_blocks)
                long_answer = "\n\n".join(long_blocks)

            else:
                # ---- LIVE CALL ----
                t0 = time.time()
                progress = st.empty()
                progress.info("Calling the ChainTruth agent... this may take 20-60 s for cross-domain questions.")
                parsed = None
                try:
                    resp = ask_agent(question)
                    parsed = parse_agent_response(resp)
                except Exception as e:
                    elapsed = time.time() - t0
                    if elapsed > 55:
                        progress.warning(f"Agent timed out after {elapsed:.0f}s.")
                        if st.button("Retry", key="retry"):
                            st.session_state["ask_pending"] = True
                            st.rerun()
                        st.stop()
                    progress.empty()
                    with st.expander("Diagnostic"):
                        st.code(traceback.format_exc(), language="text")
                    st.error(f"Agent call failed: {e}")
                    st.stop()
                elapsed = time.time() - t0
                progress.empty()

            if not ask_from_cache:
                # execute SQL
                result_df = None
                gen_sql = parsed["sql"]
                if gen_sql and safe_select(gen_sql):
                    try:
                        result_df = run_nocache(gen_sql)
                    except Exception:
                        result_df = None

                # deterministic contract evidence
                sup_col = None
                if result_df is not None and not result_df.empty:
                    sup_col = next((c for c in result_df.columns if c.upper() == "SUPPLIER_ID"), None)
                all_evidence = list(parsed.get("search_results", []))
                app_fetched = False
                # fetch from result supplier_ids
                if sup_col and result_df is not None and not result_df.empty:
                    sids = result_df[sup_col].head(3).tolist()
                    fetched = fetch_contract_evidence(sids)
                    seen = {h.get("doc_id") for h in all_evidence if h.get("doc_id")}
                    for h in fetched:
                        if h.get("doc_id") and h.get("doc_id") not in seen:
                            all_evidence.append(h)
                            seen.add(h.get("doc_id"))
                    if fetched:
                        app_fetched = True
                        parsed["tools"].add("ContractSearch")
                # for contract-only questions: if agent returned search results without doc_id,
                # extract SUP-XXX from the answer and fetch proper evidence
                if not app_fetched and "ContractSearch" in parsed["tools"]:
                    answer_tmp = "\n".join(parsed["texts"])
                    sup_ids_in_text = list(set(re.findall(r'SUP-\d{3}', answer_tmp)))[:3]
                    if sup_ids_in_text:
                        fetched = fetch_contract_evidence(sup_ids_in_text)
                        seen = {h.get("doc_id") for h in all_evidence if h.get("doc_id")}
                        for h in fetched:
                            if h.get("doc_id") and h.get("doc_id") not in seen:
                                all_evidence.append(h)
                                seen.add(h.get("doc_id"))
                        if fetched:
                            app_fetched = True

                # badge
                badge_cls, badge_txt = compute_badge(parsed, result_df)
                if all_evidence and "SupplyChainAnalyst" in parsed["tools"]:
                    badge_cls, badge_txt = "gov", "Governed metric + contract evidence"
                is_refusal = badge_cls == "ref"

                # timeline (fix 5: grammar)
                tl_steps = []
                step_n = 0
                agent_sc = sum(1 for t in parsed.get("tool_steps", []) if t == "ContractSearch")
                for t in parsed.get("tool_steps", []):
                    step_n += 1
                    if t == "SupplyChainAnalyst":
                        tl_steps.append(f"<b>{step_n}</b> Governed metrics queried")
                    elif t == "ContractSearch" and agent_sc > 0:
                        s_word = "supplier" if agent_sc == 1 else "suppliers"
                        tl_steps.append(f"<b>{step_n}</b> Contracts searched ({agent_sc} {s_word})")
                        agent_sc = 0
                if app_fetched:
                    step_n += 1
                    n_fetched = len(set(result_df[sup_col].head(3).tolist())) if sup_col else 0
                    s_word = "supplier" if n_fetched == 1 else "suppliers"
                    tl_steps.append(f"<b>{step_n}</b> Contracts retrieved ({n_fetched} {s_word})")
                if tl_steps:
                    step_n += 1
                    tl_steps.append(f"<b>{step_n}</b> Answer composed")
                tl_html = f'<div class="ct-tl">{" &rarr; ".join(tl_steps)} &middot; {elapsed:.1f}s</div>' if tl_steps else ""

                # answer text (fix 2: preserve bullets; fix 5: narration strip)
                answer_full = "\n\n".join(parsed["texts"])
                answer_display = strip_narration(answer_full)
                # split on blank lines to preserve bullet structure
                blocks = re.split(r'\n{2,}', answer_display.strip())
                short_blocks = blocks[:2] if blocks else []
                long_blocks = blocks[2:] if len(blocks) > 2 else []
                short_answer = "\n\n".join(short_blocks)
                long_answer = "\n\n".join(long_blocks)

                # save to cache (save governed answers AND refusals; never save errors/timeouts/clarifying questions)
                if ask_dv and answer_full.strip():
                    try:
                        AC.save(session, question, answer_full, gen_sql or "",
                                all_evidence, parsed["tools"], elapsed, ask_dv)
                    except Exception:
                        pass

            # ---- RENDER ----

            # 1. Echo card
            st.markdown(f'<div class="ct-echo"><div class="ct-echo-q">You asked: {question}</div>'
                        f'<div class="ct-echo-t">{run_ts}</div></div>', unsafe_allow_html=True)

            # 2. Badge + timeline
            cls_map = {"gov": "ct-b-gov", "res": "ct-b-res", "ref": "ct-b-ref"}
            st.markdown(f'<span class="ct-badge {cls_map[badge_cls]}">{badge_txt}</span>', unsafe_allow_html=True)
            if tl_html:
                st.markdown(tl_html, unsafe_allow_html=True)

            # 3. Short answer (fix 4: refusal uses deterministic list)
            if is_refusal:
                # keep only the LLM's one-sentence explanation + clarifying question, not its metric list
                first_line = ""
                for blk in blocks:
                    stripped = blk.strip()
                    if stripped and not stripped.startswith("-") and not stripped.startswith("*") and not stripped.startswith("1."):
                        first_line = stripped
                        break
                if first_line:
                    st.markdown(first_line)
                st.markdown('<div class="ct-sl">Defined metrics</div>', unsafe_allow_html=True)
                ont_ref = q(SQL["ont_metric_all"])
                for _, m in ont_ref.iterrows():
                    st.markdown(f'<div class="ct-defn"><strong>{m["DISPLAY_NAME"]}</strong>: {m["CANONICAL_DEFINITION"]}</div>', unsafe_allow_html=True)
            else:
                if short_answer:
                    st.markdown(short_answer)
                if long_answer:
                    with st.expander("Full answer"):
                        st.markdown(long_answer)

            # 4. Highlights
            if result_df is not None and not result_df.empty:
                otd_c = next((c for c in result_df.columns if "OTD" in c.upper()), None)
                exp_c = next((c for c in result_df.columns if "DAYS_TO" in c.upper()), None)
                name_c = next((c for c in result_df.columns if "NAME" in c.upper()), None)
                if otd_c or exp_c:
                    hl = ""
                    if otd_c and name_c:
                        wr = result_df.loc[result_df[otd_c].idxmin()]
                        hl += f'<div class="ct-hl-item"><div class="ct-hl-label">Lowest OTD</div><div class="ct-hl-val">{wr[name_c]}: {wr[otd_c]:.1f}%</div></div>'
                    if exp_c and name_c:
                        ve = result_df[result_df[exp_c].notna()]
                        if not ve.empty:
                            ur = ve.loc[ve[exp_c].idxmin()]
                            hl += f'<div class="ct-hl-item"><div class="ct-hl-label">Soonest expiry</div><div class="ct-hl-val">{ur[name_c]}: {int(ur[exp_c])} days</div></div>'
                    if exp_c:
                        n30 = int((result_df[exp_c] <= 30).sum()); n90 = int((result_df[exp_c] <= 90).sum())
                        hl += f'<div class="ct-hl-item"><div class="ct-hl-label">Expiring contracts</div><div class="ct-hl-val">{n30} within 30d &middot; {n90} within 90d</div></div>'
                    if hl:
                        st.markdown(f'<div class="ct-hl">{hl}<div class="ct-hl-note">Computed from the table</div></div>', unsafe_allow_html=True)

            # 5. Result table
            if result_df is not None and not result_df.empty:
                COL_NAMES = {"SUPPLIER_NAME":"Supplier","SUPPLIER_ID":"ID","OTD_PCT":"OTD %",
                    "LINE_COUNT":"Order lines","CONTRACT_EXPIRY_DATE":"Contract expiry",
                    "DAYS_TO_CONTRACT_EXPIRY":"Days to expiry","FILL_RATE_PCT":"Fill rate %",
                    "IN_FULL_PCT":"In-full %","DAYS_OF_INVENTORY":"Days of inventory",
                    "PLANT_REGION":"Region","PLANT_NAME":"Plant","PART_CATEGORY":"Category",
                    "DELIVERY_MONTH":"Month","AVG_LANDED_COST_PER_UNIT":"Landed cost/unit",
                    "SUPPLIER_COUNTRY":"Country","AVG_DAYS_LATE":"Avg days late","CUSTOMER_SEGMENT":"Segment"}
                NUM_SET = {"OTD_PCT","FILL_RATE_PCT","IN_FULL_PCT","LINE_COUNT",
                    "DAYS_TO_CONTRACT_EXPIRY","DAYS_OF_INVENTORY","AVG_LANDED_COST_PER_UNIT","AVG_DAYS_LATE"}
                hdr = "".join(f"<th>{COL_NAMES.get(c,c)}</th>" for c in result_df.columns)
                rw = ""
                for _, r in result_df.iterrows():
                    cells = ""
                    for c in result_df.columns:
                        v = r[c]; is_n = c.upper() in NUM_SET
                        if pd.isna(v): cells += '<td class="num">\u2014</td>' if is_n else "<td>\u2014</td>"
                        elif c.upper() == "OTD_PCT": cells += f'<td class="num">{float(v):.1f}%</td>'
                        elif is_n:
                            try: cells += f'<td class="num">{float(v):,.1f}</td>'
                            except: cells += f"<td>{v}</td>"
                        else: cells += f"<td>{v}</td>"
                    rw += f"<tr>{cells}</tr>"
                st.markdown(f'<table class="ct-restbl"><tr>{hdr}</tr>{rw}</table>', unsafe_allow_html=True)
            elif result_df is not None and result_df.empty:
                st.info("No data returned. The data may be restricted for your role.")
            elif gen_sql and not safe_select(gen_sql):
                st.error("Blocked: the generated statement was not a read-only query.")

            # 6. Contract evidence (show for ANY answer with search results, not just supplier_id)
            if all_evidence:
                st.markdown('<div class="ct-sl">Contract evidence</div>', unsafe_allow_html=True)
                for hit in all_evidence[:6]:
                    did = hit.get("doc_id", ""); dtxt = hit.get("doc_text", "")
                    if did or dtxt:
                        st.markdown(f'<div class="ct-doc"><span class="ct-doc-id">{did}</span> {dtxt}</div>', unsafe_allow_html=True)

            # 7. Chart
            if result_df is not None and not result_df.empty and len(result_df) > 1:
                import altair as alt
                otd_c2 = next((c for c in result_df.columns if "OTD" in c.upper() and "PCT" in c.upper()), None)
                name_c2 = next((c for c in result_df.columns if "SUPPLIER_NAME" in c.upper()), None)
                exp_c2 = next((c for c in result_df.columns if "DAYS_TO" in c.upper()), None)
                if otd_c2 and name_c2:
                    canon_otd = float(q(SQL["ov_core"]).iloc[0]["OTD_PCT"])
                    cd = result_df.copy(); cd["_n"] = cd[name_c2]; cd["_o"] = cd[otd_c2].astype(float)
                    if exp_c2: cd["_e"] = cd[exp_c2].astype(float)
                    bars = alt.Chart(cd).mark_bar(color="#0d7377").encode(
                        y=alt.Y("_n:N", sort=alt.EncodingSortField(field="_o", order="ascending"), title=""),
                        x=alt.X("_o:Q", title="On-time delivery %", scale=alt.Scale(domain=[0, 100])),
                        tooltip=[alt.Tooltip("_n:N", title="Supplier"), alt.Tooltip("_o:Q", title="OTD %", format=".1f")])
                    rule = alt.Chart(pd.DataFrame({"x": [canon_otd]})).mark_rule(strokeDash=[4, 4], color="#71717a", strokeWidth=1.5).encode(x="x:Q")
                    rl = alt.Chart(pd.DataFrame({"x": [canon_otd], "l": [f"Canonical: {canon_otd:.1f}%"]})).mark_text(
                        align="left", dx=4, dy=-8, fontSize=10, color="#71717a").encode(x="x:Q", text="l:N")
                    st.altair_chart((bars + rule + rl).properties(height=max(len(cd) * 36, 140)).configure_view(strokeWidth=0), use_container_width=True)
                    if exp_c2:
                        pills = ""
                        for _, rr in cd.sort_values("_o").iterrows():
                            ev = rr.get("_e", 999)
                            if pd.notna(ev) and ev < 999:
                                clr = "var(--red)" if ev < 30 else ("var(--orange)" if ev < 90 else "var(--muted)")
                                pills += f'<span style="font-size:.75rem;font-weight:700;color:{clr};margin-right:12px;">{rr["_n"]}: {int(ev)}d</span>'
                        if pills:
                            st.markdown(f'<div style="font-size:.68rem;color:var(--muted);margin-bottom:2px;">CONTRACT EXPIRY</div>{pills}', unsafe_allow_html=True)
                elif otd_c2 is None:
                    num_cs = [c for c in result_df.columns if pd.api.types.is_numeric_dtype(result_df[c])]
                    cat_cs = [c for c in result_df.columns if not pd.api.types.is_numeric_dtype(result_df[c])]
                    if num_cs and cat_cs:
                        mc = num_cs[0]; cc = cat_cs[0]; ht2 = COL_NAMES.get(mc, mc)
                        d2 = result_df.copy(); d2["_m"] = d2[mc].astype(float); d2["_c"] = d2[cc]
                        ch2 = alt.Chart(d2).mark_bar(color="#0d7377").encode(
                            x=alt.X("_c:N", title=COL_NAMES.get(cc, cc), axis=alt.Axis(labelAngle=0)),
                            y=alt.Y("_m:Q", title=ht2, scale=alt.Scale(domainMin=0)),
                            tooltip=[alt.Tooltip("_c:N"), alt.Tooltip("_m:Q", format=".1f")]
                        ).properties(height=250).configure_view(strokeWidth=0)
                        st.altair_chart(ch2, use_container_width=True)

            # 8. Proof panel
            with st.expander("Proof"):
                if answer_full:
                    st.markdown('<div class="ct-sl">Full agent response</div>', unsafe_allow_html=True)
                    st.markdown(answer_full)
                if gen_sql:
                    st.markdown('<div class="ct-sl">Generated SQL</div>', unsafe_allow_html=True)
                    st.code(gen_sql, language="sql")
                ont = q(SQL["ont_metric_all"])
                sql_lower = (gen_sql or "").lower() + " " + answer_full.lower()
                shown = False
                for _, m in ont.iterrows():
                    if m["METRIC_NAME"] in sql_lower:
                        st.markdown(f'<div class="ct-defn"><strong>{m["DISPLAY_NAME"]}</strong>: {m["CANONICAL_DEFINITION"]}</div>', unsafe_allow_html=True)
                        shown = True
                if not shown and is_refusal:
                    st.markdown('<div class="ct-sl">Defined metrics</div>', unsafe_allow_html=True)
                    st.dataframe(ont[["DISPLAY_NAME", "CANONICAL_DEFINITION"]], use_container_width=True, hide_index=True)
                if gen_sql:
                    ont_f = q(SQL["ont_metric_formulas"])
                    checks = check_formula(gen_sql, ont_f)
                    if checks:
                        st.markdown('<div class="ct-sl">Formula check</div>', unsafe_allow_html=True)
                        for name, status, msg in checks:
                            fcls = {"ok": "ct-formula-ok", "warn": "ct-formula-warn", "na": "ct-formula-na"}[status]
                            st.markdown(f'<span class="{fcls}">{name}: {msg}</span>', unsafe_allow_html=True)

            # 9. Proof Receipt
            with safe_section("receipt"):
                st.markdown('<div class="ct-sl">Proof receipt</div>', unsafe_allow_html=True)
                sql_hash_short = hashlib.sha256(gen_sql.encode()).hexdigest()[:16] if gen_sql else "—"
                sql_hash_full = hashlib.sha256(gen_sql.encode()).hexdigest() if gen_sql else "—"
                row_count = len(result_df) if result_df is not None else 0
                role_now = q(SQL["header_role"]).iloc[0]["R"]
                ov_live = q(SQL["ov_core"])  # cache is cleared after "Run tests now"
                freshness_df = ov_live
                data_fresh = str(freshness_df.iloc[0]["LATEST"])[:10] if not freshness_df.empty else "—"
                ht_live = ov_live
                t_total_r = int(ht_live.iloc[0]["TOTAL"]) if not ht_live.empty and ht_live.iloc[0]["TOTAL"] else 0
                t_pass_r = int(ht_live.iloc[0]["PASSED"]) if not ht_live.empty and ht_live.iloc[0]["PASSED"] else 0
                # matched metrics
                ont_rcpt = q(SQL["ont_metric_all"])
                matched = []
                sql_lower_r = (gen_sql or "").lower() + " " + answer_full.lower()
                for _, mr in ont_rcpt.iterrows():
                    if mr["METRIC_NAME"] in sql_lower_r:
                        matched.append({"name": mr["DISPLAY_NAME"], "definition": mr["CANONICAL_DEFINITION"]})
                metric_txt = "; ".join(m["name"] for m in matched) if matched else "—"
                defn_txt = " | ".join(m["definition"] for m in matched) if matched else "—"
                tools_txt = ", ".join(sorted(parsed["tools"])) if parsed["tools"] else "—"

                def _rr(k, v): return f'<div class="ct-rcpt-row"><div class="ct-rcpt-k">{k}</div><div class="ct-rcpt-v">{v}</div></div>'
                rcpt_html = ('<div class="ct-rcpt">'
                    + _rr("Question", question)
                    + _rr("Timestamp", run_ts)
                    + _rr("Source", f"Cached (saved {saved_hhmi})" if ask_from_cache else "Live")
                    + _rr("Role", f"{role_now} (app runs with the owner's rights)")
                    + _rr("Tools called", tools_txt)
                    + _rr("Metric", metric_txt)
                    + _rr("Definition", defn_txt)
                    + _rr("SQL hash (SHA-256)", f"<code>{sql_hash_short}</code>")
                    + _rr("Rows returned", str(row_count))
                    + _rr("Data freshness", data_fresh)
                    + _rr("Consistency tests", f"{t_pass_r}/{t_total_r} passing")
                    + '</div>')
                st.markdown(rcpt_html, unsafe_allow_html=True)

                receipt_json = json.dumps({
                    "question": question, "timestamp": run_ts,
                    "source": f"cached (saved {saved_hhmi})" if ask_from_cache else "live",
                    "role": role_now,
                    "tools": sorted(parsed["tools"]), "metric": metric_txt,
                    "definition": defn_txt, "sql_hash_sha256": sql_hash_full,
                    "rows": row_count, "data_freshness": data_fresh,
                    "consistency_tests": f"{t_pass_r}/{t_total_r}"
                }, indent=2)
                st.download_button("Download receipt", data=receipt_json,
                                   file_name=f"chaintruth_receipt_{run_ts.replace(' ','_').replace(':','')}.json",
                                   mime="application/json", key="dl_rcpt")

        elif st.session_state.get("ask_last_q"):
            st.markdown(f'<div class="ct-echo"><div class="ct-echo-q">You asked: {st.session_state["ask_last_q"]}</div>'
                        f'<div class="ct-echo-t">{st.session_state.get("ask_last_ts", "")}</div></div>', unsafe_allow_html=True)
            st.caption("Re-run to refresh the result.")

# ===== TAB 3: PERSONAS =====
with tabs[2]:
    with safe_section("Personas"):
        import personas as PR
        st.markdown('<div class="ct-sl">Same metric, different words, one number</div>', unsafe_allow_html=True)
        st.write("Each persona phrases the OTD question differently. All three must resolve to the same canonical definition.")
        if "per_results" not in st.session_state:
            st.session_state["per_results"] = {}
        go = st.button("Run all three", type="primary", key="per_go")
        status = st.empty()
        grid = st.columns(3)
        slots = {name: grid[i].empty() for i, (name, _) in enumerate(PR.PERSONAS)}

        def _card(name, phrase, r):
            if r is None:
                body = '<div class="ct-per-v ct-null">—</div>'
            elif r["value"] is not None:
                note = f'<div class="ct-fn">{r["reason"]}</div>' if r["reason"] else ""
                body = f'<div class="ct-per-v">{r["value"]:.2f}%</div>{note}'
            else:
                body = f'<div class="ct-per-v ct-null">—</div><div class="ct-fn">{r["reason"]}</div>'
            slots[name].markdown(f'<div class="ct-per"><div class="ct-per-n">{name}</div>'
                                 f'<div class="ct-per-q">"{phrase}"</div>{body}</div>', unsafe_allow_html=True)

        if go:
            st.session_state["per_results"] = {}
            for name, phrase in PR.PERSONAS:
                _card(name, phrase, None)
            status.caption("Running 3 persona questions concurrently... 0 of 3 done")

            def _done(name, r):
                st.session_state["per_results"][name] = r  # stored as soon as it completes
                _card(name, dict(PR.PERSONAS)[name], r)
                status.caption(f"{len(st.session_state['per_results'])} of 3 done")

            _, conc = PR.run_all(session, PR.PERSONAS, on_done=_done)
            status.caption(f"3 of 3 done ({'concurrent' if conc else 'sequential'} run)")
        else:
            for name, phrase in PR.PERSONAS:
                _card(name, phrase, st.session_state["per_results"].get(name))

        res_p = st.session_state["per_results"]
        if len(res_p) == 3:
            ok, msg = PR.verdict(res_p)
            st.markdown(f'<span class="ct-pill {"ct-pill-ok" if ok else "ct-pill-bad"}">{msg}</span>', unsafe_allow_html=True)
        for name, r in res_p.items():
            if r.get("error"):
                with st.expander(f"Diagnostic: {name}"):
                    st.code(r["error"], language="text")

# ===== TAB 4: GOVERNANCE =====
with tabs[3]:
    with safe_section("Governance"):
        st.markdown('<div class="ct-sl">What each role sees</div>', unsafe_allow_html=True)
        st.caption("Captured with USE SECONDARY ROLES NONE to isolate each persona. "
                   "SiS runs as the app owner, so live role switching cannot demonstrate masking.")
        snap=q(SQL["gov_snap"])
        if snap.empty:
            st.info("No snapshot data. Run sql/08_role_snapshot.sql first.")
        else:
            ts=snap["CAPTURED_AT"].iloc[0]
            st.caption(f"Captured at: {ts}")
            MDISP={"otd_pct":"On-time delivery %","fill_rate_pct":"Fill rate %","in_full_pct":"In-full %",
                   "avg_days_late":"Avg days late","days_of_inventory":"Days of inventory",
                   "avg_landed_cost_per_unit":"Landed cost / unit"}
            roles=["PLANNER_ROLE","PROCUREMENT_ROLE","LOGISTICS_ROLE"]
            rows_html=""
            for m in MDISP:
                cells=""
                for r in roles:
                    row=snap[(snap["METRIC_NAME"]==m)&(snap["ROLE_NAME"]==r)]
                    if row.empty: cells+="<td>—</td>"
                    elif row.iloc[0]["IS_MASKED"]: cells+='<td><span class="ct-masked">Restricted</span></td>'
                    else: cells+=f'<td>{row.iloc[0]["METRIC_VALUE"]:.2f}</td>'
                rows_html+=f'<tr><td>{MDISP[m]}</td>{cells}</tr>'
            st.markdown(f'<table class="ct-gg"><tr><th>Metric</th><th>Planning</th><th>Procurement</th><th>Logistics</th></tr>{rows_html}</table>', unsafe_allow_html=True)

# ===== TAB 5: ONTOLOGY =====
with tabs[4]:
    cg,cm=st.columns([2,3])
    with cg:
        with safe_section("entity graph"):
            st.markdown('<div class="ct-sl">Entity relationships</div>', unsafe_allow_html=True)
            rel=q(SQL["ont_rel"])
            dot=['digraph G{','rankdir=LR;','bgcolor="transparent";',
                 'node[shape=box,style="rounded,filled",fillcolor="#0a6e72",color="#0a6e72",fontname="Helvetica",fontsize=11,fontcolor="#ffffff"];',
                 'edge[color="#9ca3af",fontname="Helvetica",fontsize=9,fontcolor="#9ca3af"];']
            for _,r in rel.iterrows():
                dot.append(f'"{r["FROM_ENTITY"]}"->"{r["TO_ENTITY"]}"[label="  {r["RELATIONSHIP"]}  "];')
            dot.append("}")
            st.graphviz_chart("\n".join(dot))
    with cm:
        with safe_section("metric glossary"):
            st.markdown('<div class="ct-sl">Metric glossary</div>', unsafe_allow_html=True)
            glos=q(SQL["ont_metric_full"])
            rows_html=""
            for _,r in glos.iterrows():
                lv=r["LEGACY_VARIANTS"]
                lv_html=f'<div class="ct-glos-legacy">{lv}</div>' if lv and str(lv).strip() and str(lv)!="None" else ""
                rows_html+=f'<tr><td><strong>{r["DISPLAY_NAME"]}</strong></td><td>{r["CANONICAL_DEFINITION"]}{lv_html}</td></tr>'
            st.markdown(f'<table class="ct-glos"><tr><th>Metric</th><th>Canonical definition</th></tr>{rows_html}</table>', unsafe_allow_html=True)
    # --- Interactive lineage ---
    with safe_section("lineage"):
        st.markdown('<div class="ct-sl">Metric lineage</div>', unsafe_allow_html=True)
        lin_m = q(SQL["lineage_metrics"])
        lin_e = q(SQL["lineage_entities"])
        if not lin_m.empty:
            sel_metric = st.selectbox("Select a metric", lin_m["DISPLAY_NAME"].tolist(), key="lin_sel")
            mrow = lin_m[lin_m["DISPLAY_NAME"] == sel_metric].iloc[0]
            mn = mrow["METRIC_NAME"]
            formula = mrow["FORMULA_SQL"]
            owner = mrow["OWNER_PERSONA"]
            # determine source tables from formula columns
            METRIC_SOURCES = {
                "otd_pct": ["RAW.ERP_ORDER_LINES", "RAW.LOGISTICS_SHIPMENTS"],
                "fill_rate_pct": ["RAW.ERP_ORDER_LINES", "RAW.LOGISTICS_SHIPMENTS"],
                "in_full_pct": ["RAW.ERP_ORDER_LINES", "RAW.LOGISTICS_SHIPMENTS"],
                "avg_days_late": ["RAW.ERP_ORDER_LINES", "RAW.LOGISTICS_SHIPMENTS"],
                "avg_landed_cost_per_unit": ["RAW.ERP_ORDER_LINES", "RAW.LOGISTICS_SHIPMENTS"],
                "days_of_inventory": ["RAW.INVENTORY_SNAPSHOTS"],
            }
            sources = METRIC_SOURCES.get(mn, ["RAW tables"])
            dt_name = "CURATED.DT_INVENTORY_LATEST" if mn == "days_of_inventory" else "CURATED.DT_ORDER_LINE"
            fact_name = "CURATED.FACT_INVENTORY" if mn == "days_of_inventory" else "CURATED.FACT_ORDER_LINE"
            # build flow as inline SVG
            nodes = sources + [dt_name, fact_name, "ONTOLOGY.SV_SUPPLY_CHAIN", "APP.SUPPLY_CHAIN_AGENT"]
            n = len(nodes)
            box_w = 140; gap = 20; svg_w = n * (box_w + gap)
            svg_parts = [f'<svg width="100%" viewBox="0 0 {svg_w} 52" style="overflow:visible;font-family:Helvetica,sans-serif;">']
            for i, nd in enumerate(nodes):
                x = i * (box_w + gap)
                short = nd.split(".")[-1] if "." in nd else nd
                is_static = nd in sources  # static label (hardcoded mapping)
                fill = "#0d7377" if not is_static else "#71717a"
                svg_parts.append(
                    f'<rect x="{x}" y="10" width="{box_w}" height="32" rx="4" fill="{fill}" opacity="0.9"/>'
                    f'<text x="{x + box_w/2}" y="30" text-anchor="middle" font-size="8" fill="#fff" font-weight="600">{short}</text>')
                if is_static:
                    svg_parts.append(f'<text x="{x + box_w/2}" y="48" text-anchor="middle" font-size="6" fill="var(--muted)">static</text>')
                if i < n - 1:
                    ax = x + box_w; bx = ax + gap
                    svg_parts.append(f'<line x1="{ax}" y1="26" x2="{bx}" y2="26" stroke="var(--muted)" stroke-width="1" marker-end="url(#arr)"/>')
            svg_parts.insert(1, '<defs><marker id="arr" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6" fill="var(--muted)"/></marker></defs>')
            svg_parts.append('</svg>')
            st.markdown("\n".join(svg_parts), unsafe_allow_html=True)
            st.caption(f"**Formula**: `{formula}`  |  **Owner**: {owner}")
            if mn != "days_of_inventory":
                st.caption(f"Filter: `delivered_date ≤ CURRENT_DATE()` applied at {fact_name} (view layer, not the dynamic table).")

# ===== TAB 6: TRUST =====
with tabs[5]:
    with safe_section("Trust"):
        st.markdown('<div class="ct-sl">Consistency tests</div>', unsafe_allow_html=True)
        if st.button("Run tests now",type="primary",key="trust_go"):
            with st.spinner("Running 9 consistency tests..."):
                r=run_nocache("CALL SC_ONTOLOGY.GOVERNANCE.RUN_CONSISTENCY_TESTS()").iloc[0][0]
            # header chip and receipts read the cached test count: clear and redraw
            q.clear()
            st.session_state["trust_msg"] = r
            st.rerun()
        if st.session_state.get("trust_msg"):
            st.success(st.session_state.pop("trust_msg"))
        res=run_nocache(SQL["trust_results"])
        if res.empty:
            st.info("No test runs yet. Click 'Run tests now'.")
        else:
            total=len(res); passed=int(res["PASSED"].sum()); failed=total-passed
            c1,c2,c3=st.columns(3)
            c1.metric("Passed",passed); c2.metric("Failed",failed)
            c3.metric("Last run",str(res["RUN_TS"].iloc[0])[:19])
            cells=""
            for _,r in res.iterrows():
                cls="ct-tp" if r["PASSED"] else "ct-tf"
                cells+=f'<span class="ct-tc {cls}" title="{r["TEST_NAME"]}: {r["METRIC"]}"></span>'
            st.markdown(cells, unsafe_allow_html=True)
            st.dataframe(res[["TEST_NAME","METRIC","SEMANTIC_VALUE","GOLDEN_VALUE","PASSED"]], use_container_width=True, hide_index=True)
        st.markdown('<div class="ct-sl" style="margin-top:16px;">Open alerts</div>', unsafe_allow_html=True)
        alerts=run_nocache(SQL["alerts"])
        if alerts.empty: st.caption("No open alerts.")
        else: st.dataframe(alerts, use_container_width=True, hide_index=True)
