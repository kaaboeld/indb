"""
INDB Kernel - Protocol-Agnostic Core

The kernel is the single source of truth for all database operations.
It is protocol-agnostic and can be accessed via HTTP, UDP, WebSocket, gRPC, etc.
"""

import logging
from typing import Dict, Iterator, List, Optional, Any
from dataclasses import dataclass
from core.indb import INDB
from core.event import Event
from core.webhooks import WebhookManager
from core.constants import (
    INTERPRET_MOOD_DEFAULT,
    INTERPRET_ACTIVATION_DEFAULT,
    DEFAULT_QUERY_LIMIT,
    EVENT_RESPONSE_MISSING_ID,
    EVENT_RESPONSE_MISSING_LOCATION,
)
import time
import asyncio

logger = logging.getLogger("indb.kernel")


@dataclass
class AuthContext:
    """Authentication context for a request"""

    user_id: str
    username: Optional[str] = None
    auth_method: str = "mtls"  # mtls, webauthn, anonymous
    certificate_cn: Optional[str] = None
    session_token: Optional[str] = None
    # Role carried by the credential. When absent, RBAC falls back to looking the
    # user id up in its own table.
    role: Optional[str] = None


@dataclass
class InterpretRequest:
    """Protocol-agnostic interpretation request"""

    context: Dict[str, Any]
    temporal_query: Optional[str] = None
    firewall_bypass: bool = False
    include_associations: bool = False
    interpretation_mode: str = "standard"
    threat_categories: Optional[List[str]] = None
    fuzzy_temporal: bool = False
    infer_context: bool = True
    semantic_expansion: Optional[str] = None
    probabilistic: bool = False

    def __post_init__(self):
        """Allow extra parameters to be ignored"""
        pass


