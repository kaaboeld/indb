"""
Memory Manager for INDB
Handles the in-memory event stream, entropy/pruning, and lifecycle management.
"""

from typing import Callable, List, Optional, Deque, Dict, Any
from collections import deque
import time
import logging

from core.event import Event

logger = logging.getLogger(__name__)

CompactionCallback = Callable[[], None]


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
        self.pruning_threshold = pruning_threshold
        self.is_pruning = False
        self._on_compaction = on_compaction

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
        
        if len(self.stream) > self.capacity:
            self.prune()

    def get_all(self) -> List[Event]:
        """Return reference to stream."""
        return self.stream
        
    def prune(self):
        """
        Entropy Pruning:
        Remove events with low 'Mass' (Fusion Count) to free up space.
        High mass events (Significant memories) are preserved.
        """
        if self.is_pruning:
            return
            
        self.is_pruning = True
        try:
            target_size = int(self.capacity * self.pruning_threshold)
            remove_count = len(self.stream) - target_size
            
            if remove_count <= 0:
                return

            logger.info(f"Memory Capacity Reached ({len(self.stream)}/{self.capacity}). Pruning {remove_count} events...")
            
            # Entropy Algorithm:
            # 1. Sort by Mass (Fusion Count) and Time (Recency)
            # We want to KEEP: Recent events AND Heavy events.
            # We want to DROP: Old, Light events.
            
            # Simple heuristic optimization:
            # Just slice the oldest ones first, but check for "High Gravity" items to preserve?
            # For v0.3 (Alpha), we will implement a "Smart Tail Cut".
            
            # We iterate from the start (oldest) and remove items that have low mass.
            new_stream = []
            removed = 0
            
            # Keep the last N events unconditionally (Short-term memory buffer)
            # Ensure buffer doesn't eat the whole capacity (max 50%)
            short_term_buffer = min(1000, int(self.capacity * 0.5))
            
            candidates = self.stream[:-short_term_buffer]
            recent_memory = self.stream[-short_term_buffer:]
            
            for event in candidates:
                if removed < remove_count:
                    # HEURISTIC: Fuse Count > 3 means "Significant". Keep it.
                    if getattr(event, 'fusion_count', 0) > 3:
                        new_stream.append(event)
                    else:
                        # Drop (It's already on disk in indb.bin, so this is just RAM release)
                        removed += 1
                else:
                    new_stream.append(event)
            
            self.stream = new_stream + recent_memory

            logger.info(f"Pruning Complete. New Size: {len(self.stream)}. Removed: {removed} events.")
            if removed > 0:
                self._notify_compaction()

        except Exception as e:
            logger.error(f"Error during memory pruning: {e}")
        finally:
            self.is_pruning = False

    def __len__(self):
        return len(self.stream)

    def __iter__(self):
        return iter(self.stream)

    def __getitem__(self, index):
        return self.stream[index]

    def __setitem__(self, index, value):
        self.stream[index] = value

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
            logger.debug("TTL GC: purged %d expired events", removed)
            self._notify_compaction()
        return removed

    @property
    def events(self) -> List[Event]:
        """Read-only snapshot of the current memory stream."""
        return self.stream
