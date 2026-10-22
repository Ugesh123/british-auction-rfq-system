
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main as main_module
from app.database import Base, get_db


class FrozenDateTime(datetime):
    fixed_now = datetime.now(timezone.utc)

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls.fixed_now.replace(tzinfo=None)
        return cls.fixed_now.astimezone(tz)


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main_module.app.dependency_overrides[get_db] = override_get_db

    with TestClient(main_module.app) as test_client:
        yield test_client

    main_module.app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def create_test_rfq(client, trigger_type="BID_RECEIVED", forced_minutes=20):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    start = now + timedelta(days=1)
    close = start + timedelta(minutes=10)
    forced_close = start + timedelta(minutes=forced_minutes)

    payload = {
        "name": f"Automated RFQ {now.timestamp()}",
        "bid_start": start.isoformat(),
        "bid_close": close.isoformat(),
        "forced_close": forced_close.isoformat(),
        "pickup_date": (now + timedelta(days=3)).date().isoformat(),
        "config": {
            "trigger_window_x": 10,
            "extension_y": 5,
            "trigger_type": trigger_type,
        },
    }

    response = client.post("/rfqs", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"], start, forced_close


def freeze_time(monkeypatch, value):
    FrozenDateTime.fixed_now = value
    monkeypatch.setattr(main_module, "datetime", FrozenDateTime)


def bid_payload(supplier_id, carrier_name, freight):
    return {
        "supplier_id": supplier_id,
        "carrier_name": carrier_name,
        "freight": freight,
        "origin_charges": 0,
        "destination_charges": 0,
        "transit_time": "2 days",
        "quote_validity": (
            datetime.now(timezone.utc) + timedelta(days=10)
        ).date().isoformat(),
    }


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_and_get_rfq(client):
    rfq_id, _, _ = create_test_rfq(client)
    response = client.get(f"/rfqs/{rfq_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == rfq_id
    assert data["config"]["trigger_window_x"] == 10
    assert data["config"]["extension_y"] == 5
    assert data["bids"] == []
    assert data["ranking"] == []
    assert data["activity_log"] == []


def test_invalid_trigger_type_is_rejected(client):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    payload = {
        "name": "Invalid Trigger Test",
        "bid_start": (now + timedelta(days=1)).isoformat(),
        "bid_close": (now + timedelta(days=1, minutes=10)).isoformat(),
        "forced_close": (now + timedelta(days=1, minutes=20)).isoformat(),
        "pickup_date": (now + timedelta(days=2)).date().isoformat(),
        "config": {
            "trigger_window_x": 10,
            "extension_y": 5,
            "trigger_type": "INVALID_TRIGGER",
        },
    }

    response = client.post("/rfqs", json=payload)
    assert response.status_code == 422


def test_bid_received_inside_window_extends_auction(client, monkeypatch):
    rfq_id, start, _ = create_test_rfq(client, "BID_RECEIVED")
    freeze_time(monkeypatch, start + timedelta(minutes=9))

    response = client.post(
        f"/rfqs/{rfq_id}/bids",
        json=bid_payload("SUP-1", "Carrier One", 1000),
    )

    assert response.status_code == 201, response.text
    result = response.json()
    assert result["trigger_window_active"] is True
    assert result["extension_triggered"] is True

    actual_close = datetime.fromisoformat(result["bid_close"])
    assert actual_close == (start + timedelta(minutes=15)).replace(tzinfo=None)


def test_any_rank_change_trigger_extends_auction(client, monkeypatch):
    rfq_id, start, _ = create_test_rfq(client, "ANY_RANK_CHANGE")
    freeze_time(monkeypatch, start + timedelta(minutes=9))

    response = client.post(
        f"/rfqs/{rfq_id}/bids",
        json=bid_payload("SUP-1", "Carrier One", 1000),
    )

    assert response.status_code == 201, response.text
    assert response.json()["extension_triggered"] is True


def test_l1_change_trigger_extends_auction(client, monkeypatch):
    rfq_id, start, _ = create_test_rfq(client, "L1_CHANGE")
    freeze_time(monkeypatch, start + timedelta(minutes=9))

    first = client.post(
        f"/rfqs/{rfq_id}/bids",
        json=bid_payload("SUP-1", "Carrier One", 1000),
    )
    assert first.status_code == 201, first.text

    second = client.post(
        f"/rfqs/{rfq_id}/bids",
        json=bid_payload("SUP-2", "Carrier Two", 900),
    )

    assert second.status_code == 201, second.text
    assert second.json()["extension_triggered"] is True
    assert second.json()["rank"] == 1


def test_extension_never_exceeds_forced_close(client, monkeypatch):
    rfq_id, start, forced_close = create_test_rfq(
        client, "BID_RECEIVED", forced_minutes=12
    )
    freeze_time(monkeypatch, start + timedelta(minutes=9))

    response = client.post(
        f"/rfqs/{rfq_id}/bids",
        json=bid_payload("SUP-1", "Carrier One", 1000),
    )

    assert response.status_code == 201, response.text
    result = response.json()
    assert result["extension_triggered"] is True

    actual_close = datetime.fromisoformat(result["bid_close"])
    returned_forced_close = datetime.fromisoformat(result["forced_close"])

    assert actual_close == forced_close.replace(tzinfo=None)
    assert actual_close == returned_forced_close


def test_bid_is_rejected_after_auction_closes(client, monkeypatch):
    rfq_id, start, _ = create_test_rfq(client, "BID_RECEIVED")
    freeze_time(monkeypatch, start + timedelta(minutes=10))

    response = client.post(
        f"/rfqs/{rfq_id}/bids",
        json=bid_payload("SUP-1", "Carrier One", 1000),
    )

    assert response.status_code == 400
    assert "closed" in response.json()["detail"].lower()


def test_same_supplier_must_lower_previous_bid(client, monkeypatch):
    rfq_id, start, _ = create_test_rfq(client, "BID_RECEIVED")
    freeze_time(monkeypatch, start + timedelta(minutes=2))

    first = client.post(
        f"/rfqs/{rfq_id}/bids",
        json=bid_payload("SUP-1", "Carrier One", 1000),
    )
    assert first.status_code == 201, first.text

    second = client.post(
        f"/rfqs/{rfq_id}/bids",
        json=bid_payload("SUP-1", "Carrier One", 1000),
    )

    assert second.status_code == 400
    assert "lower" in second.json()["detail"].lower()
