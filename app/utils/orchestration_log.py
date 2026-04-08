"""
Orchestration console printer.

Prints a clear, emoji-rich, human-readable trace of every step in the
two-pass device analysis pipeline directly to stdout using print().

This is intentionally separate from the structured logger so it always
appears in the terminal regardless of LOG_LEVEL or formatter settings.
"""

import sys
import time
from typing import Optional, List


# ANSI colour codes
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_RESET  = "\033[0m"
_CYAN   = "\033[96m"
_GREEN  = "\033[92m"
_YELLOW = "\033[93m"
_RED    = "\033[91m"
_BLUE   = "\033[94m"
_MAGENTA = "\033[95m"
_WHITE  = "\033[97m"


def _p(line: str) -> None:
    """Print and immediately flush so Railway/Docker sees it in real-time."""
    print(line, flush=True)


def _divider(char: str = "─", width: int = 68) -> None:
    _p(f"{_DIM}{char * width}{_RESET}")


def _section(emoji: str, title: str, color: str = _CYAN) -> None:
    _p(f"\n{color}{_BOLD}{emoji}  {title}{_RESET}")
    _divider()


def _field(label: str, value, indent: int = 4, new_tag: bool = False) -> None:
    tag = f" {_YELLOW}[NEW ✨]{_RESET}" if new_tag else ""
    val_str = str(value) if value is not None else f"{_DIM}null{_RESET}"
    _p(f"{' ' * indent}{_DIM}{label:<22}{_RESET}{_WHITE}{val_str}{_RESET}{tag}")


# ---------------------------------------------------------------------------
# Public API – called from analyzer.py
# ---------------------------------------------------------------------------

def log_request_received(filename: str, file_size: int, content_type: str) -> float:
    """
    Print the opening banner for a new analysis request.
    Returns the start timestamp so elapsed time can be calculated later.
    """
    start = time.time()
    _p(f"\n{_BOLD}{_BLUE}{'═' * 68}{_RESET}")
    _p(f"{_BOLD}{_BLUE}  🔍  NEW DEVICE ANALYSIS REQUEST{_RESET}")
    _p(f"{_BOLD}{_BLUE}{'═' * 68}{_RESET}")
    _field("File", filename)
    _field("Size", f"{file_size / 1024:.1f} KB")
    _field("Content-Type", content_type)
    return start


def log_image_valid(filename: str) -> None:
    _p(f"\n  {_GREEN}✅  Image validated OK{_RESET}  ({filename})")


def log_image_invalid(error_code: str, message: str) -> None:
    _p(f"\n  {_RED}❌  Image validation FAILED{_RESET}")
    _field("Error code", error_code, indent=6)
    _field("Message", message, indent=6)

def log_llm_attempt(llm_name: str) -> None:
    _p(f"\n  {_BLUE}🤖  Routing task to LLM: {_RESET}{_BOLD}{llm_name}{_RESET}")

def log_llm_switched(failed_llm: str, reason: str, next_llm: str) -> None:
    _p(f"  {_YELLOW}⚠️   {failed_llm} failed ({reason}). Switching to {next_llm}...{_RESET}")


def log_pass1_start(num_categories: int, category_names: list = None) -> None:
    _section("🧠", f"PASS 1 — Category Identification  ({num_categories} DB categories offered)")
    if category_names:
        _p(f"  {_DIM}Offering categories:{_RESET}")
        for i, name in enumerate(category_names[:10], 1):  # Show first 10
            _p(f"    {_DIM}{i}.{_RESET} {name}")
        if len(category_names) > 10:
            _p(f"    {_DIM}... and {len(category_names) - 10} more{_RESET}")


def log_pass1_result(
    category_raw: str,
    device_type: str,
    confidence: float,
) -> None:
    conf_color = _GREEN if confidence >= 0.7 else (_YELLOW if confidence >= 0.4 else _RED)
    _field("Raw pick", category_raw)
    _field("Device type", device_type)
    _field("Confidence", f"{conf_color}{confidence:.0%}{_RESET}")


