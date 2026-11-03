"""
Centralized configuration management (v2).
"""
import os
from typing import List, Optional, Union
from pydantic import Field, AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.constants import (
    DEFAULT_HTTP_PORT,
    DEFAULT_UDP_PORT,
    DEFAULT_GRPC_PORT,
    DEFAULT_WS_PORT,
    DEFAULT_BSON_PORT,
    DEFAULT_STORAGE_PATH,
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_MAX_EVENTS_IN_MEMORY,
    DEFAULT_GC_INTERVAL_HOURS,
    DEFAULT_FUSION_THRESHOLD,
    DEFAULT_SIMILARITY_THRESHOLD,
    DEFAULT_LOG_LEVEL,
)

class Settings(BaseSettings):
    """
    Application settings with environment variable validation.
    """
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True 
    )

    # Server Configuration
    # We map environment variables to fields. 
    # Use Field(alias="ENV_VAR") if needed, but matching name works too with case_sensitive=True
    
    # We keep UPPERCASE to match existing usage in codebase
    HTTP_HOST: str = Field(default="0.0.0.0", alias="INDB_HOST")
    HTTP_PORT: int = Field(default=DEFAULT_HTTP_PORT, alias="INDB_PORT")
    
    # Protocol Ports
    UDP_PORT: int = Field(default=DEFAULT_UDP_PORT)
    GRPC_PORT: int = Field(default=DEFAULT_GRPC_PORT)
    BSON_PORT: int = Field(default=DEFAULT_BSON_PORT)
    
    # Storage
    STORAGE_PATH: str = Field(default=DEFAULT_STORAGE_PATH, alias="INDB_STORAGE_PATH")
    CACHE_TTL_SECONDS: int = Field(default=DEFAULT_CACHE_TTL_SECONDS)
    MAX_EVENTS_IN_MEMORY: int = Field(default=DEFAULT_MAX_EVENTS_IN_MEMORY)
    GC_INTERVAL_HOURS: int = Field(default=DEFAULT_GC_INTERVAL_HOURS)
    
    # Algorithms
    FUSION_THRESHOLD: float = Field(default=DEFAULT_FUSION_THRESHOLD)
    SIMILARITY_THRESHOLD: float = Field(default=DEFAULT_SIMILARITY_THRESHOLD)
    
    # Logging
    LOG_LEVEL: str = Field(default=DEFAULT_LOG_LEVEL)
    LOG_FILE: Optional[str] = None
    
    # CORS
    # No "*" by default: combined with CORS_ALLOW_CREDENTIALS it lets any site read
    # authenticated responses. The WUI is served same-origin from /wui and needs no entry.
    CORS_ENABLED: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "*"
    CORS_ALLOW_HEADERS: str = "*"
    
    # Raft
    RAFT_NODE_ID: Optional[str] = None
    RAFT_PEERS: str = ""
    # Shared secret for /raft/vote and /raft/append — required when peers > 0.
    RAFT_RPC_TOKEN: Optional[str] = None
    DATA_DIR: str = "."
    
    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: Optional[str] = None

    # Response Signing
    # Base64-encoded Ed25519 private key (32 raw bytes → 44 base64 chars).
    # If absent, a temporary key is generated per process — signatures will not
    # survive restarts and cannot be independently verified across deployments.
    SIGNING_PRIVATE_KEY: Optional[str] = None

    @property
    def WS_PORT(self) -> int:
        return self.HTTP_PORT # Usually same for FastAPI
        
    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]
        
    @property
    def cors_methods_list(self) -> List[str]:
        return [m.strip() for m in self.CORS_ALLOW_METHODS.split(",") if m.strip()]
        
    @property
    def cors_headers_list(self) -> List[str]:
        return [h.strip() for h in self.CORS_ALLOW_HEADERS.split(",") if h.strip()]
        
    @property
    def raft_peers_list(self) -> List[str]:
        return [p.strip() for p in self.RAFT_PEERS.split(",") if p.strip()]

config = Settings()
