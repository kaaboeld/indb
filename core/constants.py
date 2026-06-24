"""
INDB Application Constants

Centralized constants for the INDB backend application.
All hardcoded values should be defined here for easy maintenance.
"""

# ==============================================================================
# Application Version
# ==============================================================================

VERSION = "0.7.0"
"""INDB application version. Used in health, OpenAPI, and responses."""

INDB_PRODUCT_NAME = "Interpretational Database"
"""Public product category — memory with meaning at read time, not archive storage."""

INDB_PRODUCT_ACRONYM = "INDB"
"""I(nterpretational) D(ata)b(ase)."""

# ==============================================================================
# Protocol Constants
# ==============================================================================

PROTOCOL_MAGIC = b"INDB"
"""Magic bytes for INDB protocol identification"""

PROTOCOL_VERSION = 1
"""Current protocol version number"""

# ==============================================================================
# Default Ports
# ==============================================================================

DEFAULT_HTTP_PORT = 8000
"""Default port for HTTP/REST API server"""

DEFAULT_UDP_PORT = 9000
"""Default port for UDP protocol server"""

DEFAULT_WS_PORT = 9001
"""Default port for WebSocket server"""

DEFAULT_BSON_PORT = 9002
"""Default port for BSON protocol server"""

DEFAULT_GRPC_PORT = 50051
"""Default port for gRPC server"""

# ==============================================================================
# Storage Configuration
# ==============================================================================

DEFAULT_STORAGE_PATH = "./indb.bin"
"""Default path for binary storage file"""

DEFAULT_CACHE_TTL_SECONDS = 60
"""Default cache time-to-live in seconds"""

DEFAULT_MAX_EVENTS_IN_MEMORY = 10000
"""Maximum number of events to keep in memory"""

DEFAULT_GC_INTERVAL_HOURS = 24
"""Garbage collection interval in hours"""

# ==============================================================================
# CORS Defaults
# ==============================================================================

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:9000",
    "http://127.0.0.1:9000"
]
"""Default allowed CORS origins for development"""

DEFAULT_CORS_METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
"""Default allowed HTTP methods for CORS"""

DEFAULT_CORS_HEADERS = ["*"]
"""Default allowed headers for CORS"""

# ==============================================================================
# Logging Configuration
# ==============================================================================

DEFAULT_LOG_LEVEL = "INFO"
"""Default logging level"""

# Fusion
DEFAULT_FUSION_THRESHOLD = 0.7
DEFAULT_SIMILARITY_THRESHOLD = 0.5

# Temporal
SEASONS = {
    "winter": [12, 1, 2],
    "spring": [3, 4, 5],
    "summer": [6, 7, 8],
    "autumn": [9, 10, 11],
    "fall": [9, 10, 11],
}

TIME_OF_DAY = {"morning": (6, 12), "afternoon": (12, 18), "evening": (18, 22), "night": (22, 6)}

# Status Codes
STATUS_SUCCESS = 0
STATUS_ERROR = 1
STATUS_AUTH_FAILED = 2
STATUS_NOT_FOUND = 3

# Error Messages
ERROR_AUTH_FAILED = "Authentication failed"
ERROR_INVALID_REQUEST = "Invalid request format"
ERROR_NOT_FOUND = "Resource not found"
ERROR_INTERNAL = "Internal server error"

# Limits
MAX_QUERY_LIMIT = 1000
DEFAULT_QUERY_LIMIT = 100
MAX_PACKET_SIZE = 65535  # UDP max packet size

# mTLS
MTLS_CA_CERT_PATH = "certs/ca.crt"
MTLS_SERVER_CERT_PATH = "certs/server.crt"
MTLS_SERVER_KEY_PATH = "certs/server.key"

# ==============================================================================
# Cache Defaults
# ==============================================================================

CACHE_QUERY_MAXSIZE = 1000
"""Maximum items in the query result cache."""

CACHE_QUERY_TTL_SEC = 300
"""Query cache TTL: 5 minutes."""

CACHE_FUSION_MAXSIZE = 500
"""Maximum items in the fusion candidate cache."""

CACHE_FUSION_TTL_SEC = 600
"""Fusion cache TTL: 10 minutes."""

CACHE_DECORATOR_DEFAULT_MAXSIZE = 128
"""Default maxsize for the @ttl_cache decorator."""