def log_category_resolved(
    name: str,
    is_new: bool,
    score: float,
) -> None:
    if is_new:
        _p(f"\n  {_YELLOW}✨  NEW CATEGORY AUTO-SEEDED{_RESET}")
        _field("Name", name, new_tag=True)
    else:
        _p(f"\n  {_GREEN}✅  Category matched{_RESET}")
        _field("Name", name)
        _field("Match score", f"{score:.0%}")


def log_category_failed(raw_pick: str) -> None:
    _p(f"\n  {_RED}⚠️   Category could not be resolved{_RESET}")
    _field("Raw pick", raw_pick)
    _p(f"     {_DIM}(continuing with raw text — no DB ID){_RESET}")


def log_pass2_start(category: str, num_brands: int, brand_names: list = None) -> None:
    _section(
        "🏷️ ",
        f"PASS 2 — Brand & Model Identification  ({num_brands} brands offered)",
        color=_MAGENTA,
    )
    _field("For category", category)
    if brand_names:
        _p(f"  {_DIM}Offering brands:{_RESET}")
        for i, name in enumerate(brand_names[:10], 1):  # Show first 10
            _p(f"    {_DIM}{i}.{_RESET} {name}")
        if len(brand_names) > 10:
            _p(f"    {_DIM}... and {len(brand_names) - 10} more{_RESET}")


def log_pass2_result(brand_raw: Optional[str]) -> None:
    _field("Brand (raw)", brand_raw or "null")


def log_pass3_start(brand: str, num_models: int, model_names: list = None) -> None:
    _section(
        "📱",
        f"PASS 3 — Model Identification  ({num_models} models offered)",
        color=_YELLOW,
    )
    _field("For brand", brand)
    if model_names:
        _p(f"  {_DIM}Offering models:{_RESET}")
        for i, name in enumerate(model_names[:10], 1):  # Show first 10
            _p(f"    {_DIM}{i}.{_RESET} {name}")
        if len(model_names) > 10:
            _p(f"    {_DIM}... and {len(model_names) - 10} more{_RESET}")


def log_pass3_result(model_raw: Optional[str], uncertainty_reason: Optional[str] = None) -> None:
    _field("Model (raw)", model_raw or "null")
    if uncertainty_reason:
        _p(f"    {_YELLOW}⚠️  Uncertainty:{_RESET} {_DIM}{uncertainty_reason}{_RESET}")


def log_brand_resolved(name: str, is_new: bool, score: float) -> None:
    if is_new:
        _p(f"\n  {_YELLOW}✨  NEW BRAND AUTO-SEEDED{_RESET}")
        _field("Name", name, new_tag=True)
    else:
        _p(f"\n  {_GREEN}✅  Brand matched{_RESET}")
        _field("Name", name)
        _field("Match score", f"{score:.0%}")


def log_brand_failed(raw_pick: Optional[str]) -> None:
    _p(f"\n  {_DIM}⚪  Brand not resolved{_RESET}  (raw='{raw_pick}')")


def log_model_resolved(name: str, is_new: bool, score: float, num_models: int) -> None:
    if is_new:
        _p(f"\n  {_YELLOW}✨  NEW MODEL AUTO-SEEDED{_RESET}")
        _field("Name", name, new_tag=True)
    else:
        _p(f"\n  {_GREEN}✅  Model matched{_RESET}  ({num_models} models were in DB)")
        _field("Name", name)
        _field("Match score", f"{score:.0%}")


def log_model_failed(raw_pick: Optional[str]) -> None:
    _p(f"\n  {_DIM}⚪  Model not resolved{_RESET}  (raw='{raw_pick}')")


