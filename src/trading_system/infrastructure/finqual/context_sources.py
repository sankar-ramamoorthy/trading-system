"""Finqual-backed read-only fundamentals and ownership snapshot adapters."""

from collections.abc import Callable
from datetime import UTC, datetime
import json
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from trading_system.infrastructure.local_secret_vault import require_secret
from trading_system.ports.market_context import ImportedMarketContext


FINQUAL_BASE_URL = "https://finqual.leapcell.app"
FINQUAL_STATEMENTS = {"income-statement", "balance-sheet", "cash-flow"}


class FinqualFinancialStatementImportSource:
    """Loads one normalized financial statement context snapshot from Finqual."""

    def __init__(
        self,
        symbol: str,
        statement: str,
        start: int,
        end: int,
        *,
        quarter: bool = False,
        api_key: str | None = None,
        http_get: Callable[[str], Any] | None = None,
        base_url: str = FINQUAL_BASE_URL,
    ) -> None:
        symbol = symbol.strip().upper()
        statement = statement.strip().lower()
        if not symbol:
            raise ValueError("Finqual statement symbol is required.")
        if statement not in FINQUAL_STATEMENTS:
            raise ValueError("Finqual financial statement type is not supported.")
        if end < start:
            raise ValueError("End year must be greater than or equal to start year.")

        self._symbol = symbol
        self._statement = statement
        self._start = start
        self._end = end
        self._quarter = quarter
        self._api_key = api_key
        self._http_get = http_get or _get_json
        self._base_url = base_url.rstrip("/")
        self.source_ref = (
            f"symbol={self._symbol};statement={self._statement};"
            f"start={self._start};end={self._end};"
            f"quarter={str(self._quarter).lower()};provider=finqual"
        )

    def load(self) -> ImportedMarketContext:
        """Fetch one Finqual financial statement and convert it into a snapshot."""
        api_key = self._api_key or require_secret("FINQUAL_API_KEY")
        query = {
            "ticker": self._symbol,
            "start": str(self._start),
            "end": str(self._end),
            "quarter": str(self._quarter).lower(),
            "api_key": api_key,
        }

        try:
            data = self._http_get(_url(self._base_url, self._statement, query))
        except ValueError:
            raise
        except Exception as exc:  # pragma: no cover - exercised by adapter tests
            raise ValueError(
                f"Finqual financial statement fetch failed for {self._symbol}."
            ) from exc

        return ImportedMarketContext(
            context_type="financial_statement",
            observed_at=datetime.now(UTC),
            payload={
                "symbol": self._symbol,
                "provider": "finqual",
                "statement": self._statement,
                "start": self._start,
                "end": self._end,
                "quarter": self._quarter,
                "data": data,
            },
        )


class FinqualInsiderTransactionsImportSource:
    """Loads recent insider transactions for one ticker from Finqual."""

    def __init__(
        self,
        symbol: str,
        period: str,
        *,
        api_key: str | None = None,
        http_get: Callable[[str], Any] | None = None,
        base_url: str = FINQUAL_BASE_URL,
    ) -> None:
        symbol = symbol.strip().upper()
        period = period.strip()
        if not symbol:
            raise ValueError("Finqual insider transaction symbol is required.")
        if not period:
            raise ValueError("Finqual insider transaction period is required.")

        self._symbol = symbol
        self._period = period
        self._api_key = api_key
        self._http_get = http_get or _get_json
        self._base_url = base_url.rstrip("/")
        self.source_ref = (
            f"symbol={self._symbol};period={self._period};"
            "provider=finqual;dataset=insider-transactions"
        )

    def load(self) -> ImportedMarketContext:
        """Fetch insider transactions and convert them into a snapshot."""
        api_key = self._api_key or require_secret("FINQUAL_API_KEY")
        query = {
            "ticker": self._symbol,
            "period": self._period,
            "api_key": api_key,
        }

        try:
            data = self._http_get(_url(self._base_url, "insider-transactions", query))
        except ValueError:
            raise
        except Exception as exc:  # pragma: no cover - exercised by adapter tests
            raise ValueError(
                f"Finqual insider transactions fetch failed for {self._symbol}."
            ) from exc

        return ImportedMarketContext(
            context_type="insider_transactions",
            observed_at=datetime.now(UTC),
            payload={
                "symbol": self._symbol,
                "provider": "finqual",
                "period": self._period,
                "data": data,
            },
        )


class Finqual13FImportSource:
    """Loads recent 13F holdings for one CIK from Finqual."""

    def __init__(
        self,
        cik: str,
        period: int,
        *,
        api_key: str | None = None,
        http_get: Callable[[str], Any] | None = None,
        base_url: str = FINQUAL_BASE_URL,
    ) -> None:
        cik = cik.strip()
        if not cik:
            raise ValueError("Finqual 13F CIK is required.")
        if period <= 0:
            raise ValueError("Finqual 13F period must be positive.")

        self._cik = cik
        self._period = period
        self._api_key = api_key
        self._http_get = http_get or _get_json
        self._base_url = base_url.rstrip("/")
        self.source_ref = (
            f"cik={self._cik};period={self._period};"
            "provider=finqual;dataset=13f"
        )

    def load(self) -> ImportedMarketContext:
        """Fetch 13F holdings and convert them into a snapshot."""
        api_key = self._api_key or require_secret("FINQUAL_API_KEY")
        query = {
            "cik": self._cik,
            "period": str(self._period),
            "api_key": api_key,
        }

        try:
            data = self._http_get(_url(self._base_url, "13f", query))
        except ValueError:
            raise
        except Exception as exc:  # pragma: no cover - exercised by adapter tests
            raise ValueError(f"Finqual 13F fetch failed for CIK {self._cik}.") from exc

        return ImportedMarketContext(
            context_type="institutional_holdings_13f",
            observed_at=datetime.now(UTC),
            payload={
                "cik": self._cik,
                "provider": "finqual",
                "period": self._period,
                "data": data,
            },
        )


def _url(base_url: str, path: str, query: dict[str, str]) -> str:
    return f"{base_url}/{path}?{urlencode(query)}"


def _get_json(url: str) -> Any:
    try:
        with urlopen(url, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError("Finqual response is not valid JSON.") from exc