CACHE_DECORATOR_DEFAULT_TTL_SEC = 300
"""Default TTL for the @ttl_cache decorator: 5 minutes."""

# ==============================================================================
# Fusion Engine Constants
# ==============================================================================

FUSION_MAX_FUSION_COUNT = 100
"""Maximum number of source events a single FusedEvent may accumulate."""

FUSION_DEFAULT_THRESHOLD = 0.75
"""Baseline fusion threshold used by the auto-tuner as the target value."""

FUSION_FULL_MERGE_THRESHOLD = 0.95
"""Similarity above this triggers full_merge strategy."""

FUSION_SEMANTIC_LINK_THRESHOLD = 0.6
"""Similarity above this (but below config threshold) creates a semantic link only."""

# Similarity weights — Neural path (semantic embeddings available)
FUSION_W_SEMANTIC = 0.70
"""Neural path: weight for semantic embedding similarity."""

FUSION_W_LOCATION_NEURAL = 0.15
"""Neural path: weight for location match."""

FUSION_W_TEMPORAL_NEURAL = 0.15
"""Neural path: weight for temporal proximity."""

# Similarity weights — Heuristic path (fallback, no embeddings)
FUSION_W_TOKEN = 0.60
"""Heuristic path: weight for Jaccard token similarity."""

FUSION_W_LOCATION_HEURISTIC = 0.20
"""Heuristic path: weight for location match."""

FUSION_W_TEMPORAL_HEURISTIC = 0.20
"""Heuristic path: weight for temporal proximity."""

# Auto-tuner thresholds
FUSION_AUTOTUNE_CPU_HIGH = 80.0
"""CPU % above which fusion threshold is tightened (strict mode)."""

FUSION_AUTOTUNE_MEM_HIGH = 80.0
"""Memory % above which fusion threshold is relaxed (aggressive mode)."""

FUSION_AUTOTUNE_CPU_LOW = 50.0
"""CPU % below which memory-driven relaxation is allowed."""

FUSION_AUTOTUNE_STEP = 0.05
"""Threshold adjustment step per auto-tune cycle."""

FUSION_AUTOTUNE_NORMALIZE_STEP = 0.01
"""Smaller step used when drifting back towards the default threshold."""

FUSION_AUTOTUNE_INTERVAL_SEC = 5.0
"""Minimum seconds between consecutive auto-tune cycles."""


# Pattern detection intervals (in seconds)
FUSION_INTERVAL_HOUR = 3_600
"""1 hour in seconds — used for burst and daily pattern classification."""

FUSION_INTERVAL_DAY = 86_400
"""1 day in seconds — boundary between daily and weekly patterns."""

FUSION_INTERVAL_WEEK = 604_800
"""1 week in seconds — boundary between weekly and monthly patterns."""

FUSION_BURST_MIN_OCCURRENCES = 3
"""Minimum event count within 1 hour to be classified as a burst pattern."""

# ==============================================================================
# Analytics / History Trim Limits
# ==============================================================================

ANALYTICS_SYSTEM_HISTORY_LIMIT = 100
"""Maximum system health samples kept in memory."""

ANALYTICS_QUERY_HISTORY_LIMIT = 1_000
"""Maximum query timing samples kept in memory."""

ANALYTICS_FUSION_HISTORY_LIMIT = 1_000
"""Maximum fusion history entries kept in memory."""

ANALYTICS_COGNITIVE_HISTORY_LIMIT = 1_000
"""Maximum cognitive operation history entries kept in memory."""

ANALYTICS_INSIGHT_EVENT_THRESHOLD = 1_000
"""Event count above which low-fusion-rate is flagged as an insight."""

ANALYTICS_INSIGHT_LATENCY_WARN_MS = 100.0
"""Average query latency above this (ms) triggers a performance warning insight."""

ANALYTICS_INSIGHT_LATENCY_GOOD_MS = 10.0
"""Average query latency below this (ms) triggers a positive performance insight."""


# ==============================================================================
# Source Connector Defaults
# ==============================================================================

MOLTBOOK_MAX_TOKENS = 200
"""Maximum number of tokens extracted from a Moltbook post to keep Event size bounded."""

# ==============================================================================
# Object Pool
# ==============================================================================

