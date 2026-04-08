"""
Live query service for the Intermediary Ops Co-Pilot.
All queries are read-only and scoped to the intermediary's facility_id.
"""

import logging
import re
import time
from typing import Optional, List
from app.services.db_connection import db_manager
from app.utils.orchestration_log import (
    log_advanced_query_start, log_advanced_step,
    log_llm_intent_request, log_llm_intent_response, log_llm_intent_error,
    log_model_resolution_start, log_model_candidates, log_model_llm_pick,
    log_model_resolution_none, log_dynamic_sql,
    log_advanced_query_complete, log_advanced_query_no_results,
    log_classifier_start, log_classifier_result,
    log_classifier_fallback, log_classifier_skipped,
)

logger = logging.getLogger(__name__)

_BOLD="\033[1m";_DIM="\033[2m";_RESET="\033[0m";_CYAN="\033[96m"
_GREEN="\033[92m";_YELLOW="\033[93m";_RED="\033[91m";_MAGENTA="\033[95m";_WHITE="\033[97m"

def _p(l): print(l, flush=True)
def _divider(): _p(f"{_DIM}{'─'*68}{_RESET}")

def _log_query_start(intent, facility_id, user_id):
    start = time.time()
    _p(f"\n{_BOLD}{_MAGENTA}{'═'*68}{_RESET}")
    _p(f"{_BOLD}{_MAGENTA}  🗄️   LIVE DB QUERY — {intent.upper().replace('_',' ')}{_RESET}")
    _p(f"{_BOLD}{_MAGENTA}{'═'*68}{_RESET}")
    _p(f"    {_DIM}{'Facility ID':<22}{_RESET}{_WHITE}{facility_id or 'NOT PROVIDED'}{_RESET}")
    _p(f"    {_DIM}{'User ID':<22}{_RESET}{_WHITE}{user_id or 'N/A'}{_RESET}")
    return start

def _log_sql(sql, params):
    _p(f"\n  {_CYAN}📋  SQL QUERY:{_RESET}")
    for line in sql.strip().splitlines():
        _p(f"    {_DIM}{line}{_RESET}")
    if params:
        _p(f"\n  {_CYAN}📌  PARAMS:{_RESET}")
        for i, p in enumerate(params, 1):
            _p(f"    {_DIM}${i} ={_RESET} {_WHITE}{p}{_RESET}")

def _log_result(start, n):
    _p(f"\n  {_GREEN}✅  QUERY COMPLETE{_RESET}  —  {_BOLD}{n} row(s){_RESET}  ({int((time.time()-start)*1000)} ms)")
    _divider()

def _log_err(e):
    _p(f"\n  {_RED}❌  QUERY FAILED:{_RESET} {e}")
    _divider()

# ---------------------------------------------------------------------------
# Intent detection
# ---------------------------------------------------------------------------

def detect_intent(message: str) -> Optional[str]:
    m = message.lower().strip()
    # Request history / timeline
    if re.search(r'\b(r?cy[-\s]?\d{4}[-\s]?\d+|req[-\s]?\d+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', m, re.IGNORECASE):
        if re.search(r'(history|timeline|log|trail|activity|track|progress|journey|what happened)', m):
            return "request_history"
        return "request_by_id"

    # Advanced: device model + condition/status qualifier together
    has_device = bool(re.search(
        r'(iphone|samsung|galaxy|pixel|oneplus|redmi|oppo|vivo|nokia|motorola|macbook|ipad|canon|nikon|sony|lg|dell|hp|lenovo)',
        m
    ))
    has_qualifier = bool(re.search(
        r'(excellent|good|fair|poor|condition|approved|recycled|cancelled|verified|not recycled|pending|completed|failed)',
        m
    ))
    if has_device and has_qualifier:
        return "requests_advanced"
    if re.search(r'(recycle\s*request|request).{0,30}(iphone|samsung|galaxy|pixel|oneplus|redmi|oppo|vivo|nokia|motorola|laptop|macbook|ipad|tablet|tv|refrigerator|washing)', m):
        return "requests_by_model"
    if re.search(r'(iphone|samsung|galaxy|pixel|oneplus|redmi|oppo|vivo|nokia|motorola|macbook|ipad).{0,30}(recycle|request|raised|submitted)', m):
        return "requests_by_model"
    if re.search(r'(driver).{0,40}(current|working on|handling|doing|active job|active task|on pickup)', m):
        return "driver_current_job"
    if re.search(r'(current|working on|handling).{0,30}(driver)', m):
        return "driver_current_job"
    if re.search(r'(driver).{0,30}(available|availability|free|idle|busy|status)', m):
        return "driver_availability"
    if re.search(r'(available|free|idle).{0,20}driver', m):
        return "driver_availability"
    if re.search(r'(list|show|all|which).{0,20}driver', m):
        return "driver_availability"
    if re.search(r'(recycle\s*request|request).{0,30}(pending|completed|in.transit|assigned|failed|dropped|rejected)', m):
        return "requests_by_status"
    if re.search(r'(pending|completed|in.transit|failed|dropped|rejected).{0,30}(recycle|request)', m):
        return "requests_by_status"
    if re.search(r'(show|list|all).{0,20}(recycle\s*request|request)', m):
        return "requests_all"
    if re.search(r'request.{0,30}(assigned to|for driver|by driver)', m):
        return "requests_by_driver"
    return None


# ---------------------------------------------------------------------------
# LLM Classifier — replaces regex detect_intent for intermediary role
# ---------------------------------------------------------------------------

_CLASSIFIER_PROMPT = """You are a query classifier for an e-waste recycling platform used by facility managers.

Your job: decide if the user's message is a DATABASE QUERY (needs live data) or an ADVISORY question (answered from knowledge).

DATABASE QUERY examples:
- "Show me all pending requests"
- "What are iPhone 14 requests with GOOD condition?"
- "Show me EXCELLENT condition requests that are approved"
- "Which drivers are available?"
- "What is driver Ravi working on?"
- "Give me details for RCY-2026-000046"
- "Show me all recycle requests"
- "What are completed requests?"
- "Show me requests for Canon EOS"

ADVISORY examples:
- "How do I export Form-6?"
- "What are the CPCB filing deadlines?"
- "How do I assign a driver?"
- "What vehicle type suits large appliances?"
- "Navigate to collections page"

DB SCHEMA (for query classification):
- condition_code: EXCELLENT, GOOD, FAIR, POOR
- status (RecycleStatus): CREATED, APPROVED, VERIFIED, LOCKED, RECYCLED, REJECTED, CANCELLED, REMINDER_SENT
- fulfillment_status (FulfillmentStatus): PICKUP_REQUESTED, PICKUP_ASSIGNED, PICKUP_IN_PROGRESS, PICKUP_COMPLETED, PICKUP_FAILED, DROP_PENDING, DROPPED_AT_FACILITY, DROP_VERIFIED, REJECTED

User message: "{message}"

Return ONLY valid JSON, no markdown fences:
{{
  "is_query": true,
  "intent": "requests_advanced",
  "model_search": "iPhone 14",
  "condition_include": ["GOOD"],
  "condition_exclude": [],
  "status_include": ["APPROVED"],
  "status_exclude": ["RECYCLED"],
  "fulfillment_include": [],
  "fulfillment_exclude": [],
  "request_id": null,
  "driver_name": null,
  "label": "iPhone 14 — Good condition, Approved, not Recycled"
}}

Intent values:
- "requests_advanced"   → filtered requests (model/condition/status combo)
- "requests_by_status"  → filter by status/fulfillment only (no model)
- "requests_all"        → all requests, no filter
- "request_by_id"       → single request by RCY number or UUID (full details)
- "request_history"     → status change timeline/history for a specific request
- "requests_by_model"   → requests for a specific device model only
- "driver_availability" → list all drivers + status
- "driver_current_job"  → what is a specific driver working on
- "requests_by_driver"  → all requests assigned to a driver

If is_query is false, set intent to null and all filter fields to null/[].
Return ONLY the JSON object.
"""


