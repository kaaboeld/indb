
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from core.raft.api import router as raft_router
import core.raft.api as raft_api
from core.config import config


@pytest.fixture
def raft_client(monkeypatch):
    monkeypatch.setattr(config, "RAFT_RPC_TOKEN", "test-raft-secret")
    node = MagicMock()
    node.on_request_vote.return_value = False
    node.on_append_entries.return_value = False
    node.current_term = 1
    raft_api.raft_node = node

    app = FastAPI()
    app.include_router(raft_router)
    with TestClient(app) as client:
        yield client, node

    raft_api.raft_node = None
    monkeypatch.setattr(config, "RAFT_RPC_TOKEN", None)


def test_raft_vote_requires_token(raft_client):
    client, _ = raft_client
    payload = {
        "term": 2,
        "candidate_id": "indb-node-2",
        "last_log_index": -1,
        "last_log_term": 0,
    }

    denied = client.post("/raft/vote", json=payload)
    assert denied.status_code == 403

    allowed = client.post(
        "/raft/vote",
        json=payload,
        headers={"X-Raft-Token": "test-raft-secret"},
    )
    assert allowed.status_code == 200


def test_raft_append_requires_token(raft_client):
    client, _ = raft_client
    payload = {
        "term": 2,
        "leader_id": "indb-node-1",
        "entries": [],
        "prev_log_index": -1,
        "prev_log_term": 0,
        "leader_commit": 0,
    }

    denied = client.post("/raft/append", json=payload)
    assert denied.status_code == 403

    allowed = client.post(
        "/raft/append",
        json=payload,
        headers={"X-Raft-Token": "test-raft-secret"},
    )
    assert allowed.status_code == 200
