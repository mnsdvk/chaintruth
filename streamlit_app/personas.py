"""Persona consistency runner: shared by app.py and tests/persona_run_test.py."""
import json, time, traceback
import answer_cache as AC

AGENT = "SC_ONTOLOGY.APP.SUPPLY_CHAIN_AGENT"
PERSONA_TIMEOUT_S = 150  # longer than the Ask tab's 55 s

PERSONAS = [
    ("Planning", "What's our on-time delivery rate overall?"),
    ("Procurement", "Across all suppliers, what percent of deliveries arrive on time?"),
    ("Logistics", "What share of shipments get delivered by the promised date?"),
]


CLARIFY_REPLY = "Use all available data."


def agent_sql(question, prior_answer=None):
    """Build the DATA_AGENT_RUN call. DATA_AGENT_RUN accepts exactly one user message,
    so a clarification retry appends the reply to the original question."""
    text = f"{question} {CLARIFY_REPLY}" if prior_answer else question
    msgs = [{"role": "user", "content": [{"type": "text", "text": text}]}]
    payload = json.dumps({"messages": msgs}).replace("\\", "\\\\").replace("'", "\\'")
    return f"SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN('{AGENT}', '{payload}', TRUE) AS resp"


def answer_text(resp):
    return " ".join(c["text"].strip() for c in resp.get("content", [])
                    if c.get("type") == "text" and c.get("text", "").strip())


def classify(resp):
    """Return (value, reason). value is None when no usable number was found."""
    content = resp.get("content", [])
    sql_results, texts = [], []
    for item in content:
        if item.get("type") == "text" and item.get("text", "").strip():
            texts.append(item["text"].strip())
        if item.get("type") == "tool_result":
            tr = item.get("tool_result", {})
            if tr.get("name") == "system_execute_sql":
                for ci in tr.get("content", []):
                    rs = ci.get("json", {}).get("result_set", {})
                    if rs.get("data"):
                        sql_results.append(rs)
    for rs in sql_results:
        meta = rs.get("resultSetMetaData", {}).get("rowType", [])
        row = rs["data"][0]
        idx = next((i for i, c in enumerate(meta) if "otd" in c.get("name", "").lower()), None)
        if idx is None:
            idx = next((i for i, c in enumerate(meta) if c.get("type") in ("fixed", "real")), None)
        if idx is not None and idx < len(row) and row[idx] is not None:
            try:
                v = float(row[idx])
            except (TypeError, ValueError):
                continue
            reason = "returned a ratio, not a percent" if v <= 1.0 else ""
            return v, reason
    answer = " ".join(texts)
    if not sql_results and "?" in answer:
        return None, "agent asked a clarifying question"
    if not sql_results:
        return None, "no result returned (agent ran no SQL)"
    return None, "no result returned (no numeric OTD column)"


def start(session, question, prior_answer=None):
    """Launch the agent call asynchronously; fall back to None when async is unavailable."""
    try:
        return session.sql(agent_sql(question, prior_answer)).collect_nowait()
    except Exception:
        return None


def finish(session, question, job, t0, timeout_s=PERSONA_TIMEOUT_S, prior_answer=None):
    """Wait for one call. Returns dict with value, reason, secs, error, answer."""
    try:
        if job is None:
            rows = session.sql(agent_sql(question, prior_answer)).collect()
        else:
            while not job.is_done():
                if time.time() - t0 > timeout_s:
                    try:
                        job.cancel()
                    except Exception:
                        pass
                    return {"value": None, "reason": f"timed out after {int(time.time() - t0)} s",
                            "secs": time.time() - t0, "error": "", "answer": ""}
                time.sleep(0.5)
            rows = job.result()
        raw = rows[0][0]
        resp = json.loads(raw) if isinstance(raw, str) else raw
        if "content" not in resp and resp.get("message"):
            return {"value": None, "reason": f"agent error {resp.get('code', '')}: {resp['message']}",
                    "secs": time.time() - t0, "error": json.dumps(resp), "answer": ""}
        v, reason = classify(resp)
        sql = next((ci.get("json", {}).get("sql", "") for c in resp.get("content", [])
                    if c.get("type") == "tool_result" and c.get("tool_result", {}).get("name") == "system_execute_sql"
                    for ci in c["tool_result"].get("content", []) if ci.get("json", {}).get("sql")), "")
        return {"value": v, "reason": reason, "secs": time.time() - t0, "error": "",
                "answer": answer_text(resp), "sql": sql}
    except Exception as e:
        return {"value": None, "reason": f"call failed: {type(e).__name__}",
                "secs": time.time() - t0, "error": traceback.format_exc(), "answer": ""}


def _from_cache(hit, secs):
    """Turn a saved persona answer into a result dict; None if it holds no usable number."""
    ev = hit["EVIDENCE"] if hit else None
    if not isinstance(ev, dict) or ev.get("value") is None:
        return None
    return {"value": float(ev["value"]), "reason": ev.get("reason", ""), "secs": secs, "error": "",
            "answer": hit["ANSWER_TEXT"], "cached": True, "saved_at": hit["SAVED_HHMI"]}


def run_all(session, personas=PERSONAS, on_done=None, use_cache=True):
    """Serve each persona from the answer cache when possible; run the rest concurrently
    (async jobs) with one retry each, and save successful live answers.
    on_done(name, result) is called as soon as each persona completes."""
    results = {}
    jobs = {}
    try:
        dv = AC.data_version(session)
    except Exception:
        dv = None
    for name, q in personas:
        if use_cache and dv:
            t0 = time.time()
            hit = _from_cache(AC.lookup(session, q, dv), 0.0)
            if hit:
                hit["secs"] = time.time() - t0
                results[name] = hit
                if on_done:
                    on_done(name, hit)
                continue
        jobs[name] = (q, start(session, q), time.time())
    concurrent = all(j is not None for _, j, _ in jobs.values())
    for name, (q, job, t0) in jobs.items():
        r = finish(session, q, job, t0)
        if r["value"] is None:  # one automatic retry
            first = r
            prior = first["answer"] if first["reason"] == "agent asked a clarifying question" else None
            t1 = time.time()
            r = finish(session, q, start(session, q, prior), t1, prior_answer=prior)
            r["retried"] = True
            r["secs"] += first["secs"]
            if prior and r["value"] is not None:
                r["reason"] = f'agent asked for a time window; retried with "{CLARIFY_REPLY}" appended'
            elif r["value"] is None:
                r["reason"] = f'{r["reason"]} (after retry; first attempt: {first["reason"]})'
                r["error"] = r["error"] or first["error"]
        r["cached"] = False
        if r["value"] is not None and dv:  # never save errors, timeouts or clarifying questions
            AC.save(session, q, r["answer"], r.get("sql", ""), {"value": r["value"], "reason": r["reason"]},
                    ["SupplyChainAnalyst"], r["secs"], dv)
        results[name] = r
        if on_done:
            on_done(name, r)
    return results, concurrent


def verdict(results):
    vals = [r["value"] for r in results.values()]
    failed = [n for n, r in results.items() if r["value"] is None]
    if failed:
        return False, "Unanswered: " + ", ".join(failed)
    if len(set(round(v, 4) for v in vals)) == 1:
        return True, "Consistent: all personas see the same value"
    return False, "Inconsistent: " + ", ".join(f"{n} {r['value']:.2f}" for n, r in results.items())
