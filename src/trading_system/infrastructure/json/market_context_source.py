"""Local JSON file import adapter for read-only market context snapshots."""

from datetime import datetime
import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from trading_system.ports.market_context import ImportedMarketContext


class JsonMarketContextImportSource:
    """Loads one explicit market context snapshot from a local JSON file."""

    def __init__(self, path: Path | str) -> None:
        self._path = Path(path)

    def load(self) -> ImportedMarketContext:
        """Read and validate one context document from disk."""
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise ValueError(f"Context import file does not exist: {self._path}") from exc
        except JSONDecodeError as exc:
            raise ValueError(f"Context import file is invalid JSON: {self._path}") from exc

        if not isinstance(raw, dict):
            raise ValueError("Context import root must be an object.")

        context_type = raw.get("context_type")
        if not isinstance(context_type, str) or not context_type.strip():
            raise ValueError("Context import requires a non-empty context_type.")

        observed_at = raw.get("observed_at")
        if not isinstance(observed_at, str):
            raise ValueError("Context import requires observed_at as an ISO datetime.")

        payload = raw.get("payload")
        if not isinstance(payload, dict):
            raise ValueError("Context import requires payload as an object.")

        return ImportedMarketContext(
            context_type=context_type,
            observed_at=_datetime(observed_at),
            payload=dict(payload),
        )


def _datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Context import observed_at must be an ISO datetime.") from exc
