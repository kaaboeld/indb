"""
Cold tier — events that exhaled out of hot memory.

The encrypted file is the sleeper. RAM keeps only the id and the tokens
needed to notice a strong seed. The body is read back when something
actually wakes it, or when an id is asked for by name.
"""
from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Set

from core.event import Event
from core.resonance_index import _token_keys
from storage.binary import load_decrypted, save_encrypted
from storage.format import COLD_FILE

logger = logging.getLogger("indb.cold")


class ColdStore:
    def __init__(self) -> None:
        self._traces: Dict[str, Set[str]] = {}
        self._by_token: Dict[str, Set[str]] = defaultdict(set)
        self.wake_count = 0

    @property
    def count(self) -> int:
        return len(self._traces)

    def ids(self) -> Set[str]:
        return set(self._traces)

    def contains(self, event_id: str) -> bool:
        return event_id in self._traces

    def trace_tokens(self, event_id: str) -> Optional[Set[str]]:
        """Tokens kept awake so a seed can be scored without loading the body."""
        return self._traces.get(event_id)

    def get(self, event_id: str) -> Optional[Event]:
        if event_id not in self._traces:
            return None
        for event in self._read_bodies():
            if isinstance(event, Event) and event.id == event_id:
                return event
        return None

    def load(self) -> None:
        if not os.path.exists(COLD_FILE):
            return
        for event in self._read_bodies():
            if isinstance(event, Event):
                self._remember_trace(event)
        logger.info("Cold index loaded: %d sleepers, bodies left on disk", self.count)

    def add(self, events: Iterable[Event]) -> None:
        incoming = [event for event in events if not getattr(event, "signature", None)]
        if not incoming:
            return
        bodies = {event.id: event for event in self._read_bodies() if isinstance(event, Event)}
        for event in incoming:
            bodies[event.id] = event
            self._remember_trace(event)
        self._write(bodies.values())

    def drop_present(self, hot_ids: Set[str]) -> bool:
        """Hot copy wins. A restart must not keep a duplicate asleep."""
        overlap = [event_id for event_id in self._traces if event_id in hot_ids]
        if not overlap:
            return False
        for event_id in overlap:
            self._forget_trace(event_id)
        self.persist()
        return True

    def take(self, event_id: str) -> Optional[Event]:
        if event_id not in self._traces:
            return None
        bodies = [event for event in self._read_bodies() if isinstance(event, Event)]
        chosen = next((event for event in bodies if event.id == event_id), None)
        self._forget_trace(event_id)
        self._write(event for event in bodies if event.id != event_id)
        return chosen

    def overlapping_ids(self, seed: Event, cap: int = 64) -> List[str]:
        keys = _token_keys(seed.raw_data_anchor)
        found: Set[str] = set()
        for key in keys:
            found |= self._by_token.get(key, set())
            if len(found) >= cap:
                break
        found.discard(seed.id)
        return list(found)[:cap]

    def persist(self) -> None:
        bodies = [
            event
            for event in self._read_bodies()
            if isinstance(event, Event) and event.id in self._traces
        ]
        self._write(bodies)

    def _read_bodies(self) -> List[Event]:
        if not os.path.exists(COLD_FILE):
            return []
        loaded = load_decrypted(COLD_FILE)
        return [event for event in loaded if isinstance(event, Event)]

    def _write(self, events: Iterable[Event]) -> None:
        save_encrypted([event.to_dict() for event in events], COLD_FILE)

    def _remember_trace(self, event: Event) -> None:
        self._forget_trace(event.id)
        keys = _token_keys(event.raw_data_anchor)
        self._traces[event.id] = keys
        for key in keys:
            self._by_token[key].add(event.id)

    def _forget_trace(self, event_id: str) -> None:
        keys = self._traces.pop(event_id, None)
        if not keys:
            return
        for key in keys:
            bucket = self._by_token.get(key)
            if not bucket:
                continue
            bucket.discard(event_id)
            if not bucket:
                del self._by_token[key]