def log_final_result(
    start_time: float,
    category: str,
    brand: Optional[str],
    model: Optional[str],
    device_type: str,
    confidence: float,
    db_status: str,
    category_id,
    brand_id,
    model_id,
    category_new: bool,
    brand_new: bool,
    model_new: bool,
    severity: str,
    contains_hazardous: bool,
    contains_precious: bool,
    model_uncertainty_reason: Optional[str] = None,
) -> None:
    elapsed_ms = int((time.time() - start_time) * 1000)

    status_icon = {"success": "🟢", "partial_success": "🟡", "failure": "🔴", "unavailable": "⚫"}.get(db_status, "❓")
    sev_color = {"critical": _RED, "high": _YELLOW, "medium": _CYAN, "low": _GREEN}.get(severity, _WHITE)

    _p(f"\n{_BOLD}{_GREEN}{'═' * 68}{_RESET}")
    _p(f"{_BOLD}{_GREEN}  ✅  ANALYSIS COMPLETE  ({elapsed_ms} ms){_RESET}")
    _p(f"{_BOLD}{_GREEN}{'═' * 68}{_RESET}")

    _section("📦", "DEVICE IDENTITY", _CYAN)
    _field("Category", category, new_tag=category_new)
    _field("Brand", brand or "null", new_tag=brand_new)
    _field("Model", model or "null", new_tag=model_new)
    if model_uncertainty_reason:
        _p(f"    {_YELLOW}⚠️  Why uncertain:{_RESET} {_DIM}{model_uncertainty_reason}{_RESET}")
    _field("Device type", device_type)

    conf_color = _GREEN if confidence >= 0.7 else (_YELLOW if confidence >= 0.4 else _RED)
    _field("Confidence", f"{conf_color}{confidence:.0%}{_RESET}")

    _section("🗄️ ", "DATABASE IDs", _BLUE)
    _field("Category ID", category_id or "—")
    _field("Brand ID", brand_id or "—")
    _field("Model ID", model_id or "—")
    _field("DB status", f"{status_icon} {db_status}")

    _section("⚠️ ", "SAFETY INFO", _YELLOW)
    _field("Severity", f"{sev_color}{severity.upper()}{_RESET}")
    _field("Hazardous materials", "⚠️  YES" if contains_hazardous else "✅ NO")
    _field("Precious metals", "💰 YES" if contains_precious else "❌ NO")

    _p(f"\n{_DIM}{'─' * 68}{_RESET}\n")


def log_error(stage: str, error_code: str, message: str) -> None:
    _p(f"\n{_RED}{_BOLD}❌  ERROR at [{stage}]{_RESET}")
    _field("Code", error_code, indent=6)
    _field("Message", message, indent=6)
    _p(f"{_DIM}{'─' * 68}{_RESET}\n")


# ---------------------------------------------------------------------------
# Material Analysis Logging
# ---------------------------------------------------------------------------

def log_material_analysis_start(
    brand: str,
    model: str,
    category: str,
    country: str
) -> float:
    """
    Print the opening banner for a new material analysis request.
    Returns the start timestamp so elapsed time can be calculated later.
    """
    start = time.time()
    _p(f"\n{_BOLD}{_MAGENTA}{'═' * 68}{_RESET}")
    _p(f"{_BOLD}{_MAGENTA}  🔬  NEW MATERIAL ANALYSIS REQUEST{_RESET}")
    _p(f"{_BOLD}{_MAGENTA}{'═' * 68}{_RESET}")
    _field("Brand", brand)
    _field("Model", model)
    _field("Category", category)
    _field("Country", country)
    return start


def log_material_llm_priority(priority_list: List[str], workers: List[str]) -> None:
    """Log the LLM priority order for material analysis."""
    _section("🎯", "LLM PRIORITY ORDER", _CYAN)
    _field("Priority", " → ".join([p.upper() for p in priority_list]))
    _p(f"\n  {_DIM}Available workers:{_RESET}")
    for i, worker in enumerate(workers, 1):
        _p(f"    {_DIM}{i}.{_RESET} {worker}")


def log_material_llm_attempt(llm_name: str, model: str) -> None:
    """Log attempt to use a specific LLM for material analysis."""
    _p(f"\n  {_BLUE}🤖  Attempting with: {_RESET}{_BOLD}{llm_name}{_RESET} {_DIM}({model}){_RESET}")


def log_material_llm_success(llm_name: str, model: str, material_count: int) -> None:
    """Log successful material analysis."""
    _p(f"  {_GREEN}✅  Success!{_RESET} Found {_BOLD}{material_count}{_RESET} materials")


