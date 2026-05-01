from fastapi.testclient import TestClient

from trading_system.app.api import create_app


def test_health_endpoint_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_reference_instrument_endpoints_use_symbols() -> None:
    client = TestClient(create_app())

    list_response = client.get("/reference/instruments")
    detail_response = client.get("/reference/instruments/nvda")

    assert list_response.status_code == 200
    assert {
        "id": "33333333-3333-4333-8333-333333333333",
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
    } in list_response.json()
    assert detail_response.status_code == 200
    assert detail_response.json() == {
        "id": "33333333-3333-4333-8333-333333333333",
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
    }


def test_reference_playbook_endpoints_use_slugs() -> None:
    client = TestClient(create_app())

    list_response = client.get("/reference/playbooks")
    detail_response = client.get("/reference/playbooks/pullback-to-trend")

    assert list_response.status_code == 200
    assert {
        "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "slug": "pullback-to-trend",
        "name": "Pullback To Trend",
        "description": "Trend-continuation setup after a controlled pullback.",
    } in list_response.json()
    assert detail_response.status_code == 200
    assert detail_response.json() == {
        "id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        "slug": "pullback-to-trend",
        "name": "Pullback To Trend",
        "description": "Trend-continuation setup after a controlled pullback.",
    }


def test_reference_detail_endpoints_reject_unknown_values() -> None:
    client = TestClient(create_app())

    missing_instrument = client.get("/reference/instruments/XYZ")
    missing_playbook = client.get("/reference/playbooks/unknown")

    assert missing_instrument.status_code == 404
    assert missing_instrument.json()["detail"] == "Unknown instrument symbol: XYZ"
    assert missing_playbook.status_code == 404
    assert missing_playbook.json()["detail"] == "Unknown playbook slug: unknown"
