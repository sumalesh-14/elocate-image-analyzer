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


def log_pass1_start(num_categories: int) -> None:
    _section("🧠", f"PASS 1 — Category Identification  ({num_categories} DB categories offered)")


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


def log_pass2_start(category: str, num_brands: int) -> None:
    _section(
        "🏷️ ",
        f"PASS 2 — Brand & Model Identification  ({num_brands} brands offered)",
        color=_MAGENTA,
    )
    _field("For category", category)


def log_pass2_result(brand_raw: Optional[str]) -> None:
    _field("Brand (raw)", brand_raw or "null")


def log_pass3_start(brand: str, num_models: int) -> None:
    _section(
        "📱",
        f"PASS 3 — Model Identification  ({num_models} models offered)",
        color=_YELLOW,
    )
    _field("For brand", brand)


def log_pass3_result(model_raw: Optional[str]) -> None:
    _field("Model (raw)", model_raw or "null")


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