async def classify_message(message: str, role: str = "intermediary") -> dict:
    """
    LLM-first classifier: determines if message is a DB query or advisory.
    Returns full classification dict including all extracted filters.
    Falls back to regex detect_intent on failure.
    """
    start = log_classifier_start(message, role)

    try:
        from app.services.llm_router import llm_service
        if not llm_service.workers:
            raise RuntimeError("No LLM workers available")

        prompt = _CLASSIFIER_PROMPT.format(message=message)
        llm_t = time.time()
        result = await llm_service.generate_text_only(prompt)
        elapsed = int((time.time() - llm_t) * 1000)

        classified = result if isinstance(result, dict) else {}
        # Ensure required keys exist
        classified.setdefault("is_query", False)
        classified.setdefault("intent", None)
        classified.setdefault("label", message[:60])

        log_classifier_result(classified, elapsed)
        return classified

    except Exception as e:
        log_classifier_fallback(str(e))
        logger.warning(f"LLM classifier failed: {e} — falling back to regex")
        # Regex fallback
        intent = detect_intent(message)
        if intent:
            return {"is_query": True, "intent": intent, "label": message[:60]}
        return {"is_query": False, "intent": None, "label": message[:60]}


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------

def extract_model_name(message: str) -> str:
    patterns = [
        r'(iphone\s*\d+\s*(?:pro|plus|max|mini)?)',
        r'(galaxy\s*[a-z]\d+\s*(?:ultra|plus|fe)?)',
        r'(pixel\s*\d+\s*(?:pro|a)?)',
        r'(macbook\s*(?:pro|air|mini)?(?:\s*\d+)?)',
        r'(ipad\s*(?:pro|air|mini)?(?:\s*\d+)?)',
        r'(oneplus\s*\d+\s*(?:pro|t)?)',
        r'(redmi\s*(?:note\s*)?\d+\s*(?:pro|plus)?)',
        r'(oppo\s*[a-z]\d+)', r'(nokia\s*\d+)',
        r'(motorola\s*(?:moto\s*)?[a-z]\d+)',
    ]
    msg_lower = message.lower()
    for p in patterns:
        hit = re.search(p, msg_lower)
        if hit:
            return hit.group(1).strip()
    hit = re.search(r'(?:for|of)\s+([a-z0-9 ]+?)(?:\s+recycle|\s+request|$)', msg_lower)
    return hit.group(1).strip() if hit else ""


def extract_status(message: str) -> List[str]:
    """Fast regex fallback — used when LLM parse_status_intent is unavailable."""
    m = message.lower()
    if any(w in m for w in ["pending", "new request", "unassigned", "not assigned", "show all"]):
        return ["PICKUP_REQUESTED", "DROP_PENDING"]
    if any(w in m for w in ["assigned", "driver assigned"]):
        return ["PICKUP_ASSIGNED"]
    if any(w in m for w in ["in progress", "in transit", "on the way", "ongoing", "active pickup"]):
        return ["PICKUP_IN_PROGRESS"]
    if any(w in m for w in ["completed", "done", "picked up", "pickup completed", "finished"]):
        return ["PICKUP_COMPLETED", "DROP_VERIFIED"]
    if any(w in m for w in ["failed", "failure", "unsuccessful", "missed"]):
        return ["PICKUP_FAILED"]
    if any(w in m for w in ["drop pending", "drop-off pending", "waiting to drop"]):
        return ["DROP_PENDING"]
    if any(w in m for w in ["dropped at", "dropped off", "dropped_at_facility"]):
        return ["DROPPED_AT_FACILITY"]
    if any(w in m for w in ["drop verified", "drop_verified"]):
        return ["DROP_VERIFIED"]
    if "rejected" in m:
        return ["REJECTED"]
    return ["PICKUP_REQUESTED", "PICKUP_ASSIGNED", "PICKUP_IN_PROGRESS", "DROP_PENDING", "DROPPED_AT_FACILITY"]


# LLM-based status intent parser
_STATUS_PARSE_PROMPT = """You are a query parser for an e-waste recycling platform database.

The recycle_request table has TWO status columns:
1. `status` (RecycleStatus) — business outcome:
   Values: CREATED, APPROVED, VERIFIED, LOCKED, RECYCLED, REJECTED, CANCELLED, REMINDER_SENT

2. `fulfillment_status` (FulfillmentStatus) — logistics tracking:
   Values: PICKUP_REQUESTED, PICKUP_ASSIGNED, PICKUP_IN_PROGRESS, PICKUP_COMPLETED, PICKUP_FAILED,
           DROP_PENDING, DROPPED_AT_FACILITY, DROP_VERIFIED, REJECTED

User message: "{message}"

Return ONLY valid JSON, no markdown fences:
{{"status_values": [], "fulfillment_status_values": [], "label": "short description"}}

Rules:
- Pickup/drop logistics questions → fulfillment_status_values
- Business outcome questions (approved, recycled, cancelled, verified) → status_values
- Both can be populated if both apply
- Empty arrays [] means no filter on that column
- label = short human-readable description of the filter
"""


async def parse_status_intent(message: str) -> dict:
    """Use LLM to parse natural language into exact DB filter values. Falls back to regex."""
    try:
        from app.services.llm_router import llm_service
        result = await llm_service.generate_text_only(_STATUS_PARSE_PROMPT.format(message=message))
        parsed = result if isinstance(result, dict) else {}
        sv = parsed.get("status_values") or []
        fv = parsed.get("fulfillment_status_values") or []
        label = parsed.get("label") or "requests"
        _p(f"\n  {_CYAN}🧠  LLM STATUS PARSE:{_RESET} status={sv} fulfillment={fv} label='{label}'")
        return {"status_values": sv, "fulfillment_status_values": fv, "label": label}
    except Exception as e:
        logger.warning(f"LLM status parse failed, using regex: {e}")
        fv = extract_status(message)
        return {"status_values": [], "fulfillment_status_values": fv, "label": " / ".join(fv)}