OBJECT_POOL_WARMUP_SIZE = 100
"""Number of objects pre-allocated in the object pool at startup."""

# ==============================================================================
# Prism Engine Constants
# ==============================================================================

# Identity Alignment multipliers
PRISM_ALIGNMENT_OWNER = 2.0
"""Event owned by the querying identity — strongest personal signal."""

PRISM_ALIGNMENT_TOKEN_MATCH = 1.5
"""Identity key appears in the event tokens — personal context."""

PRISM_ALIGNMENT_DEFAULT = 1.0
"""Event is unrelated to identity — neutral."""

PRISM_ALIGNMENT_ANONYMOUS = 0.5
"""No identity provided — fully neutral baseline."""

# Mass formula
PRISM_MASS_BASE = 1.0
"""Base mass value before logarithmic fusion density is added."""

PRISM_MASS_COLLECTIVE_THRESHOLD = 5.0
"""Mass above this is considered Collective Truth."""

# Insight thresholds
PRISM_INSIGHT_DEEPLY_PERSONAL_ALIGNMENT = 1.5
"""Identity alignment above this generates 'Deeply Personal' insight."""

PRISM_PERSONAL_WEIGHT_RESONANCE_THRESHOLD = 1.0
"""Personal token weight magnitude above this generates a resonance insight."""

PRISM_PERSONAL_WEIGHT_MIN = 0.1
"""Minimum personal weight after negative adjustment."""

# Paradox detection
PRISM_PARADOX_SCORE_PROXIMITY_THRESHOLD = 0.25
"""Two readings are paradoxical when perception_gap >= this value."""

PRISM_PARADOX_MIN_CANDIDATES = 2
"""Minimum candidate count required to evaluate paradox."""

# Default labels (fallback when observer provides no vocabulary)
PRISM_LABEL_SUBJECTIVE = "Subjective Reality"
"""Default label when identity alignment indicates personal context."""

PRISM_LABEL_OBJECTIVE = "Objective Data"
"""Default label when identity alignment is neutral."""

# Default insight strings
PRISM_INSIGHT_DEEPLY_PERSONAL = "Deeply Personal"
PRISM_INSIGHT_COLLECTIVE_TRUTH = "Collective Truth"
PRISM_INSIGHT_DIRECT_HIT = "Direct Hit"
PRISM_INSIGHT_EMOTIONAL_MATCH = "Emotional Match"
PRISM_INSIGHT_TIME_ECHO = "Time Echo"

# ==============================================================================
# Echo Engine Constants
# ==============================================================================

ECHO_WEIGHT_TOKEN = 0.2
"""Token similarity weight in harmonic resonance formula."""

ECHO_WEIGHT_EMOTION = 0.3
"""Emotional proximity weight in harmonic resonance formula."""

ECHO_WEIGHT_META = 0.5
"""Meta / location weight in harmonic resonance formula."""

# ==============================================================================
# Interpretation / JIT Renderer Constants (inhale-exhale-axiom: input → output)
# ==============================================================================

INTERPRET_MOOD_DEFAULT = "Neutral"
"""Default mood when context.mood is absent. Source: request context."""

INTERPRET_FIREWALL_MODE_DEFAULT = "block"
"""Default firewall mode when not specified in request."""

INTERPRET_LIMIT_DEFAULT = 10
"""Default event limit for interpretation response."""

INTERPRET_ACTIVATION_BASELINE = 0.1
"""Baseline activation score before context adjustments."""

INTERPRET_ACTIVATION_LOCATION_MATCH = 0.6
"""Bonus when query location matches event location."""

INTERPRET_ACTIVATION_TEMPORAL_FRESH = 0.2
"""Bonus when temporal_opacity exceeds threshold (recent event)."""

INTERPRET_ACTIVATION_RESONANCE = 0.2
"""Bonus when derived_emotion matches context mood."""

INTERPRET_ACTIVATION_DEFAULT = 0.8
"""Default activation when event lacks computed score (fallback only)."""

INTERPRET_TEMPORAL_OPACITY_THRESHOLD = 0.8
"""Opacity above this = 'recent' event for activation bonus."""

INTERPRET_TEMPORAL_DECAY_FACTOR = 0.001
"""Age decay: opacity = 1 / (1 + age_hours * factor)."""

