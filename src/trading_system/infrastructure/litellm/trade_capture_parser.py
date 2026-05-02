"""LiteLLM adapter for natural-language trade capture parsing."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from importlib import import_module
from typing import Any

from trading_system.services.trade_capture_draft import (
    DraftFieldIssue,
    TradeCaptureDraft,
    TradeIdeaDraft,
    TradePlanDraft,
    TradeThesisDraft,
)
from trading_system.services.trade_capture_parser import TradeCaptureParseError


SYSTEM_PROMPT = """You extract user-authored trade capture text into JSON.
Return only JSON with keys: idea, thesis, plan, ambiguous_fields.
Do not suggest trades, invent missing values, verify claims, approve plans, create order intents, open positions, or record fills.
If a field is not present in the user's text, return null for scalar fields or [] for list fields.
Use ambiguous_fields only when the user's text supports multiple interpretations."""

USER_PROMPT_SCHEMA = """Extract this trade capture note into the required JSON shape.

Schema:
{
  "idea": {
    "instrument_symbol": string|null,
    "playbook_slug": string|null,
    "purpose": string|null,
    "direction": string|null,
    "horizon": string|null
  },
  "thesis": {
    "reasoning": string|null,
    "supporting_evidence": [string],
    "risks": [string],
    "disconfirming_signals": [string]
  },
  "plan": {
    "entry_criteria": string|null,
    "invalidation": string|null,
    "targets": [string],
    "risk_model": string|null,
    "sizing_assumptions": string|null
  },
  "ambiguous_fields": [
    {
      "entity": "TradeIdea"|"TradeThesis"|"TradePlan",
      "field": string,
      "message": string,
      "candidates": [string]
    }
  ]
}

Trade capture note:
"""


@dataclass(frozen=True)
class LiteLLMTradeCaptureParserConfig:
    """Runtime configuration for the LiteLLM trade-capture parser."""

    model: str
    api_base: str

    @classmethod
    def from_env(cls) -> "LiteLLMTradeCaptureParserConfig":
        """Load parser configuration from environment variables."""
        model = os.getenv("TRADING_SYSTEM_LLM_MODEL", "").strip()
        api_base = os.getenv("TRADING_SYSTEM_LLM_API_BASE", "").strip()
        if not model:
            raise TradeCaptureParseError("TRADING_SYSTEM_LLM_MODEL is required.")
        if not api_base:
            raise TradeCaptureParseError("TRADING_SYSTEM_LLM_API_BASE is required.")
        return cls(model=model, api_base=api_base)


class LiteLLMTradeCaptureParser:
    """Parse trade-capture text through LiteLLM into editable draft contracts."""

    def __init__(self, config: LiteLLMTradeCaptureParserConfig) -> None:
        if not config.model.strip():
            raise TradeCaptureParseError("TRADING_SYSTEM_LLM_MODEL is required.")
        if not config.api_base.strip():
            raise TradeCaptureParseError("TRADING_SYSTEM_LLM_API_BASE is required.")
        self._config = config

    def parse(self, source_text: str) -> TradeCaptureDraft:
        """Return an unsaved draft parsed from user-authored source text."""
        if not source_text.strip():
            raise TradeCaptureParseError("Trade capture text is required.")

        try:
            completion = import_module("litellm").completion
            response = completion(
                model=self._config.model,
                api_base=self._config.api_base,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"{USER_PROMPT_SCHEMA}{source_text}",
                    },
                ],
                temperature=0,
                response_format={"type": "json_object"},
            )
        except TradeCaptureParseError:
            raise
        except Exception as exc:
            raise TradeCaptureParseError("Trade capture parser provider call failed.") from exc

        return _draft_from_response(response, source_text)


def _draft_from_response(response: Any, source_text: str) -> TradeCaptureDraft:
    content = _response_content(response)
    payload = _json_object(content)
    return _draft_from_payload(payload, source_text)