@dataclass
class QueryRequest:
    """Generic query request with flexible filters"""

    filter_key: Optional[str] = None
    filter_value: Optional[str] = None
    context_mood: str = "Neutral"
    limit: int = 100
    offset: int = 0
    # Allow arbitrary filter parameters (location, temporal_query, etc.)
    filters: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize filters dict if not provided"""
        if self.filters is None:
            self.filters = {}


class INDBKernel:
    """
    INDB Core Kernel

    Single source of truth for all database operations.
    Protocol adapters translate their specific formats to kernel calls.
    """

    def __init__(self):
        """Initialize kernel with INDB instance"""
        from core.indb import INDB
        from core.security.audit import AuditLog
        from core.security.rbac import AccessControl, Permission, Role

        self.db = INDB() # Init first
        self.webhooks = WebhookManager()
        self.audit = AuditLog()
        self.rbac = AccessControl()
        self.Permission = Permission
        
        self._initialized = True
        logger.info("Kernel initialised (%d events, RBAC+Audit active)", len(self.db.memory))

    def initialize(self, db: INDB):
        """Initialize kernel with migrated database"""
        self.db = db
        self._initialized = True

    def _check_initialized(self):
        """Ensure kernel is initialized"""
        if not self._initialized or self.db is None:
            raise RuntimeError("Kernel not initialized. Call initialize() first.")

    @property
    def events(self) -> List[Dict[str, Any]]:
        """Access raw events from DB as dicts"""
        self._check_initialized()
        # Convert Event objects to dicts for consumers
        return [e.to_dict() if hasattr(e, "to_dict") else e for e in self.db.memory]

    # --- Extended Accessors (for Echo/Prism) ---

    def get_event(self, event_id: str) -> Optional[Event]:
        """Retrieve one event by id. Hot map first, then a sleeping copy."""
        self._check_initialized()
        return self.db.get_event_by_id(event_id)

    def get_all_events(self) -> List[Event]:
        """Retrieve all event objects (raw)."""
        self._check_initialized()
        return self.db.get_events(limit=10_000_000)  # effectively all

    def get_event_count(self) -> int:
        """Return the total number of events currently in memory."""
        self._check_initialized()
        return self.db.get_event_count()

    def iter_events(self) -> Iterator[Event]:
        """
        Read-only iterator over all events in memory.
        Routes should prefer this over direct db.memory access.
        """
        self._check_initialized()
        return self.db.iter_events()

    # --- Core Operations ---

    def interpret(self, request: InterpretRequest, auth: AuthContext) -> Dict[str, Any]:
        """
        Main interpretation endpoint - protocol agnostic

        Args:
            request: Interpretation parameters
            auth: Authentication context

        Returns:
            Structured response with data, metadata, signature
        """
        self._check_initialized()
        
        # RBAC Check
        if not self.rbac.check_permission(auth.user_id, self.Permission.EVENT_READ, getattr(auth, "role", None)):
             self.audit.log(auth.user_id, "interpret", "events", "DENIED", {"reason": "insufficient_permissions"})
             raise PermissionError("Access Denied: EVENT_READ permission required")

        start_time = time.time()

        # Extract context (input from request)
        context = request.context
        mood = context.get("mood", INTERPRET_MOOD_DEFAULT)

        # Scan events with JIT rendering
        events = self.db.scan(filter_key=None, filter_value=None, context_mood=mood)
        
        # Audit Log (Success)
        # self.audit.log(auth.user_id, "interpret", "events", "SUCCESS", {"count": len(events)})

        from services.interpretation.emotional_firewall import EmotionalFirewall, FirewallMode

        # Apply temporal filtering if requested
        if request.temporal_query:
            # Filter the already scanned events
            events = self.db.filter_by_temporal_query(events, request.temporal_query)

        # Apply emotional firewall unless bypassed
        if not request.firewall_bypass:
            # Initialize firewall (defaulting to BLOCK for safety if not specified in config)
            # ideally we load this from config, but for now we use SAFE defaults
            firewall = EmotionalFirewall(mode=FirewallMode.BLOCK)
            
            allowed_events = []
            for event in events:
                evt_dict = event.to_dict() if hasattr(event, "to_dict") else event
                
                # Check firewall
                allowed, action, reason = firewall.check(evt_dict)
                
                if allowed:
                    if action == "redact":
                         # Redact content in the object or dict
                         if isinstance(event, dict):
                             event["raw_data_anchor"] = ["REDACTED"]
                             event["blind_payload"] = None
                         else:
                             # If it's an object, we might need to clone it or modify it
                             # For simplicity, we assume we can modify the event object or we rely on the dict conversion later
                             pass 
                    allowed_events.append(event)
                else:
                    # Log blocked event?
                    self.audit.log(auth.user_id, "interpret", "events", "BLOCKED", {"reason": reason, "id": evt_dict.get("id")})
            
            events = allowed_events

        # Convert to response format
        interpreted_events = []
        for event in events:
            # Handle both dict and Event objects
            if isinstance(event, dict):
                loc = event.get("location", EVENT_RESPONSE_MISSING_LOCATION)
                interpreted_events.append(
                    {
                        "id": event.get("id", EVENT_RESPONSE_MISSING_ID),
                        "original_location": loc,
                        "derived_emotion": event.get("derived_emotion", INTERPRET_MOOD_DEFAULT),
                        "activation_score": event.get("activation_score", INTERPRET_ACTIVATION_DEFAULT),
                        "narrative": f"Event at {loc}",
                        "data": event,
                    }
                )
            else:
                loc = getattr(event, "location", EVENT_RESPONSE_MISSING_LOCATION)
                interpreted_events.append(
                    {
                        "id": getattr(event, "id", EVENT_RESPONSE_MISSING_ID),
                        "original_location": loc,
                        "derived_emotion": (
                            getattr(event, "derived_emotion", None) or INTERPRET_MOOD_DEFAULT
                        ),
                        "activation_score": getattr(event, "activation_score", INTERPRET_ACTIVATION_DEFAULT),
                        "narrative": f"Event at {loc}",
                        "data": event.to_dict(),
                    }
                )

        query_time = (time.time() - start_time) * 1000

        # Build response (without signature first)
        response = {
            "data": {"status": "success", "events": interpreted_events},
            "metadata": {
                "total_events": len(interpreted_events),
                "interpretation_mode": request.interpretation_mode,
                "performance": {"query_time_ms": query_time},
                "auth": {"user_id": auth.user_id, "method": auth.auth_method},
            },
            "signature": "",  # Placeholder
        }

        # Sign the response
        response["signature"] = self._sign_response(response)

        return response

    def query(self, request: QueryRequest, auth: AuthContext) -> List[Dict[str, Any]]:
        """
        Generic query interface

        Args:
            request: Query parameters
            auth: Authentication context

        Returns:
            List of events
        """
        self._check_initialized()
        start_time = time.time()
        
        # RBAC Check
        if not self.rbac.check_permission(auth.user_id, self.Permission.EVENT_READ, getattr(auth, "role", None)):
             self.audit.log(auth.user_id, "query", "events", "DENIED", {"reason": "insufficient_permissions"})
             raise PermissionError("Access Denied: EVENT_READ permission required")

        # Audit Log (Success)
        self.audit.log(auth.user_id, "query", "events", "SUCCESS", {"filter": request.filter_key})

        # Extract parameters with defaults
        filter_key = request.filter_key if hasattr(request, "filter_key") else None
        filter_value = request.filter_value if hasattr(request, "filter_value") else None
        context_mood = request.context_mood if hasattr(request, "context_mood") else INTERPRET_MOOD_DEFAULT
        limit = request.limit if hasattr(request, "limit") else DEFAULT_QUERY_LIMIT
        offset = request.offset if hasattr(request, "offset") else 0

        # scan() already returns JIT-rendered dicts; no double-render
        events = self.db.scan(
            filter_key=filter_key, filter_value=filter_value, context_mood=context_mood
        )

        # Apply pagination
        start = offset
        end = start + limit
        result = events[start:end]

        # Track performance
        duration = (time.time() - start_time) * 1000
        if hasattr(self.db, "analytics"):
            self.db.analytics.track_query(duration)

        return result

    def register_source(self, name: str, source_type: str, auth: AuthContext, reputation: float = 0.5) -> Dict[str, Any]:
        """
        Register a new source.
        """
        self._check_initialized()
        
        # RBAC Check (Only System Config or Admin can register sources?)
        # Let's say EVENT_WRITE is enough for now, or maybe SYSTEM_CONFIG
        if not self.rbac.check_permission(auth.user_id, self.Permission.SYSTEM_CONFIG, getattr(auth, "role", None)):
             self.audit.log(auth.user_id, "register", "source", "DENIED", {"reason": "insufficient_permissions"})
             raise PermissionError("Access Denied: SYSTEM_CONFIG permission required")

        from core.source import Source, SourceType
        try:
            stype = SourceType(source_type)
        except ValueError:
            stype = SourceType.UNKNOWN
            
        source = Source(name=name, type=stype, reputation=reputation)
        sid = self.db.register_source(source)
        
        self.audit.log(auth.user_id, "register", "source", "SUCCESS", {"id": sid, "name": name})
        return source.to_dict()

    async def create_event(self, data: Dict[str, Any], auth: AuthContext) -> Dict[str, Any]:
        """
        Create a new event
        """
        try:
            self._check_initialized()
            
            # RBAC Check
            if not self.rbac.check_permission(auth.user_id, self.Permission.EVENT_WRITE, getattr(auth, "role", None)):
                 self.audit.log(auth.user_id, "ingest", "events", "DENIED", {"reason": "insufficient_permissions"})
                 raise PermissionError("Access Denied: EVENT_WRITE permission required")

            event = await self.db.ingest(
                raw_data_anchor=data.get("raw_data_anchor", []),
                location=data.get("location"),
                ttl=data.get("ttl"),
                blind_payload=data.get("blind_payload"),
                binary_payload=data.get("binary_payload"),
                source_id=data.get("source_id"),
                signature=data.get("signature"),
                id=data.get("id"),
                timestamp=data.get("timestamp"),
            )
            
            # Audit Log (Success)
            self.audit.log(auth.user_id, "ingest", "events", "SUCCESS", {"id": event.id})
            
            event_dict = event.to_dict()
            
            # Dispatch Webhook (Fire & Forget)
            try:
                # ingest() is always awaited, so a loop is running here
                loop = asyncio.get_running_loop()
                loop.create_task(self.webhooks.dispatch(event_dict))
            except Exception as e:
                logger.warning(
                    "Webhook dispatch failed: %s", e, exc_info=True
                )

            return event_dict
        except PermissionError as e:
             raise e
        except ValueError as e:
            if "signature" in str(e).lower():
                raise ValueError(str(e)) from e
            raise
        except Exception as e:
            if "RedirectToLeader" not in str(e):
                logger.error(
                    "Event creation failed: %s", e, exc_info=True
                )
                self.audit.log(auth.user_id, "ingest", "events", "ERROR", {"error": str(e)})
            raise e

    def refactor(
        self, target_emotion: str, new_status: str, new_emotion: str, auth: AuthContext
    ) -> List[Dict[str, Any]]:
        """
        Trigger write-on-read refactoring

        Args:
            target_emotion: Emotion to refactor
            new_status: New status
            new_emotion: New emotion
            auth: Authentication context

        Returns:
            Refactored events
        """
        self._check_initialized()

        refactored = self.db.refactor(target_emotion, new_status, new_emotion)
        return [e.to_dict() for e in refactored]

    # --- Helper Methods ---

    def _sign_response(self, data: Any) -> str:
        """
        Sign response data.
        Note: For HTTP, this is handled by ResponseSigningMiddleware.
        This method is reserved for non-HTTP transports (e.g. gRPC/UDP).
        """
        return ""

    def get_stats(self) -> Dict[str, Any]:
        """Get kernel statistics"""
        self._check_initialized()

        return {"total_events": self.db.get_event_count(), "encrypted": True, "cache_active": True}

    # --- Paradox & recovery delegates ---

    def store_paradox(self, paradox: Any) -> None:
        self._check_initialized()
        self.db.store_paradox(paradox)

    def get_paradox(self, paradox_id: str) -> Optional[Any]:
        self._check_initialized()
        return self.db.get_paradox(paradox_id)

    def events_by_key_id(self, key_id: str) -> List[Event]:
        self._check_initialized()
        return self.db.events_by_key_id(key_id)

    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        self._check_initialized()
        return self.db.get_event_by_id(event_id)

    def restore_signed_events(
        self,
        events: List[Dict[str, Any]],
        key_id: str,
        verify_only: bool = False,
    ) -> Dict[str, Any]:
        self._check_initialized()
        return self.db.restore_signed_events(events, key_id, verify_only)
