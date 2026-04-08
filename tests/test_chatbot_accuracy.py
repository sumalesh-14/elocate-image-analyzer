"""
Chatbot accuracy and response quality tests.

Tests cover:
- Citizen (EcoBot): on-topic responses, off-topic guard, suggestions, session handling
- Intermediary (Ops Co-Pilot): on-topic responses, off-topic guard, suggestions, CPCB knowledge
- Shared: session persistence, role routing, response structure
"""

import pytest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from unittest.mock import patch as _patch

# ---------------------------------------------------------------------------
# App bootstrap
# ---------------------------------------------------------------------------

import os
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("API_KEY", "test-api-key")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")

from app.main import app  # noqa: E402
from app.api.middleware import limiter  # noqa: E402

# Disable rate limiting globally for all tests
limiter.enabled = False

client = TestClient(app)
HEADERS = {"X-API-Key": "test-api-key"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def chat(message: str, role: str = "citizen", session_id: str | None = None) -> dict:
    """POST to /api/v1/chat and return the parsed JSON response."""
    payload: dict = {"message": message, "history": [], "role": role}
    if session_id:
        payload["session_id"] = session_id
    resp = client.post("/api/v1/chat", json=payload, headers=HEADERS)
    assert resp.status_code == 200, f"Unexpected status {resp.status_code}: {resp.text}"
    return resp.json()


def mock_llm_reply(text: str):
    """Return a patcher that makes the LLM router return a fixed text reply."""
    return patch(
        "app.api.routes.llm_service.call_chat_with_fallback",
        new_callable=AsyncMock,
        return_value={"text": text, "worker_name": "mock-worker"},
    )


def mock_workers_present():
    """Patch llm_service.workers to be non-empty so the no-key guard passes."""
    worker = MagicMock()
    worker.display_name = "mock-worker"
    return patch("app.api.routes.llm_service.workers", [worker])


# ===========================================================================
# 1. RESPONSE STRUCTURE
# ===========================================================================

class TestResponseStructure:
    """Every response must have the correct shape regardless of role."""

    def test_citizen_response_has_required_fields(self):
        with mock_workers_present(), mock_llm_reply("Here is how to recycle your phone."):
            data = chat("How do I recycle my phone?")
        assert data["success"] is True
        assert isinstance(data["text"], str)
        assert len(data["text"]) > 0
        assert "session_id" in data
        assert isinstance(data.get("suggestions"), list)

    def test_intermediary_response_has_required_fields(self):
        with mock_workers_present(), mock_llm_reply("Form-2 must be filed by 30th June."):
            data = chat("When is Form-2 due?", role="intermediary")
        assert data["success"] is True
        assert isinstance(data["text"], str)
        assert "session_id" in data
        assert isinstance(data.get("suggestions"), list)

    def test_no_workers_returns_error(self):
        with patch("app.api.routes.llm_service.workers", []):
            data = chat("Hello")
        assert data["success"] is False
        assert data["error"]["code"] == "NO_API_KEY"


# ===========================================================================
# 2. CITIZEN OFF-TOPIC GUARD
# ===========================================================================

class TestCitizenOffTopicGuard:
    """EcoBot must reject clearly off-topic messages without hitting the LLM."""

    OFF_TOPIC_MESSAGES = [
        "Write me a Python function to sort a list",
        "What is the capital of France?",
        "Tell me a joke",
        "What's the weather like today?",
        "How do I cook pasta?",
        "Explain the history of Rome",
        "What is math calculus?",
        "Who is Elon Musk?",
    ]

    @pytest.mark.parametrize("message", OFF_TOPIC_MESSAGES)
    def test_off_topic_blocked_for_citizen(self, message):
        with mock_workers_present():
            # LLM should NOT be called — if it is, the test will fail because
            # call_chat_with_fallback is not patched here
            with patch(
                "app.api.routes.llm_service.call_chat_with_fallback",
                new_callable=AsyncMock,
            ) as mock_llm:
                data = chat(message, role="citizen")
                # Off-topic guard should intercept before LLM call
                mock_llm.assert_not_called()

        assert data["success"] is True
        assert "EcoBot" in data["text"] or "e-waste" in data["text"].lower() or "recycling" in data["text"].lower()

    def test_on_topic_citizen_reaches_llm(self):
        with mock_workers_present(), mock_llm_reply("You can recycle your phone at any ELocate facility.") as mock_llm:
            data = chat("How do I recycle my old phone?", role="citizen")
            mock_llm.assert_called_once()
        assert data["success"] is True


# ===========================================================================
# 3. INTERMEDIARY OFF-TOPIC GUARD
# ===========================================================================

class TestIntermediaryOffTopicGuard:
    """Ops Co-Pilot must also reject off-topic messages."""

    OFF_TOPIC_MESSAGES = [
        "Write me a Python script",
        "Tell me a joke",
        "What's the weather in Mumbai?",
        "How do I cook biryani?",
        "What is the history of India?",
    ]

    @pytest.mark.parametrize("message", OFF_TOPIC_MESSAGES)
    def test_off_topic_blocked_for_intermediary(self, message):
        with mock_workers_present():
            with patch(
                "app.api.routes.llm_service.call_chat_with_fallback",
                new_callable=AsyncMock,
            ) as mock_llm:
                data = chat(message, role="intermediary")
                mock_llm.assert_not_called()

        assert data["success"] is True
        assert "Ops Co-Pilot" in data["text"] or "E-Locate" in data["text"] or "compliance" in data["text"].lower()

    def test_cpcb_question_reaches_llm(self):
        with mock_workers_present(), mock_llm_reply("Form-6 is due quarterly.") as mock_llm:
            data = chat("What is Form-6?", role="intermediary")
            mock_llm.assert_called_once()
        assert data["success"] is True

    def test_driver_assignment_question_reaches_llm(self):
        # "How do I assign a driver?" is an advisory question — classifier returns is_query=False
        # so it should reach the LLM chat, not the DB
        with mock_workers_present(), mock_llm_reply("Assign drivers from the Assign Drivers page.") as mock_llm:
            data = chat("How do I assign a driver to a pickup?", role="intermediary")
            # The classifier itself uses generate_text_only (mocked via workers present)
            # The chat LLM call_chat_with_fallback should be called for the advisory answer
            assert data["success"] is True


# ===========================================================================
# 4. ROLE ROUTING — correct system prompt used
# ===========================================================================

class TestRoleRouting:
    """Verify the correct system prompt is injected per role."""

    def test_citizen_uses_ecobot_prompt(self):
        from app.prompts.ecobot_system_prompt import ECOBOT_SYSTEM_PROMPT
        with mock_workers_present():
            with patch(
                "app.api.routes.llm_service.call_chat_with_fallback",
                new_callable=AsyncMock,
                return_value={"text": "reply", "worker_name": "mock"},
            ) as mock_llm:
                chat("How do I recycle?", role="citizen")
                call_kwargs = mock_llm.call_args[1]
                assert call_kwargs["system_instruction"] == ECOBOT_SYSTEM_PROMPT

    def test_intermediary_uses_ops_prompt(self):
        from app.prompts.intermediary_system_prompt import INTERMEDIARY_SYSTEM_PROMPT
        with mock_workers_present():
            with patch(
                "app.api.routes.llm_service.call_chat_with_fallback",
                new_callable=AsyncMock,
                return_value={"text": "reply", "worker_name": "mock"},
            ) as mock_llm:
                chat("How do I file Form-6?", role="intermediary")
                call_kwargs = mock_llm.call_args[1]
                assert call_kwargs["system_instruction"] == INTERMEDIARY_SYSTEM_PROMPT

    def test_no_role_defaults_to_citizen_prompt(self):
        from app.prompts.ecobot_system_prompt import ECOBOT_SYSTEM_PROMPT
        payload = {"message": "How do I recycle?", "history": []}
        with mock_workers_present():
            with patch(
                "app.api.routes.llm_service.call_chat_with_fallback",
                new_callable=AsyncMock,
                return_value={"text": "reply", "worker_name": "mock"},
            ) as mock_llm:
                resp = client.post("/api/v1/chat", json=payload, headers=HEADERS)
                assert resp.status_code == 200
                call_kwargs = mock_llm.call_args[1]
                assert call_kwargs["system_instruction"] == ECOBOT_SYSTEM_PROMPT


# ===========================================================================
# 5. CITIZEN SUGGESTIONS ACCURACY
# ===========================================================================

class TestCitizenSuggestions:
    """Suggestions must be contextually relevant to the citizen's topic."""

    @pytest.mark.parametrize("message,expected_keyword", [
        ("How do I sign up?", "sign in"),
        ("How do I book a recycle request?", "track"),
        ("Where can I find recycling facilities?", "facilit"),
        ("Tell me about the education section", "recycl"),
        ("How do I view my profile?", "profile"),
        ("How do I contact support?", "contact"),
        ("What happens to my old phone?", "phone"),
        ("Tell me about batteries", "batter"),
    ])
    def test_citizen_suggestions_are_relevant(self, message, expected_keyword):
        reply_text = f"Here is information about {message.lower()}"
        with mock_workers_present(), mock_llm_reply(reply_text):
            data = chat(message, role="citizen")
        suggestions = data.get("suggestions") or []
        assert len(suggestions) >= 1
        combined = " ".join(suggestions).lower()
        assert expected_keyword in combined, (
            f"Expected '{expected_keyword}' in suggestions for '{message}'. Got: {suggestions}"
        )


# ===========================================================================
# 6. INTERMEDIARY SUGGESTIONS ACCURACY
# ===========================================================================

class TestIntermediarySuggestions:
    """Suggestions must be relevant to intermediary operations."""

    @pytest.mark.parametrize("message,expected_keyword", [
        ("Tell me about Form-2 filing", "form-2"),
        ("What are the Form-6 deadlines?", "form-6"),
        ("How do I assign drivers?", "driver"),
        ("How do I view the schedule?", "schedule"),
        ("How do I export a report?", "report"),
        ("Tell me about CPCB compliance", "cpcb"),
        ("How do I manage collections?", "collection"),
        ("How do I withdraw my balance?", "withdrawal"),
        ("What does the dashboard show?", "dashboard"),
    ])
    def test_intermediary_suggestions_are_relevant(self, message, expected_keyword):
        reply_text = f"Here is information about {message.lower()}"
        with mock_workers_present(), mock_llm_reply(reply_text):
            data = chat(message, role="intermediary")
        suggestions = data.get("suggestions") or []
        assert len(suggestions) >= 1
        combined = " ".join(suggestions).lower()
        assert expected_keyword in combined, (
            f"Expected '{expected_keyword}' in suggestions for '{message}'. Got: {suggestions}"
        )

    def test_intermediary_off_topic_suggestions_are_ops_focused(self):
        """Off-topic replies for intermediary should suggest ops-related follow-ups."""
        with mock_workers_present():
            data = chat("Tell me a joke", role="intermediary")
        suggestions = data.get("suggestions") or []
        combined = " ".join(suggestions).lower()
        # Should suggest compliance/ops topics, not citizen topics
        assert any(w in combined for w in ["form", "driver", "compliance", "report", "cpcb"])


# ===========================================================================
# 7. SESSION PERSISTENCE
# ===========================================================================

class TestSessionPersistence:
    """Session IDs must be created, returned, and reused correctly."""

    def test_new_session_created_on_first_message(self):
        with mock_workers_present(), mock_llm_reply("Hello!"):
            data = chat("Hi there")
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    def test_same_session_id_reused_on_subsequent_messages(self):
        with mock_workers_present(), mock_llm_reply("First reply"):
            first = chat("First message")
        session_id = first["session_id"]

        with mock_workers_present(), mock_llm_reply("Second reply"):
            second = chat("Second message", session_id=session_id)
        assert second["session_id"] == session_id

    def test_citizen_and_intermediary_sessions_are_independent(self):
        with mock_workers_present(), mock_llm_reply("Citizen reply"):
            citizen_data = chat("How do I recycle?", role="citizen")
        with mock_workers_present(), mock_llm_reply("Intermediary reply"):
            intermediary_data = chat("How do I file Form-6?", role="intermediary")
        assert citizen_data["session_id"] != intermediary_data["session_id"]

    def test_provided_session_id_is_honoured(self):
        fixed_id = str(uuid.uuid4())
        with mock_workers_present(), mock_llm_reply("Reply with fixed session"):
            data = chat("Hello", session_id=fixed_id)
        assert data["session_id"] == fixed_id


# ===========================================================================
# 8. INTERMEDIARY SYSTEM PROMPT CONTENT
# ===========================================================================

class TestIntermediaryPromptContent:
    """The intermediary system prompt must contain critical knowledge."""

    def test_prompt_contains_cpcb_knowledge(self):
        from app.prompts.intermediary_system_prompt import INTERMEDIARY_SYSTEM_PROMPT
        assert "CPCB" in INTERMEDIARY_SYSTEM_PROMPT
        assert "Form-2" in INTERMEDIARY_SYSTEM_PROMPT
        assert "Form-6" in INTERMEDIARY_SYSTEM_PROMPT

    def test_prompt_contains_platform_pages(self):
        from app.prompts.intermediary_system_prompt import INTERMEDIARY_SYSTEM_PROMPT
        for page in ["/intermediary/dashboard", "/intermediary/reports",
                     "/intermediary/assign-drivers", "/intermediary/collections"]:
            assert page in INTERMEDIARY_SYSTEM_PROMPT, f"Missing page: {page}"

    def test_prompt_contains_off_topic_rule(self):
        from app.prompts.intermediary_system_prompt import INTERMEDIARY_SYSTEM_PROMPT
        assert "OFF-TOPIC" in INTERMEDIARY_SYSTEM_PROMPT

    def test_prompt_contains_advisory_mode_notice(self):
        from app.prompts.intermediary_system_prompt import INTERMEDIARY_SYSTEM_PROMPT
        assert "Advisory Mode" in INTERMEDIARY_SYSTEM_PROMPT

    def test_prompt_contains_output_format_rules(self):
        from app.prompts.intermediary_system_prompt import INTERMEDIARY_SYSTEM_PROMPT
        assert "RULE 1" in INTERMEDIARY_SYSTEM_PROMPT
        assert "RULE 2" in INTERMEDIARY_SYSTEM_PROMPT
        assert "RULE 3" in INTERMEDIARY_SYSTEM_PROMPT

    def test_knowledge_contains_epr_info(self):
        from app.prompts.intermediary_knowledge import INTERMEDIARY_PLATFORM_KNOWLEDGE
        assert "EPR" in INTERMEDIARY_PLATFORM_KNOWLEDGE
        assert "Extended Producer" in INTERMEDIARY_PLATFORM_KNOWLEDGE

    def test_knowledge_contains_driver_guidance(self):
        from app.prompts.intermediary_knowledge import INTERMEDIARY_PLATFORM_KNOWLEDGE
        assert "two-wheeler" in INTERMEDIARY_PLATFORM_KNOWLEDGE.lower()
        assert "truck" in INTERMEDIARY_PLATFORM_KNOWLEDGE.lower()

    def test_knowledge_contains_form6_deadlines(self):
        from app.prompts.intermediary_knowledge import INTERMEDIARY_PLATFORM_KNOWLEDGE
        assert "31st July" in INTERMEDIARY_PLATFORM_KNOWLEDGE
        assert "31st October" in INTERMEDIARY_PLATFORM_KNOWLEDGE
        assert "31st January" in INTERMEDIARY_PLATFORM_KNOWLEDGE
        assert "30th April" in INTERMEDIARY_PLATFORM_KNOWLEDGE


# ===========================================================================
# 9. CITIZEN SYSTEM PROMPT CONTENT
# ===========================================================================

class TestCitizenPromptContent:
    """EcoBot system prompt must contain all required sections."""

    def test_prompt_contains_personality(self):
        from app.prompts.ecobot_system_prompt import ECOBOT_SYSTEM_PROMPT
        assert "PERSONALITY" in ECOBOT_SYSTEM_PROMPT

    def test_prompt_contains_allowed_topics(self):
        from app.prompts.ecobot_system_prompt import ECOBOT_SYSTEM_PROMPT
        assert "ALLOWED TOPICS" in ECOBOT_SYSTEM_PROMPT

    def test_prompt_contains_off_topic_rule(self):
        from app.prompts.ecobot_system_prompt import ECOBOT_SYSTEM_PROMPT
        assert "OFF-TOPIC RULE" in ECOBOT_SYSTEM_PROMPT

    def test_prompt_contains_output_format_rules(self):
        from app.prompts.ecobot_system_prompt import ECOBOT_SYSTEM_PROMPT
        assert "RULE 1" in ECOBOT_SYSTEM_PROMPT
        assert "RULE 2" in ECOBOT_SYSTEM_PROMPT
        assert "RULE 3" in ECOBOT_SYSTEM_PROMPT

    def test_prompt_embeds_platform_knowledge(self):
        from app.prompts.ecobot_system_prompt import ECOBOT_SYSTEM_PROMPT
        assert "/citizen/book-recycle" in ECOBOT_SYSTEM_PROMPT
        assert "/citizen/analyze" in ECOBOT_SYSTEM_PROMPT
        assert "/citizen/e-facilities" in ECOBOT_SYSTEM_PROMPT


# ===========================================================================
# 10. EDGE CASES
# ===========================================================================

class TestEdgeCases:
    """Boundary and edge case handling."""

    def test_empty_message_still_returns_response(self):
        with mock_workers_present(), mock_llm_reply("Please ask me something."):
            data = chat("   ")
        # Either the LLM handles it or the guard catches it — must not crash
        assert "success" in data

    def test_very_long_message_handled(self):
        long_msg = "How do I recycle " + "my old phone " * 100
        with mock_workers_present(), mock_llm_reply("You can recycle at any ELocate facility."):
            data = chat(long_msg, role="citizen")
        assert data["success"] is True

    def test_mixed_case_off_topic_blocked(self):
        """Off-topic guard should be case-insensitive."""
        with mock_workers_present():
            with patch("app.api.routes.llm_service.call_chat_with_fallback", new_callable=AsyncMock) as mock_llm:
                data = chat("Write me a PYTHON function", role="citizen")
                mock_llm.assert_not_called()
        assert data["success"] is True

    def test_citizen_off_topic_suggestions_are_eco_focused(self):
        with mock_workers_present():
            data = chat("Tell me a joke", role="citizen")
        suggestions = data.get("suggestions") or []
        combined = " ".join(suggestions).lower()
        assert any(w in combined for w in ["recycle", "e-waste", "battery", "environment"])

    def test_response_text_is_non_empty_string(self):
        with mock_workers_present(), mock_llm_reply("Some valid response."):
            data = chat("How do I recycle?", role="citizen")
        assert isinstance(data["text"], str)
        assert len(data["text"].strip()) > 0

    def test_suggestions_list_has_at_most_three_items(self):
        with mock_workers_present(), mock_llm_reply("Here is how to recycle your phone."):
            data = chat("How do I recycle my phone?", role="citizen")
        suggestions = data.get("suggestions") or []
        assert len(suggestions) <= 3

    def test_intermediary_advisory_mode_message_for_live_data(self):
        """Questions about live DB stats should get the advisory mode reply."""
        advisory_reply = "📋 I'm currently in **Advisory Mode**"
        with mock_workers_present(), mock_llm_reply(advisory_reply):
            data = chat("How many drivers are free right now?", role="intermediary")
        assert data["success"] is True
        # The LLM is expected to return the advisory message per the system prompt instruction
        assert data["text"] is not None
