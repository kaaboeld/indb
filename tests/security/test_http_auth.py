"""
HTTP auth surface: who may read, who may write, who may export.

The suite as a whole runs with AUTH_MODE=OPEN (see tests/conftest.py), so these
tests put the shared manager into MIXED with known keys for their duration.
"""
import jwt
import pytest
from fastapi.testclient import TestClient

from auth.flexible_auth import auth_manager
from main import app

JWT_SECRET = "test-secret-for-suite"

WRITER = {"X-API-Key": "wkey"}
READER = {"X-API-Key": "rkey"}
ADMIN = {"X-API-Key": "akey"}
BAD = {"X-API-Key": "not-a-key"}


@pytest.fixture
def client():
    previous_mode = auth_manager.mode
    previous_keys = auth_manager.api_keys
    previous_secret = auth_manager.jwt_secret

    auth_manager.mode = "MIXED"
    auth_manager.api_keys = {
        "wkey": ("ingest-bot", "writer"),
        "rkey": ("dashboard", "reader"),
        "akey": ("ops", "admin"),
    }
    auth_manager.jwt_secret = JWT_SECRET
    try:
        yield TestClient(app)
    finally:
        auth_manager.mode = previous_mode
        auth_manager.api_keys = previous_keys
        auth_manager.jwt_secret = previous_secret


def an_event():
    return {"raw_data_anchor": ["alpha", "beta"], "location": "test/authcheck"}


def bearer(claims, secret=JWT_SECRET):
    return {"Authorization": f"Bearer {jwt.encode(claims, secret, algorithm='HS256')}"}


class TestReadsArePublic:
    def test_list_events_without_credentials(self, client):
        assert client.get("/api/v2/events").status_code == 200

    def test_search_without_credentials(self, client):
        assert client.get("/api/v2/search", params={"q": "a"}).status_code == 200

    def test_health_without_credentials(self, client):
        assert client.get("/health").status_code == 200


class TestWritesRequireCredentials:
    def test_anonymous_is_rejected(self, client):
        assert client.post("/api/v2/events", json=an_event()).status_code == 401

    def test_unknown_key_is_rejected(self, client):
        assert client.post("/api/v2/events", json=an_event(), headers=BAD).status_code == 401

    def test_writer_is_accepted(self, client):
        assert client.post("/api/v2/events", json=an_event(), headers=WRITER).status_code == 200

    def test_reader_is_forbidden(self, client):
        assert client.post("/api/v2/events", json=an_event(), headers=READER).status_code == 403


class TestBatchWrites:
    def test_anonymous_is_rejected(self, client):
        assert client.post("/api/v2/events/batch", json={"events": [an_event()]}).status_code == 401

    def test_reader_is_forbidden(self, client):
        res = client.post("/api/v2/events/batch", json={"events": [an_event()]}, headers=READER)
        assert res.status_code == 403

    def test_writer_is_accepted(self, client):
        res = client.post("/api/v2/events/batch", json={"events": [an_event()]}, headers=WRITER)
        assert res.status_code == 200


class TestBulkExport:
    def test_json_export_is_not_world_readable(self, client):
        assert client.get("/api/v2/export/json").status_code == 401

    def test_csv_export_is_not_world_readable(self, client):
        assert client.get("/api/v2/export/csv").status_code == 401

    def test_reader_may_export(self, client):
        assert client.get("/api/v2/export/csv", headers=READER).status_code == 200


class TestWebhooksAreAdminOnly:
    hook = {"url": "https://example.invalid/hook"}

    def test_anonymous_is_rejected(self, client):
        assert client.post("/api/v2/webhooks", json=self.hook).status_code == 401

    def test_writer_is_forbidden(self, client):
        assert client.post("/api/v2/webhooks", json=self.hook, headers=WRITER).status_code == 403

    def test_admin_is_accepted(self, client):
        assert client.post("/api/v2/webhooks", json=self.hook, headers=ADMIN).status_code == 200


class TestJwtClaims:
    def test_writer_claim_may_write(self, client):
        res = client.post("/api/v2/events", json=an_event(), headers=bearer({"sub": "alice", "role": "writer"}))
        assert res.status_code == 200

    def test_reader_claim_may_not_write(self, client):
        res = client.post("/api/v2/events", json=an_event(), headers=bearer({"sub": "bob", "role": "reader"}))
        assert res.status_code == 403

    def test_token_signed_with_wrong_secret_is_rejected(self, client):
        forged = bearer({"sub": "mallory", "role": "admin"}, secret="wrong-secret")
        assert client.post("/api/v2/events", json=an_event(), headers=forged).status_code == 401

    def test_identity_comes_from_the_claim_not_the_route(self, client):
        """A route must not be able to hand itself a privileged identity."""
        res = client.post("/api/v2/events", json=an_event(), headers=bearer({"sub": "carol"}))
        assert res.status_code == 403, "a claim with no role must default to reader"
