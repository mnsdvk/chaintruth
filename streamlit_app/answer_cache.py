"""Shared answer cache backed by SC_ONTOLOGY.GOVERNANCE.ANSWER_CACHE."""
import json, time

# Module-level memo for data_version (avoids re-running 4 hashes on every click).
_dv_cache = {"value": None, "ts": 0.0}
_DV_TTL = 90  # seconds


def _normalize(question: str) -> str:
    return " ".join(question.lower().split())


def data_version(session) -> str:
    """Fingerprint combining:
    (a) count of delivered lines in FACT_ORDER_LINE,
    (b) MD5 of all ONT_METRIC rows (name + definition + formula),
    (c) MD5 of the semantic-view DDL (SV_SUPPLY_CHAIN),
    (d) MD5 of contract documents (RAW.CONTRACT_DOCS).
    Memoised for ~90 s so it does not run on every click.
    The agent spec cannot be hashed via a scalar subquery (DESCRIBE AGENT
    is not composable); it is excluded.
    """
    now = time.time()
    if _dv_cache["value"] and (now - _dv_cache["ts"]) < _DV_TTL:
        return _dv_cache["value"]
    row = session.sql(
        "SELECT "
        "(SELECT COUNT(*) FROM SC_ONTOLOGY.CURATED.FACT_ORDER_LINE)"
        " || '|' || "
        "(SELECT MD5(LISTAGG(METRIC_NAME || ':' || CANONICAL_DEFINITION || ':' || COALESCE(FORMULA_SQL,''), '|') "
        "  WITHIN GROUP (ORDER BY METRIC_NAME)) FROM SC_ONTOLOGY.ONTOLOGY.ONT_METRIC)"
        " || '|' || "
        "(SELECT MD5(GET_DDL('SEMANTIC VIEW', 'SC_ONTOLOGY.ONTOLOGY.SV_SUPPLY_CHAIN')))"
        " || '|' || "
        "(SELECT MD5(LISTAGG(DOC_ID || ':' || COALESCE(DOC_TEXT,''), '|') "
        "  WITHIN GROUP (ORDER BY DOC_ID)) FROM SC_ONTOLOGY.RAW.CONTRACT_DOCS)"
        " AS dv"
    ).collect()
    val = str(row[0][0]) if row else "unknown"
    _dv_cache["value"] = val
    _dv_cache["ts"] = now
    return val


def lookup(session, question: str, dv: str):
    """Return a dict with ANSWER_TEXT, SQL_TEXT, EVIDENCE (parsed), TOOLS,
    ELAPSED_SECONDS, SAVED_AT, SAVED_HHMI  — or None on miss."""
    key = _normalize(question).replace("'", "''")
    dv_safe = str(dv).replace("'", "''")
    rows = session.sql(
        f"SELECT ANSWER_TEXT, SQL_TEXT, EVIDENCE_JSON, TOOLS, ELAPSED_SECONDS, "
        f"       SAVED_AT, TO_CHAR(SAVED_AT, 'HH24:MI') AS SAVED_HHMI "
        f"FROM SC_ONTOLOGY.GOVERNANCE.ANSWER_CACHE "
        f"WHERE QUESTION_KEY = '{key}' "
        f"  AND DATA_VERSION = '{dv_safe}' "
        f"  AND SAVED_AT > DATEADD(minute, -60, CURRENT_TIMESTAMP()) "
        f"ORDER BY SAVED_AT DESC LIMIT 1"
    ).collect()
    if not rows:
        return None
    r = rows[0]
    evidence = r[2]
    try:
        evidence = json.loads(evidence) if evidence else {}
    except (json.JSONDecodeError, TypeError):
        evidence = {}
    return {
        "ANSWER_TEXT": r[0] or "",
        "SQL_TEXT": r[1] or "",
        "EVIDENCE": evidence,
        "TOOLS": r[3] or "",
        "ELAPSED_SECONDS": float(r[4]) if r[4] is not None else 0.0,
        "SAVED_AT": r[5],
        "SAVED_HHMI": r[6] or "",
    }


def save(session, question: str, answer: str, sql: str, evidence, tools, secs: float, dv: str):
    """Upsert a live answer into the cache."""
    key = _normalize(question)
    ev_json = json.dumps(evidence) if not isinstance(evidence, str) else evidence
    tools_str = ",".join(sorted(tools)) if isinstance(tools, (list, set)) else str(tools)
    def esc(s):
        return str(s).replace("'", "''") if s else ""
    session.sql(
        f"MERGE INTO SC_ONTOLOGY.GOVERNANCE.ANSWER_CACHE t "
        f"USING (SELECT '{esc(key)}' AS qk) s ON t.QUESTION_KEY = s.qk "
        f"WHEN MATCHED THEN UPDATE SET "
        f"  QUESTION_TEXT = '{esc(question)}', ANSWER_TEXT = '{esc(answer)}', "
        f"  SQL_TEXT = '{esc(sql)}', EVIDENCE_JSON = '{esc(ev_json)}', "
        f"  TOOLS = '{esc(tools_str)}', ELAPSED_SECONDS = {secs:.2f}, "
        f"  SAVED_AT = CURRENT_TIMESTAMP(), DATA_VERSION = '{esc(dv)}' "
        f"WHEN NOT MATCHED THEN INSERT "
        f"  (QUESTION_KEY, QUESTION_TEXT, ANSWER_TEXT, SQL_TEXT, EVIDENCE_JSON, TOOLS, ELAPSED_SECONDS, SAVED_AT, DATA_VERSION) "
        f"VALUES ('{esc(key)}', '{esc(question)}', '{esc(answer)}', '{esc(sql)}', "
        f"  '{esc(ev_json)}', '{esc(tools_str)}', {secs:.2f}, CURRENT_TIMESTAMP(), '{esc(dv)}')"
    ).collect()


def delete_one(session, question: str):
    """Remove a single cached answer."""
    key = _normalize(question).replace("'", "''")
    session.sql(f"DELETE FROM SC_ONTOLOGY.GOVERNANCE.ANSWER_CACHE WHERE QUESTION_KEY = '{key}'").collect()


def clear(session):
    """Remove all cached answers."""
    session.sql("DELETE FROM SC_ONTOLOGY.GOVERNANCE.ANSWER_CACHE").collect()
    _dv_cache["value"] = None
    _dv_cache["ts"] = 0.0