def log_material_llm_failed(llm_name: str, reason: str, next_llm: Optional[str] = None) -> None:
    """Log failed LLM attempt and fallback."""
    if next_llm:
        _p(f"  {_YELLOW}⚠️   {llm_name} failed ({reason}). Trying {next_llm}...{_RESET}")
    else:
        _p(f"  {_RED}❌  {llm_name} failed ({reason}). No more providers.{_RESET}")


def log_material_results(
    start_time: float,
    materials: List[dict],
    analysis_description: str,
    model_used: str
) -> None:
    """Log the final material analysis results."""
    elapsed_ms = int((time.time() - start_time) * 1000)
    
    _p(f"\n{_BOLD}{_GREEN}{'═' * 68}{_RESET}")
    _p(f"{_BOLD}{_GREEN}  ✅  MATERIAL ANALYSIS COMPLETE  ({elapsed_ms} ms){_RESET}")
    _p(f"{_BOLD}{_GREEN}{'═' * 68}{_RESET}")
    
    _section("💎", "MATERIALS FOUND", _CYAN)
    _p(f"  {_DIM}{analysis_description}{_RESET}\n")
    
    # Separate precious and base materials
    precious = [m for m in materials if m.get('isPrecious') or m.get('is_precious')]
    base = [m for m in materials if not (m.get('isPrecious') or m.get('is_precious'))]
    
    if precious:
        _p(f"  {_YELLOW}💰 PRECIOUS METALS:{_RESET}")
        for mat in precious:
            name = mat.get('materialName') or mat.get('material_name') or 'Unknown'
            qty = mat.get('estimatedQuantityGrams') or mat.get('estimated_quantity_grams')
            rate = mat.get('marketRatePerGram') or mat.get('market_rate_per_gram')
            curr = mat.get('currency') or ''
            found = mat.get('foundIn') or mat.get('found_in') or 'Unknown component'
            _p(f"    {_BOLD}{name}{_RESET}")
            qty_str = f"{qty:.3f}g" if qty is not None else "N/A"
            rate_str = f"{rate:.2f} {curr}/g" if rate is not None else "N/A"
            _p(f"      {_DIM}Quantity:{_RESET} {qty_str}  {_DIM}Rate:{_RESET} {rate_str}")
            _p(f"      {_DIM}Found in:{_RESET} {found}")
    
    if base:
        _p(f"\n  {_CYAN}🔩 BASE MATERIALS:{_RESET}")
        for mat in base:
            name = mat.get('materialName') or mat.get('material_name') or 'Unknown'
            qty = mat.get('estimatedQuantityGrams') or mat.get('estimated_quantity_grams')
            rate = mat.get('marketRatePerGram') or mat.get('market_rate_per_gram')
            curr = mat.get('currency') or ''
            found = mat.get('foundIn') or mat.get('found_in') or 'Unknown component'
            _p(f"    {_BOLD}{name}{_RESET}")
            qty_str = f"{qty:.3f}g" if qty is not None else "N/A"
            rate_str = f"{rate:.2f} {curr}/g" if rate is not None else "N/A"
            _p(f"      {_DIM}Quantity:{_RESET} {qty_str}  {_DIM}Rate:{_RESET} {rate_str}")
            _p(f"      {_DIM}Found in:{_RESET} {found}")
    
    _section("🤖", "ANALYSIS METADATA", _BLUE)
    _field("Model used", model_used)
    _field("Total materials", len(materials))
    _field("Precious metals", len(precious))
    _field("Base materials", len(base))
    
    _p(f"\n{_DIM}{'─' * 68}{_RESET}\n")


def log_material_analysis_error(error_code: str, message: str) -> None:
    """Log material analysis error."""
    _p(f"\n{_RED}{_BOLD}❌  MATERIAL ANALYSIS ERROR{_RESET}")
    _field("Code", error_code, indent=6)
    _field("Message", message, indent=6)
    _p(f"{_DIM}{'─' * 68}{_RESET}\n")


# ---------------------------------------------------------------------------
# Chat / EcoBot Logging
# ---------------------------------------------------------------------------

