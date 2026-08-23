"""Unit tests for Ed25519 event signing and key_id recovery."""

import base64
import uuid

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from core.event import Event
from core.indb import INDB
from core.signing import (
    compute_key_id,
    event_signing_payload,
    sign_event,
    verify_event_signature,
)
from services.fusion import FusedEvent


@pytest.fixture
def writer_key():
    return Ed25519PrivateKey.generate()


@pytest.fixture
def indb_instance():
    return INDB(raft_node=None)


def test_compute_key_id_stable(writer_key):
    pub_b64 = base64.b64encode(writer_key.public_key().public_bytes_raw()).decode()
    assert compute_key_id(pub_b64) == compute_key_id(pub_b64)
    assert len(compute_key_id(pub_b64)) == 64


def test_sign_and_verify_event(writer_key):
    event = {
        "id": str(uuid.uuid4()),
        "timestamp": 1770018534.0,
        "raw_data_anchor": ["rain", "memory"],
        "location": "test/recovery",
    }
    event["signature"] = sign_event(event, writer_key)

    valid, key_id, err = verify_event_signature(event)
    assert valid is True
    assert err is None
    assert key_id == event["signature"]["key_id"]


def test_tampered_event_fails_verification(writer_key):
    event = {
        "id": str(uuid.uuid4()),
        "timestamp": 1770018534.0,
        "raw_data_anchor": ["truth"],
        "location": "test/recovery",
    }
    event["signature"] = sign_event(event, writer_key)
    event["raw_data_anchor"] = ["lie"]

    valid, _, err = verify_event_signature(event)
    assert valid is False
    assert err is not None


def test_events_by_key_id_and_restore(indb_instance, writer_key):
    pub_b64 = base64.b64encode(writer_key.public_key().public_bytes_raw()).decode()
    key_id = compute_key_id(pub_b64)

    event_id = str(uuid.uuid4())
    payload = {
        "id": event_id,
        "timestamp": 1770018600.0,
        "raw_data_anchor": ["restore", "test"],
        "location": "recovery/lab",
    }
    payload["signature"] = sign_event(payload, writer_key)

    stored = Event.from_dict(payload)
    indb_instance._store_event(stored)

    found = indb_instance.events_by_key_id(key_id)
    assert len(found) == 1
    assert found[0].id == event_id

    result = indb_instance.restore_signed_events(
        events=[payload],
        key_id=key_id,
        verify_only=True,
    )
    assert result["verified_count"] == 1
    assert result["failed_count"] == 0

    dup = indb_instance.restore_signed_events(
        events=[payload],
        key_id=key_id,
        verify_only=False,
    )
    assert dup["skipped_count"] == 1
    assert dup["imported_count"] == 0


def test_restore_rejects_wrong_key_id(indb_instance, writer_key):
    event_id = str(uuid.uuid4())
    payload = {
        "id": event_id,
        "timestamp": 1770018600.0,
        "raw_data_anchor": ["x"],
        "location": "recovery/lab",
    }
    payload["signature"] = sign_event(payload, writer_key)

    result = indb_instance.restore_signed_events(
        events=[payload],
        key_id="0" * 64,
        verify_only=True,
    )
    assert result["verified_count"] == 0
    assert result["failed_count"] == 1


def _signed_observation(writer_key, tokens, location, timestamp):
    payload = {
        "id": str(uuid.uuid4()),
        "timestamp": timestamp,
        "raw_data_anchor": tokens,
        "location": location,
    }
    payload["signature"] = sign_event(payload, writer_key)
    return payload


def test_identical_signed_events_are_not_fused(indb_instance, writer_key):
    """
    Two attestations of the same observation stay two records.

    Fusing them would yield a record no key signed: verification breaks and recovery by
    key_id loses the pair, which is exactly what Grain's redundant tier relies on.
    """
    pub_b64 = base64.b64encode(writer_key.public_key().public_bytes_raw()).decode()
    key_id = compute_key_id(pub_b64)

    first = _signed_observation(writer_key, ["quay", "fog"], "harbour/berth-9", 1770018600.0)
    second = _signed_observation(writer_key, ["quay", "fog"], "harbour/berth-9", 1770018601.0)

    indb_instance._store_event(Event.from_dict(first))
    indb_instance._store_event(Event.from_dict(second))

    found = indb_instance.events_by_key_id(key_id)
    assert {e.id for e in found} == {first["id"], second["id"]}

    for event in found:
        valid, recovered_key_id, err = verify_event_signature(event.to_dict())
        assert valid is True, err
        assert recovered_key_id == key_id


def test_identical_unsigned_events_still_fuse(indb_instance):
    """Control for the guard above: fusion itself must keep working for plain events."""
    common = dict(raw_data_anchor=["quay", "fog"], location="harbour/berth-9")
    indb_instance._store_event(Event(timestamp=1770018600.0, **common))
    stored = indb_instance._store_event(Event(timestamp=1770018601.0, **common))

    assert isinstance(stored, FusedEvent)
    assert stored.fusion_count >= 1