def _response_content(response: Any) -> str:
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, KeyError, TypeError) as exc:
        raise TradeCaptureParseError("Trade capture parser response was malformed.") from exc
    if not isinstance(content, str) or not content.strip():
        raise TradeCaptureParseError("Trade capture parser returned empty content.")
    return content


def _json_object(content: str) -> dict[str, Any]:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise TradeCaptureParseError("Trade capture parser returned invalid JSON.") from exc
    if not isinstance(payload, dict):
        raise TradeCaptureParseError("Trade capture parser JSON must be an object.")
    return payload


def _draft_from_payload(payload: dict[str, Any], source_text: str) -> TradeCaptureDraft:
    idea = _object_field(payload, "idea")
    thesis = _object_field(payload, "thesis")
    plan = _object_field(payload, "plan")
    ambiguous_fields = _list_field(payload, "ambiguous_fields")

    draft = TradeCaptureDraft(
        idea=TradeIdeaDraft(
            instrument_symbol=_optional_string(idea, "instrument_symbol"),
            playbook_slug=_optional_string(idea, "playbook_slug"),
            purpose=_optional_string(idea, "purpose"),
            direction=_optional_string(idea, "direction"),
            horizon=_optional_string(idea, "horizon"),
        ),
        thesis=TradeThesisDraft(
            reasoning=_optional_string(thesis, "reasoning"),
            supporting_evidence=_string_list(thesis, "supporting_evidence"),
            risks=_string_list(thesis, "risks"),
            disconfirming_signals=_string_list(thesis, "disconfirming_signals"),
        ),
        plan=TradePlanDraft(
            entry_criteria=_optional_string(plan, "entry_criteria"),
            invalidation=_optional_string(plan, "invalidation"),
            targets=_string_list(plan, "targets"),
            risk_model=_optional_string(plan, "risk_model"),
            sizing_assumptions=_optional_string(plan, "sizing_assumptions"),
        ),
        source_text=source_text,
        ambiguous_field_issues=[
            _ambiguous_issue(item) for item in ambiguous_fields
        ],
    )
    draft.validation_issues()
    return draft


def _object_field(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field, {})
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TradeCaptureParseError(f"Trade capture parser field '{field}' must be an object.")
    return value


def _list_field(payload: dict[str, Any], field: str) -> list[Any]:
    value = payload.get(field, [])
    if value is None:
        return []
    if not isinstance(value, list):
        raise TradeCaptureParseError(f"Trade capture parser field '{field}' must be a list.")
    return value


def _optional_string(payload: dict[str, Any], field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TradeCaptureParseError(f"Trade capture parser field '{field}' must be a string or null.")
    return value


def _string_list(payload: dict[str, Any], field: str) -> list[str]:
    values = _list_field(payload, field)
    if not all(isinstance(value, str) for value in values):
        raise TradeCaptureParseError(f"Trade capture parser field '{field}' must contain only strings.")
    return values


def _ambiguous_issue(payload: Any) -> DraftFieldIssue:
    if not isinstance(payload, dict):
        raise TradeCaptureParseError("Trade capture parser ambiguity entries must be objects.")
    entity = payload.get("entity")
    field = payload.get("field")
    message = payload.get("message")
    candidates = payload.get("candidates", [])
    if entity not in {"TradeIdea", "TradeThesis", "TradePlan"}:
        raise TradeCaptureParseError("Trade capture parser ambiguity entity is invalid.")
    if not isinstance(field, str) or not field.strip():
        raise TradeCaptureParseError("Trade capture parser ambiguity field is required.")
    if not isinstance(message, str) or not message.strip():
        raise TradeCaptureParseError("Trade capture parser ambiguity message is required.")
    if candidates is None:
        candidates = []
    if not isinstance(candidates, list) or not all(
        isinstance(candidate, str) for candidate in candidates
    ):
        raise TradeCaptureParseError("Trade capture parser ambiguity candidates must be strings.")
    return DraftFieldIssue(
        entity=entity,
        field=field,
        issue_type="ambiguous",
        message=message,
        candidates=tuple(candidates),
    )