def log_chat_request(message: str, session_id: Optional[str], has_history: bool) -> float:
    """Print opening banner for a new chat request."""
    start = time.time()
    _p(f"\n{_BOLD}{_CYAN}{'═' * 68}{_RESET}")
    _p(f"{_BOLD}{_CYAN}  💬  NEW ECOBOT CHAT REQUEST{_RESET}")
    _p(f"{_BOLD}{_CYAN}{'═' * 68}{_RESET}")
    _field("Message", message[:80] + ("..." if len(message) > 80 else ""))
    _field("Session ID", session_id or "new")
    _field("Has history", "yes" if has_history else "no")
    return start


def log_chat_off_topic(message: str) -> None:
    """Log when a message is blocked as off-topic."""
    _p(f"\n  {_YELLOW}🚫  OFF-TOPIC BLOCKED (no LLM call){_RESET}")
    _field("Message", message[:80], indent=6)


def log_chat_llm_attempt(llm_name: str) -> None:
    """Log attempt to use a specific LLM for chat."""
    _p(f"\n  {_BLUE}🤖  Routing chat to LLM: {_RESET}{_BOLD}{llm_name}{_RESET}")


def log_chat_llm_switched(failed_llm: str, reason: str, next_llm: str) -> None:
    """Log LLM switch due to failure."""
    _p(f"  {_YELLOW}⚠️   {failed_llm} failed ({reason}). Switching to {next_llm}...{_RESET}")


def log_chat_llm_all_failed() -> None:
    """Log when all LLM workers failed."""
    _p(f"  {_RED}❌  All LLM workers failed for chat request.{_RESET}")


def log_chat_complete(start_time: float, llm_name: str, reply_preview: str) -> None:
    """Log successful chat completion."""
    elapsed_ms = int((time.time() - start_time) * 1000)
    _p(f"\n{_BOLD}{_GREEN}{'═' * 68}{_RESET}")
    _p(f"{_BOLD}{_GREEN}  ✅  ECOBOT RESPONSE READY  ({elapsed_ms} ms){_RESET}")
    _p(f"{_BOLD}{_GREEN}{'═' * 68}{_RESET}")
    _field("LLM used", llm_name)
    _field("Reply preview", reply_preview[:80] + ("..." if len(reply_preview) > 80 else ""))
    _p(f"\n{_DIM}{'─' * 68}{_RESET}\n")


def log_chat_error(error_code: str, message: str) -> None:
    """Log chat error."""
    _p(f"\n{_RED}{_BOLD}❌  ECOBOT CHAT ERROR{_RESET}")
    _field("Code", error_code, indent=6)
    _field("Message", message, indent=6)
    _p(f"{_DIM}{'─' * 68}{_RESET}\n")


# ---------------------------------------------------------------------------
# LLM Request / Response Logging (Chat)
# ---------------------------------------------------------------------------

def log_llm_chat_request(
    system_prompt_preview: str,
    user_message: str,
    history_turns: int,
    worker_name: str,
    role: str,
    facility_id: str = None,
    user_id: str = None,
) -> None:
    """Log the full LLM request payload before sending."""
    _p(f"\n{_BOLD}{_BLUE}{'─' * 68}{_RESET}")
    _p(f"{_BOLD}{_BLUE}  📤  LLM REQUEST  →  {worker_name}{_RESET}")
    _p(f"{_BOLD}{_BLUE}{'─' * 68}{_RESET}")
    _field("Role", role)
    _field("Facility ID", facility_id or "N/A")
    _field("User ID", user_id or "N/A")
    _field("History turns", history_turns)
    _field("System prompt", system_prompt_preview[:120] + ("..." if len(system_prompt_preview) > 120 else ""))
    _field("User message", user_message[:120] + ("..." if len(user_message) > 120 else ""))


def log_llm_chat_response(
    worker_name: str,
    reply_text: str,
    elapsed_ms: int,
) -> None:
    """Log the LLM response after receiving it."""
    _p(f"\n{_BOLD}{_GREEN}{'─' * 68}{_RESET}")
    _p(f"{_BOLD}{_GREEN}  📥  LLM RESPONSE  ←  {worker_name}  ({elapsed_ms} ms){_RESET}")
    _p(f"{_BOLD}{_GREEN}{'─' * 68}{_RESET}")
    # Print full reply in chunks so long responses are readable
    preview = reply_text.strip()
    if len(preview) <= 300:
        _field("Reply", preview)
    else:
        _field("Reply (first 300)", preview[:300] + "...")
        _field("Total length", f"{len(preview)} chars")
    _p(f"{_DIM}{'─' * 68}{_RESET}")