INTERPRET_EMPTY_ID = ""
"""Placeholder when event.id is absent (axiom: no fake ids)."""

INTERPRET_EMPTY_LOCATION = ""
"""Placeholder when event.location is absent."""

INTERPRET_EMPTY_TIMESTAMP = 0.0
"""Placeholder when event.timestamp is absent."""

INTERPRET_FIREWALL_BLOCKED_EMOTION = "BLOCKED"
"""Emotion label when firewall blocks the event."""

INTERPRET_BLOCKED_ACTIVATION = 0.0
"""Activation/weight when event is blocked (axiom: blocked = zero)."""

INTERPRET_FIREWALL_REASON_DEFAULT = "Firewall Policy"
"""Default reason when firewall blocks but provides no reason."""

INTERPRET_CACHE_TTL_SEC = 60
"""JIT render cache TTL (seconds)."""

# Token profile signals (input-driven: derived from event.raw_data_anchor)
INTERPRET_TOKEN_NEGATIVE = (
    "pain", "blood", "scream", "crash", "fear", "dark", "pressure", "stagnant"
)
INTERPRET_TOKEN_POSITIVE = (
    "smile", "sun", "money", "hug", "flow", "success", "system", "harmony"
)
INTERPRET_TOKEN_HIGH_ENERGY = (
    "fast", "loud", "running", "bass", "adrenaline", "spike"
)

# Event response placeholders (when attribute truly missing)
EVENT_RESPONSE_MISSING_ID = ""
EVENT_RESPONSE_MISSING_LOCATION = ""

# What-If (Hermes-gated hypothetical prediction)
WHAT_IF_RETRY_AFTER_SECONDS = 60
WHAT_IF_LLM_UNAVAILABLE = "Prediction unavailable: LLM (Ollama or Hermes) not reachable."
WHAT_IF_OLLAMA_URL_DEFAULT = "http://localhost:11434"
WHAT_IF_OLLAMA_MODEL_DEFAULT = "llama3.2"
WHAT_IF_HERMES_TIMEOUT = 60
WHAT_IF_MODE_CORE = "core"
WHAT_IF_MODE_LLM = "llm"
WHAT_IF_MODE_BOTH = "both"
WHAT_IF_SUBWAVE_DEFAULT = True

# Horizontal slice (core what-if, no LLM)
RESONANCE_INDEX_MAX_CANDIDATES = 500
SLICE_FACTOR_MIN_LEN = 3
SLICE_SHIFT_MAX = 0.35

# Materialized resonance graph (persisted horizontal edges)
RESONANCE_GRAPH_ENABLED_DEFAULT = True
RESONANCE_GRAPH_MAX_EDGES_PER_SEED = 50
RESONANCE_GRAPH_STALE_SEC = 86400 * 7

# Semantic neighbors (embeddings; optional ML stack)
RESONANCE_SEMANTIC_ENABLED_DEFAULT = True
RESONANCE_SEMANTIC_THRESHOLD = 0.55
RESONANCE_SEMANTIC_TOP_K = 40
RESONANCE_SEMANTIC_POOL_CAP = 250

# Causal / temporal horizontal links
CAUSAL_INDEX_ENABLED_DEFAULT = True
CAUSAL_TIME_WINDOW_SEC = 86400
CAUSAL_INDEX_MAX_LINKS_PER_EVENT = 20

# Memory lifecycle (salience / hot-cold / wake) — see docs/MEMORY_LIFECYCLE.md
MEMORY_RECENCY_TAU_SEC = 86_400.0
MEMORY_HOT_SALIENCE_THRESHOLD = 0.15
MEMORY_WAKE_ECHO_THRESHOLD = 0.85
MEMORY_WAKE_LOCK_THRESHOLD = 0.75
MEMORY_TOUCH_PERSIST_ON_RESONANCE = False
"""If True, Echo/Subwave persist last_resonance_at to disk (one update_event per touch)."""

# Subwave — unified resonance broadcast from anchor
SUBWAVE_LOCK_THRESHOLD = 0.35
SUBWAVE_MAX_NODES = 50
SUBWAVE_WEIGHT_RESONANCE = 0.5
SUBWAVE_WEIGHT_TOKEN = 0.35
SUBWAVE_WEIGHT_FACTOR = 0.15