def extract_request_id(message: str) -> str:
    # UUID
    hit = re.search(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', message.lower())
    if hit: return hit.group(0)
    # RCY-2026-000046 or CY-2026-000046 (common typo) style
    hit = re.search(r'(r?cy[-\s]?\d{4}[-\s]?\d+)', message, re.IGNORECASE)
    if hit:
        val = hit.group(1).upper().replace(" ", "-")
        # Normalise CY- → RCY-
        if not val.startswith("RCY"):
            val = "RCY" + val[2:] if val.startswith("CY") else val
        return val
    # REQ-001 style (legacy)
    hit = re.search(r'(req[-\s]?\d+)', message, re.IGNORECASE)
    if hit: return hit.group(1).upper().replace(" ", "-")
    # "request id/number XYZ"
    hit = re.search(r'request\s*(?:id|number|#)\s*([\w-]+)', message, re.IGNORECASE)
    return hit.group(1) if hit else ""


def extract_driver_name(message: str) -> str:
    hit = re.search(r'driver\s+(?:named?\s+)?([a-z][a-z\s]{1,30}?)(?:\s+is|\s+has|\s+current|$|\?)', message, re.IGNORECASE)
    return hit.group(1).strip() if hit else ""


# ---------------------------------------------------------------------------
# DB fetch helper
# ---------------------------------------------------------------------------

async def _fetch(sql: str, params: tuple, intent: str, facility_id, user_id):
    if not db_manager.is_available():
        _p(f"\n  {_RED}❌  DB unavailable{_RESET}")
        return None
    start = _log_query_start(intent, facility_id, user_id)
    _log_sql(sql, params)
    try:
        async with db_manager.pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            result = [dict(r) for r in rows]
            _log_result(start, len(result))
            return result
    except Exception as e:
        _log_err(e)
        logger.error(f"Live query [{intent}] error: {e}")
        return None


# ---------------------------------------------------------------------------
# Query: driver availability
# ---------------------------------------------------------------------------

async def query_driver_availability(facility_id, user_id) -> str:
    if facility_id:
        sql = """
            SELECT d.name, d.phone, d.vehicle_type, d.vehicle_number, d.availability,
                COUNT(rr.id) FILTER (WHERE rr.fulfillment_status NOT IN
                    ('PICKUP_COMPLETED','PICKUP_FAILED','DROP_VERIFIED','REJECTED')) AS active_jobs
            FROM public.driver d
            LEFT JOIN public.recycle_request rr ON rr.assigned_driver_id = d.id
            WHERE d.facility_id = $1
            GROUP BY d.id ORDER BY d.availability, d.name
        """
        params = (facility_id,)
    else:
        sql = """
            SELECT d.name, d.phone, d.vehicle_type, d.vehicle_number, d.availability,
                COUNT(rr.id) FILTER (WHERE rr.fulfillment_status NOT IN
                    ('PICKUP_COMPLETED','PICKUP_FAILED','DROP_VERIFIED','REJECTED')) AS active_jobs
            FROM public.driver d
            LEFT JOIN public.recycle_request rr ON rr.assigned_driver_id = d.id
            GROUP BY d.id ORDER BY d.availability, d.name
        """
        params = ()
    rows = await _fetch(sql, params, "driver_availability", facility_id, user_id)
    if rows is None: return "⚠️ Database is currently unreachable."
    if not rows: return "No drivers are registered under your facility yet."
    lines = [
        "Here is the current driver status for your facility\n",
        "| Driver | Vehicle | Number | Status | Active Jobs | Phone |",
        "|--------|---------|--------|--------|-------------|-------|",
    ]
    for r in rows:
        icon = "🟢" if r["availability"] == "AVAILABLE" else "🔴"
        lines.append(
            f"| {icon} **{r['name']}** | {r['vehicle_type']} | {r['vehicle_number']} "
            f"| **{r['availability']}** | {r['active_jobs']} | 📞 {r['phone']} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Query: driver current job
# ---------------------------------------------------------------------------

async def query_driver_current_job(driver_name: str, facility_id, user_id) -> str:
    name_filter = f"%{driver_name}%" if driver_name else "%"
    terminal = ('PICKUP_COMPLETED', 'PICKUP_FAILED', 'DROP_VERIFIED', 'REJECTED')
    if facility_id:
        sql = """
            SELECT d.name AS driver_name, d.vehicle_type, d.availability,
                rr.request_number, rr.fulfillment_status, rr.pickup_date,
                dm.model_name AS device_model, u.full_name AS citizen_name, u.mobile_number AS citizen_phone
            FROM public.driver d
            LEFT JOIN public.recycle_request rr
                ON rr.assigned_driver_id = d.id AND rr.fulfillment_status != ALL($3::text[])
            LEFT JOIN public.device_model dm ON dm.id = rr.device_model_id
            LEFT JOIN public."user" u ON u.id = rr.user_id
            WHERE d.name ILIKE $1 AND d.facility_id = $2
            ORDER BY d.name, rr.created_at DESC
        """
        params = (name_filter, facility_id, list(terminal))
    else:
        sql = """
            SELECT d.name AS driver_name, d.vehicle_type, d.availability,
                rr.request_number, rr.fulfillment_status, rr.pickup_date,
                dm.model_name AS device_model, u.full_name AS citizen_name, u.mobile_number AS citizen_phone
            FROM public.driver d
            LEFT JOIN public.recycle_request rr
                ON rr.assigned_driver_id = d.id AND rr.fulfillment_status != ALL($2::text[])
            LEFT JOIN public.device_model dm ON dm.id = rr.device_model_id
            LEFT JOIN public."user" u ON u.id = rr.user_id
            WHERE d.name ILIKE $1
            ORDER BY d.name, rr.created_at DESC
        """
        params = (name_filter, list(terminal))
    rows = await _fetch(sql, params, "driver_current_job", facility_id, user_id)
    if rows is None: return "⚠️ Database is currently unreachable."
    if not rows: return f"No driver found matching **{driver_name}**." if driver_name else "No drivers found."
    lines = []
    for r in rows:
        if r["request_number"]:
            lines.append(f"**{r['driver_name']}** ({r['vehicle_type']}) — Active Assignment\n")
            lines.append(f"- **Request:** {r['request_number']}")
            lines.append(f"- **Status:** {r['fulfillment_status']}")
            lines.append(f"- **Device:** {r['device_model']}")
            lines.append(f"- **Pickup Date:** {r['pickup_date'] or 'TBD'}")
            lines.append(f"- **Citizen:** {r['citizen_name']} | 📞 {r['citizen_phone']}")
        else:
            lines.append(f"- **{r['driver_name']}** ({r['vehicle_type']}) — Status: **{r['availability']}** | No active assignment.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Query: requests by model
# ---------------------------------------------------------------------------

async def query_requests_by_model(model_name: str, facility_id, user_id) -> str:
    if not model_name: return "Please specify a device model name (e.g. 'iPhone 14', 'Galaxy S23')."
    if facility_id:
        sql = """
            SELECT rr.request_number, rr.fulfillment_status, rr.pickup_date,
                rr.estimated_amount, rr.final_amount, dm.model_name AS device_model,
                u.full_name AS citizen_name, d.name AS driver_name
            FROM public.recycle_request rr
            JOIN public.device_model dm ON dm.id = rr.device_model_id
            JOIN public."user" u ON u.id = rr.user_id
            LEFT JOIN public.driver d ON d.id = rr.assigned_driver_id
            WHERE dm.model_name ILIKE $1 AND rr.recycling_facility_id = $2
            ORDER BY rr.created_at DESC LIMIT 20
        """
        params = (f"%{model_name}%", facility_id)
    else:
        sql = """
            SELECT rr.request_number, rr.fulfillment_status, rr.pickup_date,
                rr.estimated_amount, rr.final_amount, dm.model_name AS device_model,
                u.full_name AS citizen_name, d.name AS driver_name
            FROM public.recycle_request rr
            JOIN public.device_model dm ON dm.id = rr.device_model_id
            JOIN public."user" u ON u.id = rr.user_id
            LEFT JOIN public.driver d ON d.id = rr.assigned_driver_id
            WHERE dm.model_name ILIKE $1
            ORDER BY rr.created_at DESC LIMIT 20
        """
        params = (f"%{model_name}%",)
    rows = await _fetch(sql, params, "requests_by_model", facility_id, user_id)
    if rows is None: return "⚠️ Database is currently unreachable."
    if not rows: return f"No recycle requests found for **{model_name}** at your facility."
    lines = [
        f"Found **{len(rows)}** recycle request(s) for **{model_name}**\n",
        "| Request # | Device | Status | Citizen | Driver | Amount | Pickup |",
        "|-----------|--------|--------|---------|--------|--------|--------|",
    ]
    for r in rows:
        amt = f"₹{r['final_amount']}" if r['final_amount'] else (f"~₹{r['estimated_amount']}" if r['estimated_amount'] else "N/A")
        lines.append(
            f"| **{r['request_number']}** | {r['device_model']} | {r['fulfillment_status']} "
            f"| {r['citizen_name']} | {r['driver_name'] or 'Unassigned'} | {amt} | {r['pickup_date'] or 'TBD'} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Query: request by ID
# ---------------------------------------------------------------------------

async def query_request_by_id(request_id: str, facility_id, user_id) -> str:
    if not request_id: return "Please provide a valid request number or ID."
    if facility_id:
        sql = """
            SELECT rr.request_number, rr.fulfillment_status, rr.condition_code, rr.pickup_date,
                rr.estimated_amount, rr.final_amount, rr.fulfillment_type, rr.driver_comments, rr.certificate_url,
                dm.model_name AS device_model, db2.name AS brand_name,
                u.full_name AS citizen_name, u.mobile_number AS citizen_phone, u.email AS citizen_email,
                d.name AS driver_name, d.phone AS driver_phone, d.vehicle_type, d.vehicle_number,
                rf.name AS facility_name
            FROM public.recycle_request rr
            JOIN public.device_model dm ON dm.id = rr.device_model_id
            JOIN public.device_brand db2 ON db2.id = dm.brand_id
            JOIN public."user" u ON u.id = rr.user_id
            LEFT JOIN public.driver d ON d.id = rr.assigned_driver_id
            LEFT JOIN public.recycling_facility rf ON rf.id = rr.recycling_facility_id
            WHERE (rr.request_number ILIKE $1 OR rr.id::text = $1) AND rr.recycling_facility_id = $2
            LIMIT 1
        """
        params = (request_id, facility_id)
    else:
        sql = """
            SELECT rr.request_number, rr.fulfillment_status, rr.condition_code, rr.pickup_date,
                rr.estimated_amount, rr.final_amount, rr.fulfillment_type, rr.driver_comments, rr.certificate_url,
                dm.model_name AS device_model, db2.name AS brand_name,
                u.full_name AS citizen_name, u.mobile_number AS citizen_phone, u.email AS citizen_email,
                d.name AS driver_name, d.phone AS driver_phone, d.vehicle_type, d.vehicle_number,
                rf.name AS facility_name
            FROM public.recycle_request rr
            JOIN public.device_model dm ON dm.id = rr.device_model_id
            JOIN public.device_brand db2 ON db2.id = dm.brand_id
            JOIN public."user" u ON u.id = rr.user_id
            LEFT JOIN public.driver d ON d.id = rr.assigned_driver_id
            LEFT JOIN public.recycling_facility rf ON rf.id = rr.recycling_facility_id
            WHERE rr.request_number ILIKE $1 OR rr.id::text = $1
            LIMIT 1
        """
        params = (request_id,)
    rows = await _fetch(sql, params, "request_by_id", facility_id, user_id)
    if rows is None: return "⚠️ Database is currently unreachable."
    if not rows: return f"No recycle request found with ID **{request_id}** at your facility."
    r = rows[0]
    driver_info = (f"**{r['driver_name']}** — {r['vehicle_type']} ({r['vehicle_number']}) | 📞 {r['driver_phone']}"
                   if r['driver_name'] else "Not yet assigned")
    cert = f"[Download Certificate]({r['certificate_url']})" if r['certificate_url'] else "Not issued yet"
    est = f"₹{r['estimated_amount']}" if r['estimated_amount'] else "N/A"
    final = f"₹{r['final_amount']}" if r['final_amount'] else "Pending"

    lines = [
        f"**Request {r['request_number']}** — Full Details\n",
        f"- **Device:** {r['brand_name']} {r['device_model']} ({r['condition_code']})",
        f"- **Type:** {r['fulfillment_type']}",
        f"- **Status:** {r['fulfillment_status']}",
        f"- **Pickup Date:** {r['pickup_date'] or 'TBD'}",
        f"- **Estimated Amount:** {est}",
        f"- **Final Amount:** {final}",
        f"- **Citizen:** {r['citizen_name']}",
        f"- **Phone:** 📞 {r['citizen_phone']}",
        f"- **Email:** ✉️ {r['citizen_email'] or 'N/A'}",
        f"- **Assigned Driver:** {driver_info}",
        f"- **Facility:** {r['facility_name'] or 'N/A'}",
        f"- **Certificate:** {cert}",
    ]
    if r['driver_comments']:
        lines.append(f"- **Driver Notes:** {r['driver_comments']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Query: request status history / timeline
# ---------------------------------------------------------------------------

async def query_request_history(request_id: str, facility_id, user_id) -> str:
    if not request_id:
        return "Please provide a request number (e.g. RCY-2026-000045)."

    # First resolve the request UUID from the request_number
    if facility_id:
        id_sql = """
            SELECT rr.id, rr.request_number, rr.status, rr.fulfillment_status,
                dm.model_name AS device_model, db2.name AS brand_name,
                u.full_name AS citizen_name
            FROM public.recycle_request rr
            JOIN public.device_model dm ON dm.id = rr.device_model_id
            JOIN public.device_brand db2 ON db2.id = dm.brand_id
            JOIN public."user" u ON u.id = rr.user_id
            WHERE (rr.request_number ILIKE $1 OR rr.id::text = $1)
              AND rr.recycling_facility_id = $2
            LIMIT 1
        """
        id_params = (request_id, facility_id)
    else:
        id_sql = """
            SELECT rr.id, rr.request_number, rr.status, rr.fulfillment_status,
                dm.model_name AS device_model, db2.name AS brand_name,
                u.full_name AS citizen_name
            FROM public.recycle_request rr
            JOIN public.device_model dm ON dm.id = rr.device_model_id
            JOIN public.device_brand db2 ON db2.id = dm.brand_id
            JOIN public."user" u ON u.id = rr.user_id
            WHERE rr.request_number ILIKE $1 OR rr.id::text = $1
            LIMIT 1
        """
        id_params = (request_id,)

    req_rows = await _fetch(id_sql, id_params, "request_history_lookup", facility_id, user_id)
    if req_rows is None: return "⚠️ Database is currently unreachable."
    if not req_rows: return f"No request found with ID **{request_id}** at your facility."

    req = req_rows[0]
    req_uuid = str(req["id"])

    # Fetch full history
    history_sql = """
        SELECT
            h.changed_at,
            h.status_type,
            h.old_status,
            h.new_status,
            h.comments,
            h.changed_by_name
        FROM public.recycle_status_history h
        WHERE h.recycle_request_id = $1
        ORDER BY h.changed_at ASC
    """
    hist_rows = await _fetch(history_sql, (req_uuid,), "request_history_events", facility_id, user_id)
    if hist_rows is None: return "⚠️ Database is currently unreachable."

    # Header
    lines = [
        f"**{req['request_number']}** — Status History\n",
        f"- **Device:** {req['brand_name']} {req['device_model']}",
        f"- **Citizen:** {req['citizen_name']}",
        f"- **Current Status:** {req['status']} / {req['fulfillment_status']}\n",
    ]

    if not hist_rows:
        lines.append("No status history recorded yet.")
        return "\n".join(lines)

    # Status icons
    _ICONS = {
        "CREATED": "🆕", "APPROVED": "✅", "VERIFIED": "🔍", "RECYCLED": "♻️",
        "CANCELLED": "❌", "REJECTED": "🚫", "LOCKED": "🔒", "REMINDER_SENT": "📧",
        "PICKUP_REQUESTED": "📋", "PICKUP_ASSIGNED": "🚗", "PICKUP_IN_PROGRESS": "🚚",
        "PICKUP_COMPLETED": "📦", "PICKUP_FAILED": "⚠️",
        "DROP_PENDING": "⏳", "DROPPED_AT_FACILITY": "🏭", "DROP_VERIFIED": "✅",
    }

    lines.append("| # | Time | Type | From | To | By | Notes |")
    lines.append("|---|------|------|------|----|----|-------|")

    for i, h in enumerate(hist_rows, 1):
        ts = str(h["changed_at"])[:16].replace("T", " ") if h["changed_at"] else "—"
        old = h["old_status"] or "—"
        new = h["new_status"] or "—"
        icon = _ICONS.get(new, "•")
        stype = h["status_type"] or "—"
        by = h["changed_by_name"] or "System"
        notes = (h["comments"] or "")[:40] + ("..." if h["comments"] and len(h["comments"]) > 40 else "")
        lines.append(f"| {i} | {ts} | {stype} | {old} | {icon} {new} | {by} | {notes} |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Query: requests by status  (uses ANY($n) with real enum values)
# ---------------------------------------------------------------------------

async def query_requests_by_status(statuses: List[str], facility_id, user_id) -> str:
    if not statuses:
        return ("Please specify a status. Examples:\n"
                "- **pending** → PICKUP_REQUESTED / DROP_PENDING\n"
                "- **assigned** → PICKUP_ASSIGNED\n"
                "- **in progress** → PICKUP_IN_PROGRESS\n"
                "- **completed** → PICKUP_COMPLETED / DROP_VERIFIED\n"
                "- **failed** → PICKUP_FAILED\n"
                "- **dropped** → DROPPED_AT_FACILITY\n"
                "- **rejected** → REJECTED")

    _STATUS_LABELS = {
        "PICKUP_REQUESTED": "Pickup Requested", "PICKUP_ASSIGNED": "Pickup Assigned",
        "PICKUP_IN_PROGRESS": "In Progress", "PICKUP_COMPLETED": "Pickup Completed",
        "PICKUP_FAILED": "Pickup Failed", "DROP_PENDING": "Drop Pending",
        "DROPPED_AT_FACILITY": "Dropped at Facility", "DROP_VERIFIED": "Drop Verified",
        "REJECTED": "Rejected",
    }
    label = " / ".join(_STATUS_LABELS.get(s, s) for s in statuses)
    if facility_id:
        sql = """
            SELECT rr.request_number, rr.status, rr.fulfillment_status, rr.pickup_date,
                dm.model_name AS device_model, u.full_name AS citizen_name, d.name AS driver_name
            FROM public.recycle_request rr
            JOIN public.device_model dm ON dm.id = rr.device_model_id
            JOIN public."user" u ON u.id = rr.user_id
            LEFT JOIN public.driver d ON d.id = rr.assigned_driver_id
            WHERE rr.fulfillment_status = ANY($1) AND rr.recycling_facility_id = $2
            ORDER BY rr.created_at DESC LIMIT 50
        """
        params = (statuses, facility_id)
    else:
        sql = """
            SELECT rr.request_number, rr.status, rr.fulfillment_status, rr.pickup_date,
                dm.model_name AS device_model, u.full_name AS citizen_name, d.name AS driver_name
            FROM public.recycle_request rr
            JOIN public.device_model dm ON dm.id = rr.device_model_id
            JOIN public."user" u ON u.id = rr.user_id
            LEFT JOIN public.driver d ON d.id = rr.assigned_driver_id
            WHERE rr.fulfillment_status = ANY($1)
            ORDER BY rr.created_at DESC LIMIT 50
        """
        params = (statuses,)
    rows = await _fetch(sql, params, "requests_by_status", facility_id, user_id)
    if rows is None: return "⚠️ Database is currently unreachable."
    if not rows: return f"No recycle requests found with status **{label}** at your facility."
    lines = [
        f"Found **{len(rows)}** request(s) — **{label}**\n",
        "| Request # | Device | Status | Fulfillment | Citizen | Driver | Pickup |",
        "|-----------|--------|--------|-------------|---------|--------|--------|",
    ]
    for r in rows:
        lines.append(
            f"| **{r['request_number']}** | {r['device_model']} | {r['status']} | {r['fulfillment_status']} "
            f"| {r['citizen_name']} | {r['driver_name'] or 'Unassigned'} | {r['pickup_date'] or 'TBD'} |"
        )
    return "\n".join(lines)


async def query_requests_by_status_intent(intent: dict, facility_id, user_id) -> str:
    """
    LLM-parsed version — filters on status, fulfillment_status, or both.
    Falls back to fulfillment_status-only if only one array is populated.
    """
    sv = intent.get("status_values") or []
    fv = intent.get("fulfillment_status_values") or []
    label = intent.get("label") or "requests"

    # Build WHERE conditions dynamically
    conditions = []
    params: list = []
    idx = 1

    if sv:
        conditions.append(f"rr.status = ANY(${idx})")
        params.append(sv); idx += 1
    if fv:
        conditions.append(f"rr.fulfillment_status = ANY(${idx})")
        params.append(fv); idx += 1
    if facility_id:
        conditions.append(f"rr.recycling_facility_id = ${idx}")
        params.append(facility_id); idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT rr.request_number, rr.status, rr.fulfillment_status, rr.pickup_date,
            dm.model_name AS device_model, u.full_name AS citizen_name, d.name AS driver_name
        FROM public.recycle_request rr
        JOIN public.device_model dm ON dm.id = rr.device_model_id
        JOIN public."user" u ON u.id = rr.user_id
        LEFT JOIN public.driver d ON d.id = rr.assigned_driver_id
        {where}
        ORDER BY rr.created_at DESC LIMIT 50
    """
    rows = await _fetch(sql, tuple(params), f"requests_by_status_intent({label})", facility_id, user_id)
    if rows is None: return "⚠️ Database is currently unreachable."
    if not rows: return f"No recycle requests found for **{label}** at your facility."
    lines = [
        f"Found **{len(rows)}** request(s) — **{label}**\n",
        "| Request # | Device | Status | Fulfillment | Citizen | Driver | Pickup |",
        "|-----------|--------|--------|-------------|---------|--------|--------|",
    ]
    for r in rows:
        lines.append(
            f"| **{r['request_number']}** | {r['device_model']} | {r['status']} | {r['fulfillment_status']} "
            f"| {r['citizen_name']} | {r['driver_name'] or 'Unassigned'} | {r['pickup_date'] or 'TBD'} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Query: requests by driver
# ---------------------------------------------------------------------------

async def query_requests_by_driver(driver_name: str, facility_id, user_id) -> str:
    name_filter = f"%{driver_name}%" if driver_name else "%"
    if facility_id:
        sql = """
            SELECT rr.request_number, rr.fulfillment_status, rr.pickup_date,
                dm.model_name AS device_model, u.full_name AS citizen_name, d.name AS driver_name
            FROM public.recycle_request rr
            JOIN public.device_model dm ON dm.id = rr.device_model_id
            JOIN public."user" u ON u.id = rr.user_id
            JOIN public.driver d ON d.id = rr.assigned_driver_id
            WHERE d.name ILIKE $1 AND d.facility_id = $2
            ORDER BY rr.created_at DESC LIMIT 20
        """
        params = (name_filter, facility_id)
    else:
        sql = """
            SELECT rr.request_number, rr.fulfillment_status, rr.pickup_date,
                dm.model_name AS device_model, u.full_name AS citizen_name, d.name AS driver_name
            FROM public.recycle_request rr
            JOIN public.device_model dm ON dm.id = rr.device_model_id
            JOIN public."user" u ON u.id = rr.user_id
            JOIN public.driver d ON d.id = rr.assigned_driver_id
            WHERE d.name ILIKE $1
            ORDER BY rr.created_at DESC LIMIT 20
        """
        params = (name_filter,)
    rows = await _fetch(sql, params, "requests_by_driver", facility_id, user_id)
    if rows is None: return "⚠️ Database is currently unreachable."
    if not rows: return f"No requests found for driver **{driver_name}** at your facility."
    lines = [
        f"Requests assigned to **{driver_name}**\n",
        "| Request # | Device | Status | Citizen | Pickup |",
        "|-----------|--------|--------|---------|--------|",
    ]
    for r in rows:
        lines.append(
            f"| **{r['request_number']}** | {r['device_model']} | {r['fulfillment_status']} "
            f"| {r['citizen_name']} | {r['pickup_date'] or 'TBD'} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Query: all requests (no status filter)
# ---------------------------------------------------------------------------

async def query_requests_all(facility_id, user_id) -> str:
    if facility_id:
        sql = """
            SELECT rr.request_number, rr.status, rr.fulfillment_status, rr.pickup_date,
                dm.model_name AS device_model, u.full_name AS citizen_name, d.name AS driver_name
            FROM public.recycle_request rr
            JOIN public.device_model dm ON dm.id = rr.device_model_id
            JOIN public."user" u ON u.id = rr.user_id
            LEFT JOIN public.driver d ON d.id = rr.assigned_driver_id
            WHERE rr.recycling_facility_id = $1
            ORDER BY rr.created_at DESC LIMIT 50
        """
        params = (facility_id,)
    else:
        sql = """
            SELECT rr.request_number, rr.status, rr.fulfillment_status, rr.pickup_date,
                dm.model_name AS device_model, u.full_name AS citizen_name, d.name AS driver_name
            FROM public.recycle_request rr
            JOIN public.device_model dm ON dm.id = rr.device_model_id
            JOIN public."user" u ON u.id = rr.user_id
            LEFT JOIN public.driver d ON d.id = rr.assigned_driver_id
            ORDER BY rr.created_at DESC LIMIT 50
        """
        params = ()
    rows = await _fetch(sql, params, "requests_all", facility_id, user_id)
    if rows is None: return "⚠️ Database is currently unreachable."
    if not rows: return "No recycle requests found at your facility."
    lines = [
        f"Found **{len(rows)}** recycle request(s) at your facility\n",
        "| Request # | Device | Status | Fulfillment | Citizen | Driver | Pickup |",
        "|-----------|--------|--------|-------------|---------|--------|--------|",
    ]
    for r in rows:
        lines.append(
            f"| **{r['request_number']}** | {r['device_model']} | {r['status']} | {r['fulfillment_status']} "
            f"| {r['citizen_name']} | {r['driver_name'] or 'Unassigned'} | {r['pickup_date'] or 'TBD'} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Advanced query — LLM extracts filters, DB resolves model IDs
# ---------------------------------------------------------------------------

_ADVANCED_QUERY_PROMPT = """You are a query parser for an e-waste recycling platform database.

SCHEMA CONTEXT:
- recycle_request has: condition_code, status (RecycleStatus), fulfillment_status (FulfillmentStatus)
- condition_code values: EXCELLENT, GOOD, FAIR, POOR
- status values: CREATED, APPROVED, VERIFIED, LOCKED, RECYCLED, REJECTED, CANCELLED, REMINDER_SENT
- fulfillment_status values: PICKUP_REQUESTED, PICKUP_ASSIGNED, PICKUP_IN_PROGRESS, PICKUP_COMPLETED,
  PICKUP_FAILED, DROP_PENDING, DROPPED_AT_FACILITY, DROP_VERIFIED, REJECTED

USER MESSAGE: "{message}"

Extract all filters the user wants. Return ONLY valid JSON, no markdown:
{{
  "model_search": "iPhone 14",
  "condition_include": ["GOOD", "EXCELLENT"],
  "condition_exclude": [],
  "status_include": ["APPROVED"],
  "status_exclude": ["RECYCLED", "CANCELLED"],
  "fulfillment_include": [],
  "fulfillment_exclude": [],
  "label": "iPhone 14 — Good/Excellent condition, Approved, not Recycled"
}}

Rules:
- model_search: device model name as mentioned by user, or null if not specified
- condition_include: condition codes to include (empty = no filter)
- condition_exclude: condition codes to exclude (empty = no filter)
- status_include: RecycleStatus values to include (empty = no filter)
- status_exclude: RecycleStatus values to exclude (empty = no filter)
- fulfillment_include: FulfillmentStatus values to include (empty = no filter)
- fulfillment_exclude: FulfillmentStatus values to exclude (empty = no filter)
- label: short human-readable description of the combined filter
- Return ONLY the JSON object, nothing else.
"""

_MODEL_PICK_PROMPT = """You are matching a user's device description to the closest entry in a database.

User asked for: "{search}"

Available models in database:
{model_list}

Pick the single best match. Return ONLY valid JSON, no markdown:
{{"model_id": "<uuid>", "model_name": "<name>", "brand_name": "<brand>"}}

If nothing is a reasonable match, return: {{"model_id": null, "model_name": null, "brand_name": null}}
"""


async def _resolve_model_ids(model_search: str) -> list[dict]:
    """
    Step 1: fuzzy fetch candidates from DB.
    Step 2: if multiple, ask LLM to pick the best one.
    Returns list of dicts with model_id, model_name, brand_name.
    """
    if not model_search or not db_manager.is_available():
        return []

    log_model_resolution_start(model_search)

    # Fetch candidates
    words = model_search.strip().split()
    like = "%" + "%".join(words) + "%"
    try:
        async with db_manager.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT dm.id::text AS model_id, dm.model_name, db2.name AS brand_name
                FROM public.device_model dm
                JOIN public.device_brand db2 ON db2.id = dm.brand_id
                WHERE (dm.model_name ILIKE $1 OR db2.name ILIKE $2)
                  AND dm.is_active = true
                ORDER BY dm.model_name
                LIMIT 20
            """, like, f"%{words[0]}%")
            candidates = [dict(r) for r in rows]
    except Exception as e:
        logger.error(f"Model resolution DB error: {e}")
        return []

    if not candidates:
        log_model_resolution_none(model_search)
        return []

    log_model_candidates(candidates)

    if len(candidates) == 1:
        _p(f"\n  {_GREEN}✅  Single match — no LLM needed{_RESET}")
        return candidates

    # Multiple candidates — ask LLM to pick best
    try:
        from app.services.llm_router import llm_service
        model_list = "\n".join(
            f"- id={r['model_id']} | {r['brand_name']} {r['model_name']}"
            for r in candidates
        )
        prompt = _MODEL_PICK_PROMPT.format(search=model_search, model_list=model_list)
        llm_start = log_llm_intent_request(prompt[:120], worker_name="LLM Router (model pick)")
        result = await llm_service.generate_text_only(prompt)
        picked = result if isinstance(result, dict) else {}
        elapsed = int((time.time() - llm_start) * 1000)
        log_model_llm_pick(picked, elapsed)
        if picked.get("model_id"):
            return [picked]
        return candidates
    except Exception as e:
        logger.warning(f"LLM model pick failed: {e}")
        _p(f"\n  {_YELLOW}⚠️   LLM model pick failed ({e}) — using all {len(candidates)} candidates{_RESET}")
        return candidates


async def query_requests_advanced(message: str, facility_id, user_id) -> str:
    """
    Full LLM-powered advanced query with step-by-step orchestration logging:
    Step 1 — LLM extracts all filters from natural language
    Step 2 — DB resolves model name → model_id(s), LLM picks best match
    Step 3 — Dynamic SQL built from filters
    Step 4 — Execute and return results
    """
    overall_start = log_advanced_query_start(message, facility_id, user_id)

    # ── STEP 1: LLM Intent Extraction ──────────────────────────────────────
    log_advanced_step(1, "LLM INTENT EXTRACTION")
    intent = {}
    try:
        from app.services.llm_router import llm_service
        prompt = _ADVANCED_QUERY_PROMPT.format(message=message)
        llm_start = log_llm_intent_request(prompt[:120], worker_name="LLM Router")
        intent_result = await llm_service.generate_text_only(prompt)
        intent = intent_result if isinstance(intent_result, dict) else {}
        elapsed = int((time.time() - llm_start) * 1000)
        log_llm_intent_response(intent, elapsed, worker_name="LLM Router")
    except Exception as e:
        log_llm_intent_error(str(e))
        logger.warning(f"Advanced query LLM intent failed: {e}")

    model_search = intent.get("model_search") or ""
    cond_inc     = intent.get("condition_include") or []
    cond_exc     = intent.get("condition_exclude") or []
    status_inc   = intent.get("status_include") or []
    status_exc   = intent.get("status_exclude") or []
    fulfill_inc  = intent.get("fulfillment_include") or []
    fulfill_exc  = intent.get("fulfillment_exclude") or []
    label        = intent.get("label") or message[:60]

    # ── STEP 2: Model ID Resolution ─────────────────────────────────────────
    model_ids = []
    if model_search:
        log_advanced_step(2, f"MODEL ID RESOLUTION — '{model_search}'")
        resolved = await _resolve_model_ids(model_search)
        model_ids = [r["model_id"] for r in resolved if r.get("model_id")]
        if not model_ids:
            log_model_resolution_none(model_search)
            log_advanced_query_no_results(label)
            return f"No device model found matching **{model_search}** in the database."
    else:
        log_advanced_step(2, "MODEL ID RESOLUTION — skipped (no model specified)")

    # ── STEP 3: Build Dynamic SQL ────────────────────────────────────────────
    log_advanced_step(3, "DYNAMIC SQL CONSTRUCTION")
    conditions = []
    params: list = []
    idx = 1

    if model_ids:
        conditions.append(f"rr.device_model_id = ANY(${idx}::uuid[])")
        params.append(model_ids); idx += 1
    if cond_inc:
        conditions.append(f"rr.condition_code = ANY(${idx})")
        params.append(cond_inc); idx += 1
    if cond_exc:
        conditions.append(f"rr.condition_code != ALL(${idx})")
        params.append(cond_exc); idx += 1
    if status_inc:
        conditions.append(f"rr.status = ANY(${idx})")
        params.append(status_inc); idx += 1
    if status_exc:
        conditions.append(f"rr.status != ALL(${idx})")
        params.append(status_exc); idx += 1
    if fulfill_inc:
        conditions.append(f"rr.fulfillment_status = ANY(${idx})")
        params.append(fulfill_inc); idx += 1
    if fulfill_exc:
        conditions.append(f"rr.fulfillment_status != ALL(${idx})")
        params.append(fulfill_exc); idx += 1
    if facility_id:
        conditions.append(f"rr.recycling_facility_id = ${idx}")
        params.append(facility_id); idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT
            rr.request_number,
            db2.name AS brand_name,
            dm.model_name AS device_model,
            rr.condition_code,
            rr.status,
            rr.fulfillment_status,
            rr.estimated_amount,
            rr.final_amount,
            u.full_name AS citizen_name,
            d.name AS driver_name,
            rr.pickup_date
        FROM public.recycle_request rr
        JOIN public.device_model dm ON dm.id = rr.device_model_id
        JOIN public.device_brand db2 ON db2.id = dm.brand_id
        JOIN public."user" u ON u.id = rr.user_id
        LEFT JOIN public.driver d ON d.id = rr.assigned_driver_id
        {where}
        ORDER BY rr.created_at DESC
        LIMIT 50
    """
    log_dynamic_sql(conditions, params, sql)

    # ── STEP 4: Execute Query ────────────────────────────────────────────────
    log_advanced_step(4, "EXECUTE QUERY")
    rows = await _fetch(sql, tuple(params), "requests_advanced", facility_id, user_id)

    if rows is None:
        return "⚠️ Database is currently unreachable."
    if not rows:
        log_advanced_query_no_results(label)
        return f"No recycle requests found for: **{label}**"

    log_advanced_query_complete(overall_start, len(rows), label)

    lines = [
        f"Found **{len(rows)}** request(s) — **{label}**\n",
        "| Request # | Device | Condition | Status | Fulfillment | Amount | Citizen | Driver | Pickup |",
        "|-----------|--------|-----------|--------|-------------|--------|---------|--------|--------|",
    ]
    for r in rows:
        amt = f"₹{r['final_amount']}" if r['final_amount'] else (f"~₹{r['estimated_amount']}" if r['estimated_amount'] else "N/A")
        lines.append(
            f"| **{r['request_number']}** | {r['brand_name']} {r['device_model']} | {r['condition_code']} "
            f"| {r['status']} | {r['fulfillment_status']} | {amt} "
            f"| {r['citizen_name']} | {r['driver_name'] or 'Unassigned'} | {r['pickup_date'] or 'TBD'} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main dispatcher
# ---------------------------------------------------------------------------

async def run_live_query(intent: str, message: str, facility_id=None, user_id=None) -> str:
    """Legacy dispatcher — used by regex fallback path."""
    if intent == "driver_availability":
        return await query_driver_availability(facility_id, user_id)
    if intent == "driver_current_job":
        return await query_driver_current_job(extract_driver_name(message), facility_id, user_id)
    if intent == "requests_advanced":
        return await query_requests_advanced(message, facility_id, user_id)
    if intent == "requests_by_model":
        return await query_requests_by_model(extract_model_name(message), facility_id, user_id)
    if intent == "request_by_id":
        return await query_request_by_id(extract_request_id(message), facility_id, user_id)
    if intent == "request_history":
        return await query_request_history(extract_request_id(message), facility_id, user_id)
    if intent == "requests_by_status":
        parsed = await parse_status_intent(message)
        return await query_requests_by_status_intent(parsed, facility_id, user_id)
    if intent == "requests_all":
        return await query_requests_all(facility_id, user_id)
    if intent == "requests_by_driver":
        return await query_requests_by_driver(extract_driver_name(message), facility_id, user_id)
    return ""


async def run_live_query_from_classification(classified: dict, message: str, facility_id=None, user_id=None) -> str:
    """
    Primary dispatcher — uses filters already extracted by the LLM classifier.
    Avoids a second LLM call for advanced queries since filters are pre-extracted.
    """
    intent = classified.get("intent")

    if intent == "driver_availability":
        return await query_driver_availability(facility_id, user_id)

    if intent == "driver_current_job":
        driver_name = classified.get("driver_name") or extract_driver_name(message)
        return await query_driver_current_job(driver_name, facility_id, user_id)

    if intent == "request_by_id":
        req_id = classified.get("request_id") or extract_request_id(message)
        return await query_request_by_id(req_id, facility_id, user_id)

    if intent == "request_history":
        req_id = classified.get("request_id") or extract_request_id(message)
        return await query_request_history(req_id, facility_id, user_id)

    if intent == "requests_all":
        return await query_requests_all(facility_id, user_id)

    if intent == "requests_by_driver":
        driver_name = classified.get("driver_name") or extract_driver_name(message)
        return await query_requests_by_driver(driver_name, facility_id, user_id)

    if intent == "requests_by_model":
        model_search = classified.get("model_search") or extract_model_name(message)
        return await query_requests_by_model(model_search, facility_id, user_id)

    if intent == "requests_by_status":
        # Build intent dict from classifier output
        sv = classified.get("status_include") or []
        fv = classified.get("fulfillment_include") or []
        # If status_exclude given but no include, treat as "all except excluded"
        label = classified.get("label") or message[:60]
        status_intent = {"status_values": sv, "fulfillment_status_values": fv, "label": label}
        return await query_requests_by_status_intent(status_intent, facility_id, user_id)

    if intent == "requests_advanced":
        # Classifier already extracted all filters — pass directly, skip second LLM call
        overall_start = log_advanced_query_start(message, facility_id, user_id)

        model_search = classified.get("model_search") or ""
        cond_inc     = classified.get("condition_include") or []
        cond_exc     = classified.get("condition_exclude") or []
        status_inc   = classified.get("status_include") or []
        status_exc   = classified.get("status_exclude") or []
        fulfill_inc  = classified.get("fulfillment_include") or []
        fulfill_exc  = classified.get("fulfillment_exclude") or []
        label        = classified.get("label") or message[:60]

        # Step 2 — Resolve model IDs if needed
        model_ids = []
        if model_search:
            log_advanced_step(2, f"MODEL ID RESOLUTION — '{model_search}'")
            resolved = await _resolve_model_ids(model_search)
            model_ids = [r["model_id"] for r in resolved if r.get("model_id")]
            if not model_ids:
                log_model_resolution_none(model_search)
                return f"No device model found matching **{model_search}** in the database."
        else:
            log_advanced_step(2, "MODEL ID RESOLUTION — skipped (no model specified)")

        # Step 3 — Build dynamic SQL
        log_advanced_step(3, "DYNAMIC SQL CONSTRUCTION")
        conditions = []
        params: list = []
        idx = 1

        if model_ids:
            conditions.append(f"rr.device_model_id = ANY(${idx}::uuid[])")
            params.append(model_ids); idx += 1
        if cond_inc:
            conditions.append(f"rr.condition_code = ANY(${idx})")
            params.append(cond_inc); idx += 1
        if cond_exc:
            conditions.append(f"rr.condition_code != ALL(${idx})")
            params.append(cond_exc); idx += 1
        if status_inc:
            conditions.append(f"rr.status = ANY(${idx})")
            params.append(status_inc); idx += 1
        if status_exc:
            conditions.append(f"rr.status != ALL(${idx})")
            params.append(status_exc); idx += 1
        if fulfill_inc:
            conditions.append(f"rr.fulfillment_status = ANY(${idx})")
            params.append(fulfill_inc); idx += 1
        if fulfill_exc:
            conditions.append(f"rr.fulfillment_status != ALL(${idx})")
            params.append(fulfill_exc); idx += 1
        if facility_id:
            conditions.append(f"rr.recycling_facility_id = ${idx}")
            params.append(facility_id); idx += 1

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"""
            SELECT rr.request_number, db2.name AS brand_name, dm.model_name AS device_model,
                rr.condition_code, rr.status, rr.fulfillment_status,
                rr.estimated_amount, rr.final_amount,
                u.full_name AS citizen_name, d.name AS driver_name, rr.pickup_date
            FROM public.recycle_request rr
            JOIN public.device_model dm ON dm.id = rr.device_model_id
            JOIN public.device_brand db2 ON db2.id = dm.brand_id
            JOIN public."user" u ON u.id = rr.user_id
            LEFT JOIN public.driver d ON d.id = rr.assigned_driver_id
            {where}
            ORDER BY rr.created_at DESC LIMIT 50
        """
        log_dynamic_sql(conditions, params, sql)

        # Step 4 — Execute
        log_advanced_step(4, "EXECUTE QUERY")
        rows = await _fetch(sql, tuple(params), "requests_advanced", facility_id, user_id)
        if rows is None: return "⚠️ Database is currently unreachable."
        if not rows:
            log_advanced_query_no_results(label)
            return f"No recycle requests found for: **{label}**"

        log_advanced_query_complete(overall_start, len(rows), label)
        lines = [
            f"Found **{len(rows)}** request(s) — **{label}**\n",
            "| Request # | Device | Condition | Status | Fulfillment | Amount | Citizen | Driver | Pickup |",
            "|-----------|--------|-----------|--------|-------------|--------|---------|--------|--------|",
        ]
        for r in rows:
            amt = f"₹{r['final_amount']}" if r['final_amount'] else (f"~₹{r['estimated_amount']}" if r['estimated_amount'] else "N/A")
            lines.append(
                f"| **{r['request_number']}** | {r['brand_name']} {r['device_model']} | {r['condition_code']} "
                f"| {r['status']} | {r['fulfillment_status']} | {amt} "
                f"| {r['citizen_name']} | {r['driver_name'] or 'Unassigned'} | {r['pickup_date'] or 'TBD'} |"
            )
        return "\n".join(lines)

    return ""