# ---------------------------------------------------------------------------
# Advanced Query Logging (LLM-powered natural language → SQL)
# ---------------------------------------------------------------------------

def log_advanced_query_start(message: str, facility_id: str = None, user_id: str = None) -> float:
    """Opening banner for an advanced natural-language query."""
    start = time.time()
    _p(f"\n{_BOLD}{_CYAN}{'═' * 68}{_RESET}")
    _p(f"{_BOLD}{_CYAN}  🔍  ADVANCED QUERY — NATURAL LANGUAGE → SQL{_RESET}")
    _p(f"{_BOLD}{_CYAN}{'═' * 68}{_RESET}")
    _field("User message", message[:100] + ("..." if len(message) > 100 else ""))
    _field("Facility ID", facility_id or "NOT PROVIDED")
    _field("User ID", user_id or "N/A")
    return start


def log_advanced_step(step_num: int, title: str) -> None:
    """Log a numbered step in the advanced query pipeline."""
    _p(f"\n{_BOLD}{_BLUE}  STEP {step_num} — {title}{_RESET}")
    _p(f"  {_DIM}{'─' * 60}{_RESET}")


def log_llm_intent_request(prompt_preview: str, worker_name: str = "LLM") -> float:
    """Log before sending intent extraction prompt to LLM."""
    start = time.time()
    _p(f"\n  {_BLUE}📤  SENDING TO {worker_name}:{_RESET}")
    _p(f"    {_DIM}Prompt preview:{_RESET} {_WHITE}{prompt_preview[:120]}...{_RESET}")
    return start


def log_llm_intent_response(result: dict, elapsed_ms: int, worker_name: str = "LLM") -> None:
    """Log the raw LLM JSON response for intent extraction."""
    _p(f"\n  {_GREEN}📥  {worker_name} RESPONSE  ({elapsed_ms} ms):{_RESET}")
    for k, v in result.items():
        _p(f"    {_DIM}{k:<28}{_RESET}{_WHITE}{v}{_RESET}")


def log_llm_intent_error(error: str) -> None:
    _p(f"\n  {_RED}❌  LLM INTENT EXTRACTION FAILED:{_RESET} {error}")
    _p(f"  {_YELLOW}⚠️   Falling back to regex extractor{_RESET}")


def log_model_resolution_start(search_term: str) -> None:
    _p(f"\n  {_CYAN}🔎  MODEL RESOLUTION:{_RESET} searching for '{_WHITE}{search_term}{_RESET}'")


def log_model_candidates(candidates: list) -> None:
    _p(f"  {_DIM}Found {len(candidates)} candidate(s) in DB:{_RESET}")
    for c in candidates[:10]:
        _p(f"    {_DIM}•{_RESET} {c.get('brand_name', '')} {c.get('model_name', '')}  {_DIM}[{c.get('model_id', '')[:8]}...]{_RESET}")
    if len(candidates) > 10:
        _p(f"    {_DIM}... and {len(candidates) - 10} more{_RESET}")


def log_model_llm_pick(picked: dict, elapsed_ms: int) -> None:
    if picked.get("model_id"):
        _p(f"\n  {_GREEN}✅  LLM PICKED MODEL  ({elapsed_ms} ms):{_RESET}")
        _p(f"    {_DIM}Brand:{_RESET}  {_WHITE}{picked.get('brand_name')}{_RESET}")
        _p(f"    {_DIM}Model:{_RESET}  {_WHITE}{picked.get('model_name')}{_RESET}")
        _p(f"    {_DIM}ID:{_RESET}     {_WHITE}{picked.get('model_id')}{_RESET}")
    else:
        _p(f"\n  {_YELLOW}⚠️   LLM returned no match — using all {len(picked)} candidates{_RESET}")


