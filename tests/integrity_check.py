"""
INDB Startup Integrity Check
=============================
Verifies database health at startup time — no running server required.

Usable two ways:
  1. pytest:   pytest tests/integrity_check.py -v
  2. standalone: python tests/integrity_check.py
"""

import sys
import time
import logging
from pathlib import Path

# Ensure project root is on path when run standalone
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("indb.integrity")

# ─── Helpers ──────────────────────────────────────────────────────────────────

PASS, FAIL = "PASS", "FAIL"
_results: list[tuple[str, str, str]] = []  # (name, status, detail)


def _check(name: str):
    """Decorator that records pass/fail for each check function."""
    import functools

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                detail = fn(*args, **kwargs) or ""
                _results.append((name, PASS, detail))
                logger.info("  ✓  %s  %s", name, detail)
                return True
            except Exception as exc:
                _results.append((name, FAIL, str(exc)))
                logger.error("  ✗  %s: %s", name, exc)
                return False

        return wrapper

    return decorator


# ─── Integrity Checks ─────────────────────────────────────────────────────────


@_check("Storage loads without error")
def check_storage_loads():
    # Deferred import avoids circular initialisation when running standalone
    from storage.binary import load_decrypted  # noqa: PLC0415

    data = load_decrypted()
    if not isinstance(data, list):
        raise TypeError(f"Expected list from storage, got {type(data).__name__}")
    return f"({len(data)} raw items)"


@_check("INDB initialises and memory is populated")
def check_indb_init():
    from core.indb import INDB

    db = INDB()
    count = len(db.memory)
    if count < 0:
        raise ValueError("Negative event count — memory state is corrupt")
    return f"({count} events in memory)"


@_check("All events in memory have valid id and timestamp")
def check_events_schema():
    from core.indb import INDB

    db = INDB()
    events = db.memory.get_all()
    bad = []
    for evt in events:
        # Accept Event and FusedEvent (duck-typed: must have id + timestamp)
        if not hasattr(evt, "id") or not evt.id:
            bad.append(f"missing id: {repr(evt)[:60]}")
        elif not hasattr(evt, "timestamp"):
            bad.append(f"missing timestamp: {repr(evt)[:60]}")
    if bad:
        raise ValueError(f"{len(bad)} malformed event(s): {bad[:3]}")
    return f"({len(events)} events validated)"


@_check("Event timestamps are positive floats")
def check_event_timestamps():
    from core.indb import INDB

    db = INDB()
    events = db.memory.get_all()
    bad = [e.id for e in events if not isinstance(e.timestamp, (int, float)) or e.timestamp <= 0]
    if bad:
        raise ValueError(f"Events with invalid timestamp: {bad[:5]}")
    return f"({len(events)} timestamps ok)"


@_check("Temporal parser initialises")
def check_temporal_parser():
    from core.temporal_engine import TemporalParser

    parser = TemporalParser()
    result = parser.parse("last 24 hours")
    if not isinstance(result, dict) or result.get("type") not in ("range", "relative", "unknown"):
        raise ValueError(f"Unexpected parse result: {result}")
    return f"(type={result.get('type')})"


@_check("Fusion engine initialises")
def check_fusion_engine():
    from core.indb import INDB

    db = INDB()
    if db.fusion_engine is None:
        raise RuntimeError("Fusion engine is None — module import failed")
    enabled = db.fusion_engine.config.get("enabled", False)
    threshold = db.fusion_engine.config.get("threshold", 0)
    return f"(enabled={enabled}, threshold={threshold})"


@_check("Raft state is valid (standalone: disabled)")
def check_raft_state():
    from core.indb import INDB

    db = INDB()
    if db.raft is not None:
        from core.raft.state import RaftState

        if not isinstance(db.raft.state, RaftState):
            raise TypeError(f"Unexpected raft state type: {type(db.raft.state)}")
        return f"(raft={db.raft.state.value}, node={db.raft.node_id})"
    return "(standalone — raft disabled)"


# ─── Runner ───────────────────────────────────────────────────────────────────


def run_integrity_checks() -> bool:
    logger.info("=" * 60)
    logger.info("INDB Startup Integrity Check")
    logger.info("=" * 60)
    t0 = time.time()

    # INDB must initialise first so storage.binary is fully loaded
    # before the raw storage check attempts to import it directly.
    check_indb_init()
    check_storage_loads()
    check_events_schema()
    check_event_timestamps()
    check_temporal_parser()
    check_fusion_engine()
    check_raft_state()

    elapsed = (time.time() - t0) * 1000
    passed = sum(1 for _, s, _ in _results if s == PASS)
    total = len(_results)

    logger.info("=" * 60)
    logger.info("Result: %d/%d checks passed in %.0fms", passed, total, elapsed)
    if passed < total:
        for name, status, detail in _results:
            if status == FAIL:
                logger.error("  FAILED: %s — %s", name, detail)
    logger.info("=" * 60)

    return passed == total


# ─── pytest entrypoints ───────────────────────────────────────────────────────


def test_storage_loads():
    assert check_storage_loads()


def test_indb_init():
    assert check_indb_init()


def test_events_schema():
    assert check_events_schema()


def test_event_timestamps():
    assert check_event_timestamps()


def test_temporal_parser():
    assert check_temporal_parser()


def test_fusion_engine():
    assert check_fusion_engine()


def test_raft_state():
    assert check_raft_state()


# ─── Standalone entry ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    ok = run_integrity_checks()
    sys.exit(0 if ok else 1)
