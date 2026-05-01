from uuid import UUID

import pytest

from trading_system.infrastructure.seeded_reference_data import (
    SeededReferenceDataRepository,
)
from trading_system.services.reference_lookup_service import ReferenceLookupService


def test_seeded_reference_lookup_resolves_symbol_case_insensitively() -> None:
    service = ReferenceLookupService(SeededReferenceDataRepository())

    instrument = service.resolve_instrument(" nvda ")

    assert instrument.id == UUID("33333333-3333-4333-8333-333333333333")
    assert instrument.symbol == "NVDA"


def test_seeded_reference_lookup_resolves_playbook_slug_case_insensitively() -> None:
    service = ReferenceLookupService(SeededReferenceDataRepository())

    playbook = service.resolve_playbook(" Pullback-To-Trend ")

    assert playbook.id == UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")
    assert playbook.slug == "pullback-to-trend"


def test_seeded_reference_lookup_rejects_unknown_symbol() -> None:
    service = ReferenceLookupService(SeededReferenceDataRepository())

    with pytest.raises(ValueError, match="Unknown instrument symbol: XYZ"):
        service.resolve_instrument("XYZ")


def test_seeded_reference_lookup_rejects_unknown_playbook_slug() -> None:
    service = ReferenceLookupService(SeededReferenceDataRepository())

    with pytest.raises(ValueError, match="Unknown playbook slug: unknown"):
        service.resolve_playbook("unknown")
