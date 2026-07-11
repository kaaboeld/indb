import time
import logging
import threading
import asyncio
from typing import Iterator, List, Dict, Any, Optional
from core.event import Event
from core.cache import TTLCache
from core.memory import MemoryManager
from core.resonance_index import ResonanceIndex
from core.resonance_graph import ResonanceGraph
from core.causal_index import CausalIndex
from storage.binary import load_decrypted, save_encrypted
from core.constants import (
    FUSION_DEFAULT_THRESHOLD,
    FUSION_MAX_FUSION_COUNT,
    FUSION_AUTOTUNE_INTERVAL_SEC,
    INTERPRET_MOOD_DEFAULT,
)

logger = logging.getLogger("indb.core")

# INDB v1.0 Core


class INDB:
    # INDB v1.0 Core (Distributed)
    def __init__(self, raft_node=None):
        # Load from Encrypted Binary Storage
        logger.info("Initializing storage...")
        try:
            loaded_data = load_decrypted()
            logger.info("Loaded %d items from storage.", len(loaded_data))
        except Exception as e:
            logger.error("Storage load failed — starting with empty state: %s", e)
            loaded_data = []

        self.resonance_index = ResonanceIndex()
        self.resonance_graph = ResonanceGraph.load()
        self.causal_index = CausalIndex.load()
        self.memory = MemoryManager(on_compaction=self._sync_resonance_index)
        if len(self.memory) > 0:
            self.causal_index.rebuild(self.memory)
            self.causal_index.persist_if_dirty()
        for item in loaded_data:
            if isinstance(item, dict):
                if item.get("_type") == "FusedEvent":
                     pass
                ev = Event.from_dict(item)
                self.memory.add(ev)
                self.resonance_index.index(ev)
            else:
                self.memory.add(item)
                self.resonance_index.index(item)
        logger.info("Memory initialised: %d events", len(self.memory))

        self.lock = threading.Lock()
        self.raft = raft_node
        if self.raft:
            logger.info("Raft integration enabled (node=%s)", self.raft.node_id)
        else:
            logger.info("Raft integration disabled — standalone mode")

        # Internal Cache (No Redis needed)
        self.cache = TTLCache()

        # Paradox store (separate from events)
        from storage.paradox_store import load_paradoxes

        self.paradoxes: Dict[str, Any] = load_paradoxes()
        logger.info("Paradox store loaded: %d entities", len(self.paradoxes))

        # Analytics Engine
        from core.analytics import INDBAnalytics

        self.analytics = INDBAnalytics(self)

        # Temporal Parser for natural language date queries
        from core.temporal_engine import TemporalParser

        self.temporal_parser = TemporalParser()


        # JIT Rendering Service (Decoupled)
        from services.interpretation.cognitive_firewall import CognitiveFirewall
        from services.interpretation.engine import JITRenderer
        
        self.firewall = CognitiveFirewall()
        self.renderer = JITRenderer(self.cache, self.firewall)

        # Source Registry (v0.7.0)
        from core.source import Source, SourceType
        self.source_registry: Dict[str, Source] = {}
        
        # Event Fusion Engine
        try:
            from services.fusion.engine import EventFusion

            self.fusion_engine = EventFusion(
                config={
                    "enabled": True,
                    "threshold": FUSION_DEFAULT_THRESHOLD,
                    "strategy": "auto",
                    "max_fusion_count": FUSION_MAX_FUSION_COUNT,
                }
            )
            logger.info(
                "Event fusion enabled (threshold=%.2f, max_count=%d)",
                FUSION_DEFAULT_THRESHOLD,
                FUSION_MAX_FUSION_COUNT,
            )
        except ImportError:
            self.fusion_engine = None
            logger.warning("Event fusion disabled — module not found")

        # State for Auto-Tuning
        self._last_tune_time = 0.0

        logger.info(
            "INDB v0.3.0 ready — events=%d  encrypted=yes  cache=active",
            len(self.memory),
        )

    def set_raft(self, raft_node):
        """Set Raft node after initialization (lazy activation)"""
        self.raft = raft_node
        if self.raft:
            logger.info("Raft integration enabled (node=%s)", self.raft.node_id)
        else:
            logger.warning("Raft integration disabled")

    # Analytics Methods
    def _check_initialized(self):
        """Ensure database is initialized."""
        if not hasattr(self, "memory") or self.memory is None:
             raise Exception("Database not initialized")

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive database statistics."""
        return self.analytics.get_overview()

    def get_report(self, format: str = "text") -> str:
        """Generate analytics report."""
        return self.analytics.generate_report(format)

    def get_insights(self) -> List[str]:
        """Get actionable insights."""
        return self.analytics.get_insights()

    # ------------------------------------------------------------------
    # Public Event Query API
    # Routes should use these methods instead of accessing db.memory directly.
    # ------------------------------------------------------------------

    def get_events(self, limit: int = 100, offset: int = 0) -> List[Event]:
        """
        Return a page of events from memory.

        Args:
            limit:  Maximum number of events to return (default 100).
            offset: Number of events to skip from the start.

        Returns:
            Slice of the current memory stream.
        """
        return list(self.memory)[offset: offset + limit]

    def get_event_count(self) -> int:
        """Return the total number of events currently in memory."""
        return len(self.memory)

    def iter_events(self) -> Iterator[Event]:
        """
        Return a read-only iterator over all events in memory.
        Prefer this over direct memory access in read-only paths.
        """
        return iter(self.memory)

    def print_report(self):
        """Write analytics report to log."""
        logger.info(self.get_report())

    def filter_by_temporal_query(self, events: List[Event], temporal_query: str) -> List[Event]:
        """
        Filter events based on natural language temporal query.

        Supports:
          - 'relative' criteria (Before/After/During) via RelativeTemporalParser
          - 'range' criteria (last X hours, yesterday, today) via TemporalParser
          - 'metadata' criteria (seasons, quarters) via legacy metadata path

        Args:
            events: List of events to filter
            temporal_query: Natural language query string

        Returns:
            Filtered list of events matching temporal criteria
        """
        if not temporal_query or temporal_query.strip() == "":
            return events

        # Parse query into criteria
        criteria = self.temporal_parser.parse(temporal_query)

        ctype = criteria.get("type")

        # ── Relative criteria (Before / After / During) ────────────────
        if ctype == "relative":
            filtered = []
            for event in events:
                ts = getattr(event, "timestamp", None)
                if ts is None:
                    continue
                if not self.temporal_parser.matches(ts, criteria):
                    continue
                # Optional location hint filter
                hint = criteria.get("location_hint")
                if hint:
                    loc = getattr(event, "location", "") or ""
                    if hint.lower() not in loc.lower():
                        continue
                filtered.append(event)
            return filtered

        # ── Range criteria (last X hours, yesterday, today) ────────────
        if ctype == "range":
            return [
                event for event in events
                if getattr(event, "timestamp", None) is not None
                and self.temporal_parser.matches(event.timestamp, criteria)
            ]

        # ── Legacy metadata-based criteria (seasons, quarters, …) ──────
        filtered = []
        for event in events:
            if hasattr(event, "temporal_metadata") and event.temporal_metadata:
                if self.temporal_parser.matches_criteria(event.temporal_metadata, criteria):
                    filtered.append(event)

        return filtered

    def _persist(self):
        """Save state to encrypted binary file."""
        logger.debug("Persisting %d events to storage", len(self.memory))
        data = [e.to_dict() for e in self.memory]
        save_encrypted(data)

    def update_event(self, updated_event):
        """Update existing event (used for fusion)"""
        for i, event in enumerate(self.memory):
            if event.id == updated_event.id:
                self.memory[i] = updated_event
                self.resonance_index.index(updated_event)
                self._persist()
                return updated_event

        # Event not found, append as new
        self.memory.add(updated_event)
        self.resonance_index.index(updated_event)
        self._persist()
        return updated_event

    MAX_REGISTRY_SIZE = 1000

    def register_source(self, source) -> str:
        """
        Register a new source (passport) in the registry.

        Raises:
            ValueError: If the registry has reached MAX_REGISTRY_SIZE.
        """
        if len(self.source_registry) >= self.MAX_REGISTRY_SIZE:
            logger.warning(
                "Source registry full (%d/%d) — rejecting source id=%s. "
                "Consider persisting the registry or increasing MAX_REGISTRY_SIZE.",
                len(self.source_registry),
                self.MAX_REGISTRY_SIZE,
                source.id,
            )
            raise ValueError(
                f"Source registry is full ({self.MAX_REGISTRY_SIZE} entries). "
                "Cannot register new source."
            )
        self.source_registry[source.id] = source
        return source.id

    def get_source(self, source_id: str):
        """Get source by ID."""
        return self.source_registry.get(source_id)

    def _sync_resonance_index(self) -> None:
        """Rebuild horizontal structures after memory compaction (prune / TTL)."""
        self.resonance_index.rebuild(self.memory)
        self.causal_index.rebuild(self.memory)
        valid = {e.id for e in self.memory}
        self.resonance_graph.prune_missing(valid)
        self.causal_index.prune_missing(valid)
        self.resonance_graph.persist_if_dirty()
        self.causal_index.persist_if_dirty()
        logger.debug("Horizontal indexes synced (%d events)", len(self.memory))

    def _purge_expired(self):
        """TTL Garbage Collection — delegates to MemoryManager."""
        removed = self.memory.purge_expired(time.time())
        if removed:
            self._persist()



    def _store_event(self, event: Event) -> Event:
        """Internal method to effectively store the event (Fusion + Append)"""
        # Periodic Auto-Tuning
        now = time.time()
        if self.fusion_engine and self.fusion_engine.config["enabled"]:
            if (now - self._last_tune_time) > FUSION_AUTOTUNE_INTERVAL_SEC:
                try:
                    metrics = self.analytics.get_system_health()
                    new_th = self.fusion_engine.tune_threshold(metrics)
                    self._last_tune_time = now
                except Exception as e:
                    logger.warning(
                        "Auto-tuning failed: %s", e, exc_info=True
                    )

        # Try fusion if engine is available
        if self.fusion_engine and self.fusion_engine.config["enabled"]:
            events_snapshot = list(self.memory)
            try:
                similar = self.fusion_engine.find_similar_events(
                    event,
                    events_snapshot,
                    self.fusion_engine.config["threshold"],
                    1
                )

                if similar:
                    existing = similar[0]["event"]
                    should_fuse, strategy = self.fusion_engine.should_fuse(similar[0]["similarity"])

                    if should_fuse:
                        with self.lock:
                            fused = self.fusion_engine.fuse_events(existing, event, strategy)
                            self.update_event(fused)
                            logger.debug(
                                "Fused event %s into %s (strategy=%s)",
                                event.id[:8], fused.id[:8], strategy,
                            )
                            return fused
            except Exception as e:
                logger.warning(
                    "Fusion skipped for event %s: %s", event.id[:8], e
                )

        # No fusion or fusion skipped — store as new event
        logger.debug("Storing new event %s (memory=%d)", event.id[:8], len(self.memory))
        with self.lock:
            self._purge_expired()
            self.memory.add(event)
            self.resonance_index.index(event)

            # Update Penalty Engine corpus stats for adaptive frequency tracking
            if self.fusion_engine and hasattr(self.fusion_engine, 'penalty_engine'):
                self.fusion_engine.penalty_engine.update_corpus_stats(event.raw_data_anchor)
            
            self._persist()
            return event

    def apply_event(self, event_data: Dict[str, Any]) -> Event:
        """
        State Machine Apply: Called when a log entry is committed.
        Converts dict to Event and applies it to storage.
        """
        # Check if it's already an event (local bypass) or dict (replicated)
        if isinstance(event_data, dict):
             event = Event.from_dict(event_data)
             return self._store_event(event)

        if isinstance(event_data, Event):
             return self._store_event(event_data)
        
        raise ValueError("Invalid event data type")

    async def ingest(
        self,
        raw_data_anchor: List[str],
        location: str,
        ttl: Optional[int] = None,
        blind_payload: Optional[str] = None,
        binary_payload: Optional[bytes] = None,
        source_id: Optional[str] = None,
        temporal_metadata: Optional[Dict[str, Any]] = None,
        signature: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
        timestamp: Optional[float] = None,
    ) -> Event:
        """
        Public Ingest API.
        If Raft is enabled:
          - If Leader: Replicates to log AND WAITS for commit application.
          - If Follower: Rejects (Client must retry with Leader).
        If Standalone:
          - Directly stores.
        """
        # Create Event object tentatively
        if signature:
            from core.signing import verify_event_signature, normalize_signature_block

            probe = {
                "id": id,
                "timestamp": timestamp if timestamp is not None else time.time(),
                "raw_data_anchor": raw_data_anchor,
                "location": location,
                "ttl": ttl,
                "blind_payload": blind_payload,
                "signature": signature,
            }
            if not id:
                raise ValueError("Signed events require an explicit id")
            valid, key_id, err = verify_event_signature(probe)
            if not valid:
                raise ValueError(f"Invalid event signature: {err}")
            signature = normalize_signature_block(signature)

        event = Event(
            raw_data_anchor=raw_data_anchor,
            location=location,
            id=id,
            timestamp=timestamp,
            ttl=ttl,
            blind_payload=blind_payload,
            binary_payload=binary_payload,
            source_id=source_id,
            signature=signature,
        )
        if temporal_metadata:
            event.temporal_metadata = temporal_metadata

        # Distributed Consensus Check
        if self.raft:
            state_val = self.raft.state.value if hasattr(self.raft.state, "value") else self.raft.state

            if state_val == "Leader":
                logger.debug("Replicating event %s via Raft", event.id[:8])
                success = await self.raft.replicate(event.to_dict())
                if success:
                    max_wait = 5.0
                    wait_interval = 0.05
                    waited = 0.0

                    while waited < max_wait:
                        if any(e.id == event.id for e in self.memory):
                            logger.debug("Event %s committed and applied by Raft", event.id[:8])
                            return event
                        await asyncio.sleep(wait_interval)
                        waited += wait_interval

                    logger.warning(
                        "Event %s replicated to Raft log but not yet applied (wait=%.1fs timeout)",
                        event.id[:8], max_wait,
                    )
                    return event
                else:
                    raise Exception("Raft Replication Failed (Quorum not reached)")

            elif state_val == "Follower":
                leader_id = self.raft.current_leader
                if leader_id is None:
                    logger.warning(
                        "Write rejected on follower node=%s: no leader elected yet",
                        self.raft.node_id,
                    )
                    raise Exception("Cluster Unavailable (No leader elected)")
                logger.info(
                    "Write rejected on follower node=%s: redirect to leader=%s",
                    self.raft.node_id, leader_id,
                )
                raise Exception(f"RedirectToLeader:{leader_id}")

            else:
                logger.warning(
                    "Write rejected: cluster state=%s — election in progress", state_val
                )
                raise Exception("Cluster Unavailable (Election in progress)")

        # Standalone Mode
        return self._store_event(event)

    def scan(
        self,
        filter_key: str,
        filter_value: str,
        context_mood: str = None,
        events_to_scan: Optional[List[Event]] = None,
    ) -> List[Event]:
        """Scan + JIT Render. context_mood from caller or INTERPRET_MOOD_DEFAULT."""
        self._purge_expired()  # Lazy GC on read
        mood = context_mood or INTERPRET_MOOD_DEFAULT
        results = []

        # Use provided events or default to all memory
        events_source = events_to_scan if events_to_scan is not None else self.memory
        
        with self.lock:
            for i, event_original in enumerate(events_source):
                # Naive filter update: check if tokens match or location matches
                
                # Safe attribute access helper
                def get_attr(obj, attr, default=None):
                    if isinstance(obj, dict):
                        return obj.get(attr, default)
                    return getattr(obj, attr, default)

                match = True
                loc = get_attr(event_original, 'location', '')
                
                if not filter_key:
                    # No filter = match all
                    match = True
                
                elif filter_key == "location":
                    # Case-insensitive partial match
                    if not filter_value.lower() in str(loc).lower():
                        match = False
                
                elif filter_key == "temporal":
                    # Use V2 Temporal Engine from Phase 17
                    timestamp = get_attr(event_original, 'timestamp', 0.0)
                    criteria = self.temporal_parser.parse(filter_value)
                    if not self.temporal_parser.matches(timestamp, criteria):
                        match = False
                
                else:
                    # Generic key:value search in raw_data_anchor
                    match = False
                    raw_anchor = get_attr(event_original, 'raw_data_anchor', [])
                    if raw_anchor:
                        for item in raw_anchor:
                            item_str = str(item).lower()
                            if filter_value:
                                # Strict key:value match
                                search_pattern = f"{filter_key}:{filter_value}".lower()
                                if search_pattern in item_str:
                                    match = True
                                    break
                            else:
                                # Generic substring match (for simple queries like 'timestamp' or '2025')
                                if filter_key.lower() in item_str:
                                    match = True
                                    break

                if match:
                    import copy
                    event_copy = copy.deepcopy(event_original)
                    context_dict = {"mood": mood, "location": loc}
                    
                    # Refactored: Delegate to JITRenderer
                    rendered_event = self.renderer.render(event_copy, context_dict)
                    results.append(rendered_event)
        
        # Phase 17: Cognitive Metrics Tracking
        total_events = len(events_source)
        avg_resonance = sum(r.get("activation_score", 0) for r in results) / len(results) if results else 0.0
        
        # Cognitive Load = Effort (events scanned) * Complexity Factor (1.0 baseline)
        cognitive_load = total_events * 0.05
        
        self.analytics.track_cognitive_state(cognitive_load, avg_resonance)
        
        return results

    def detect_patterns(self) -> Dict[str, Any]:
        """
        Run Neural Pattern Recognition (DBSCAN) on the entire memory stream.
        """
        if self.fusion_engine:
            return self.fusion_engine.detect_global_patterns(self.memory.get_all())
        return {"error": "Fusion Engine disabled"}

    def _event_signature_key_id(self, event: Any) -> Optional[str]:
        if isinstance(event, dict):
            sig = event.get("signature")
        else:
            sig = getattr(event, "signature", None)
        if not sig:
            return None
        return sig.get("key_id")

    def events_by_key_id(self, key_id: str) -> List[Event]:
        """Return events signed by the given key_id hash."""
        from core.signing import compute_key_id

        results: List[Event] = []
        with self.lock:
            for event in self.memory:
                sig = event.signature if hasattr(event, "signature") else None
                if not sig:
                    continue
                event_key_id = sig.get("key_id")
                if not event_key_id and sig.get("public_key"):
                    event_key_id = compute_key_id(sig["public_key"])
                if event_key_id == key_id:
                    results.append(event)
        return results

    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        with self.lock:
            for event in self.memory:
                if event.id == event_id:
                    return event
        return None

    def restore_signed_events(
        self,
        events: List[Dict[str, Any]],
        key_id: str,
        verify_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Verify and optionally re-import events for a signing identity (key_id).
        """
        from core.signing import verify_event_signature, normalize_signature_block

        verified: List[Dict[str, Any]] = []
        failed: List[Dict[str, Any]] = []
        imported = 0
        skipped = 0

        existing_ids = {e.id for e in self.memory.get_all()}

        for raw in events:
            event_id = raw.get("id", "unknown")
            valid, resolved_key_id, err = verify_event_signature(raw)
            if not valid:
                failed.append({"id": event_id, "reason": err or "invalid signature"})
                continue

            if not resolved_key_id:
                failed.append({"id": event_id, "reason": "unsigned event"})
                continue

            if resolved_key_id != key_id:
                failed.append({"id": event_id, "reason": "key_id mismatch"})
                continue

            verified.append(raw)
            if verify_only:
                continue

            if event_id in existing_ids:
                skipped += 1
                continue

            sig = normalize_signature_block(raw["signature"])
            event = Event.from_dict({**raw, "signature": sig})
            self._store_event(event)
            existing_ids.add(event.id)
            imported += 1

        return {
            "key_id": key_id,
            "verify_only": verify_only,
            "verified_count": len(verified),
            "failed_count": len(failed),
            "imported_count": imported,
            "skipped_count": skipped,
            "failed": failed,
        }

    def store_paradox(self, paradox: Any) -> None:
        from storage.paradox_store import save_paradoxes

        with self.lock:
            self.paradoxes[paradox.id] = paradox
            save_paradoxes(self.paradoxes)

    def get_paradox(self, paradox_id: str) -> Optional[Any]:
        return self.paradoxes.get(paradox_id)
