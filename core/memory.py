"""
Memory Manager for INDB
Handles the in-memory event stream, entropy/pruning, and lifecycle management.
"""

from typing import Callable, Dict, List, Optional
import time
import logging

from core.event import Event

logger = logging.getLogger(__name__)

CompactionCallback = Callable[[], None]
SleepCallback = Callable[[List[Event]], None]


class MemoryManager:
    """
    Manages the active memory stream of the INDB Kernel.
    
    Principles:
    - Finite Capacity: RAM is finite. We cannot store infinite events.
    - Entropy: Events lose relevance over time unless they have "Mass" (Fusion Count).
    - Pruning: Low-mass events are moved to 'Cold Storage' (Disk only) when capacity is reached.
    """
    
    def __init__(
        self,
        capacity: int = 100000,
        pruning_threshold: float = 0.8,
        on_compaction: Optional[CompactionCallback] = None,
        on_sleep: Optional[SleepCallback] = None,
    ):
        """
        Args:
            capacity: Max number of events to keep in RAM.
            pruning_threshold: When capacity is reached, prune down to this fraction.
            on_compaction: Called after prune or TTL purge shrinks the stream (e.g. rebuild indexes).
        """
        self.capacity = capacity
        # Using a list for now as we need random access for search/scan often.
        # A deque might be faster for appends but slower for slice scans.
        self.stream: List[Event] = []
        self._by_id: Dict[str, Event] = {}
        self.pruning_threshold = pruning_threshold
        self.is_pruning = False
        self._on_compaction = on_compaction
        self._on_sleep = on_sleep

    def set_compaction_callback(self, callback: Optional[CompactionCallback]) -> None:
        self._on_compaction = callback

    def _notify_compaction(self) -> None:
        if self._on_compaction:
            try:
                self._on_compaction()
            except Exception as e:
                logger.warning("Compaction callback failed: %s", e)

    def add(self, event: Event):
        """Add an event to memory. Triggers pruning if needed."""
        self.stream.append(event)
        self._by_id[event.id] = event

        if len(self.stream) > self.capacity:
            self.prune()

    def get(self, event_id: str) -> Optional[Event]:
        """Hot recall by id. Does not walk the stream."""
        return self._by_id.get(event_id)

    def _reindex(self) -> None:
        self._by_id = {event.id: event for event in self.stream}

    def get_all(self) -> List[Event]:
        """Return reference to stream."""
        return self.stream
        
    def _must_stay_hot(self, event: Event) -> bool:
        """Axioms and still-salient events are not exhaled."""
        if getattr(event, "signature", None):
            return True
        from core.memory_salience import compute_salience, is_hot

        return is_hot(compute_salience(event))

    def prune(self) -> List[Event]:
        """
        Exhale: move low-salience events out of hot memory.

        They are handed to on_sleep. The caller keeps them on cold disk.
        Signed events stay. The recent tail stays, so a new observation
        is not forgotten in the same breath that stored it.
        """
        if self.is_pruning:
            return []

        self.is_pruning = True
        slept: List[Event] = []
        try:
            target_size = int(self.capacity * self.pruning_threshold)
            remove_count = len(self.stream) - target_size

            if remove_count <= 0:
                return []

            logger.info(
                "Memory capacity reached (%d/%d). Sending %d events to sleep...",
                len(self.stream),
                self.capacity,
                remove_count,
            )

            new_stream: List[Event] = []

            # Keep the last N events unconditionally (short-term memory).
            short_term_buffer = min(1000, int(self.capacity * 0.5))
            if short_term_buffer <= 0 or short_term_buffer >= len(self.stream):
                candidates: List[Event] = []
                recent_memory = list(self.stream)
            else:
                candidates = self.stream[:-short_term_buffer]
                recent_memory = self.stream[-short_term_buffer:]

            removed = 0
            for event in candidates:
                if removed < remove_count and not self._must_stay_hot(event):
                    slept.append(event)
                    removed += 1
                else:
                    new_stream.append(event)

            self.stream = new_stream + recent_memory
            self._reindex()
            logger.info(
                "Sleep complete. Hot size: %d. Asleep: %d.",
                len(self.stream),
                removed,
            )
        finally:
            self.is_pruning = False

        if slept and self._on_sleep:
            self._on_sleep(slept)
        if slept:
            self._notify_compaction()
        return slept

    def __len__(self):
        return len(self.stream)

    def __iter__(self):
        return iter(self.stream)

    def __getitem__(self, index):
        return self.stream[index]

    def __setitem__(self, index, value):
        previous = self.stream[index]
        self._by_id.pop(previous.id, None)
        self.stream[index] = value
        self._by_id[value.id] = value

    def purge_expired(self, now: float) -> int:
        """
        Remove all events whose TTL has elapsed.

        Args:
            now: Current Unix timestamp (seconds).

        Returns:
            Number of events removed.
        """
        before = len(self.stream)
        self.stream = [
            e for e in self.stream
            if not (e.ttl and (now - e.timestamp) > e.ttl)
        ]
        removed = before - len(self.stream)
        if removed:
            self._reindex()
            logger.debug("TTL GC: purged %d expired events", removed)
            self._notify_compaction()
        return removed

    @property
    def events(self) -> List[Event]:
        """Read-only snapshot of the current memory stream."""
        return self.stream