def log_model_resolution_none(search_term: str) -> None:
    _p(f"\n  {_RED}❌  NO MODEL FOUND:{_RESET} '{search_term}' not in database")


def log_dynamic_sql(conditions: list, params: list, sql: str) -> None:
    """Log the dynamically built SQL with its WHERE conditions."""
    _p(f"\n  {_CYAN}🔧  DYNAMIC SQL BUILT:{_RESET}")
    _p(f"    {_DIM}WHERE conditions ({len(conditions)}):{_RESET}")
    for c in conditions:
        _p(f"      {_DIM}•{_RESET} {_WHITE}{c}{_RESET}")
    _p(f"\n  {_CYAN}📌  BOUND PARAMS:{_RESET}")
    for i, p in enumerate(params, 1):
        _p(f"    {_DIM}${i} ={_RESET} {_WHITE}{p}{_RESET}")
    _p(f"\n  {_CYAN}📋  FULL SQL:{_RESET}")
    for line in sql.strip().splitlines():
        _p(f"    {_DIM}{line}{_RESET}")


def log_advanced_query_complete(start: float, row_count: int, label: str) -> None:
    elapsed = int((time.time() - start) * 1000)
    _p(f"\n{_BOLD}{_GREEN}{'═' * 68}{_RESET}")
    _p(f"{_BOLD}{_GREEN}  ✅  ADVANCED QUERY COMPLETE  ({elapsed} ms){_RESET}")
    _p(f"{_BOLD}{_GREEN}{'═' * 68}{_RESET}")
    _field("Label", label)
    _field("Rows returned", row_count)
    _p(f"{_DIM}{'─' * 68}{_RESET}\n")


def log_advanced_query_no_results(label: str) -> None:
    _p(f"\n  {_YELLOW}⚠️   NO RESULTS:{_RESET} {label}")
    _divider()


# ---------------------------------------------------------------------------
# LLM Classifier Logging (is_query vs advisory flow)
# ---------------------------------------------------------------------------

def log_classifier_start(message: str, role: str) -> float:
    """Opening banner when the LLM classifier is invoked."""
    start = time.time()
    _p(f"\n{_BOLD}{_MAGENTA}{'═' * 68}{_RESET}")
    _p(f"{_BOLD}{_MAGENTA}  🤖  LLM CLASSIFIER — QUERY vs ADVISORY{_RESET}")
    _p(f"{_BOLD}{_MAGENTA}{'═' * 68}{_RESET}")
    _field("Role", role)
    _field("Message", message[:100] + ("..." if len(message) > 100 else ""))
    return start


def log_classifier_result(result: dict, elapsed_ms: int) -> None:
    """Log the classifier's JSON decision."""
    is_query = result.get("is_query", False)
    intent   = result.get("intent", "—")
    label    = result.get("label", "—")
    icon = f"{_GREEN}✅  IS_QUERY = TRUE{_RESET}" if is_query else f"{_YELLOW}💬  IS_QUERY = FALSE → advisory flow{_RESET}"
    _p(f"\n  {icon}  ({elapsed_ms} ms)")
    _p(f"    {_DIM}{'intent':<22}{_RESET}{_WHITE}{intent}{_RESET}")
    _p(f"    {_DIM}{'label':<22}{_RESET}{_WHITE}{label}{_RESET}")
    # Print all filter fields
    for k, v in result.items():
        if k not in ("is_query", "intent", "label") and v:
            _p(f"    {_DIM}{k:<22}{_RESET}{_WHITE}{v}{_RESET}")
    _divider()


def log_classifier_fallback(reason: str) -> None:
    """Log when classifier fails and regex fallback is used."""
    _p(f"\n  {_YELLOW}⚠️   CLASSIFIER FAILED — using regex fallback{_RESET}")
    _p(f"    {_DIM}Reason:{_RESET} {reason}")
    _divider()


def log_classifier_skipped(reason: str) -> None:
    """Log when classifier is skipped (e.g. request_by_id detected by fast regex)."""
    _p(f"\n  {_CYAN}⚡  FAST-PATH DETECTED:{_RESET} {reason} — skipping classifier")
    _divider()
