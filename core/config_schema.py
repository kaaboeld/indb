"""
INDB Configuration Management

Centralized configuration with Pydantic validation.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator, ConfigDict

from core.secrets import require_secret


class INDBConfig(BaseSettings):
    """Main INDB configuration with validation"""

    model_config = ConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Server Configuration
    server_host: str = Field(default="0.0.0.0", validation_alias="SERVER_HOST")
    server_port: int = Field(default=8000, validation_alias="SERVER_PORT")

    # Database Configuration
    storage_path: str = Field(default="./indb.bin", validation_alias="INDB_STORAGE_PATH")
    key_path: str = Field(default="./indb.key", validation_alias="INDB_KEY_PATH")
    encrypted: bool = Field(default=True, validation_alias="INDB_ENCRYPTED")

    # CORS Configuration
    cors_enabled: bool = Field(default=True, validation_alias="CORS_ENABLED")
    cors_origins: List[str] = Field(default=["*"], validation_alias="CORS_ORIGINS")
    cors_methods: List[str] = Field(default=["*"], validation_alias="CORS_METHODS")
    cors_headers: List[str] = Field(default=["*"], validation_alias="CORS_HEADERS")

    # ML Configuration
    ml_enabled: bool = Field(default=True, validation_alias="ML_ENABLED")
    ml_pattern_recognition: bool = Field(default=True, validation_alias="ML_PATTERN_RECOGNITION")
    ml_semantic_embeddings: bool = Field(default=True, validation_alias="ML_SEMANTIC_EMBEDDINGS")
    ml_emotion_classification: bool = Field(
        default=True, validation_alias="ML_EMOTION_CLASSIFICATION"
    )

    # Authentication Configuration
    jwt_secret: str = Field(
        default_factory=lambda: require_secret("JWT_SECRET", "signs access tokens"),
        validation_alias="JWT_SECRET",
    )
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=30, validation_alias="JWT_EXPIRATION_MINUTES")

    # mTLS Configuration
    mtls_enabled: bool = Field(default=False, validation_alias="MTLS_ENABLED")
    mtls_ca_cert: Optional[str] = Field(default=None, validation_alias="MTLS_CA_CERT")
    mtls_server_cert: Optional[str] = Field(default=None, validation_alias="MTLS_SERVER_CERT")
    mtls_server_key: Optional[str] = Field(default=None, validation_alias="MTLS_SERVER_KEY")

    # WebAuthn Configuration
    webauthn_enabled: bool = Field(default=False, validation_alias="WEBAUTHN_ENABLED")
    webauthn_rp_id: str = Field(default="localhost", validation_alias="WEBAUTHN_RP_ID")
    webauthn_rp_name: str = Field(default="INDB", validation_alias="WEBAUTHN_RP_NAME")

    # Protocol Configuration
    udp_enabled: bool = Field(default=True, validation_alias="UDP_ENABLED")
    udp_port: int = Field(default=9001, validation_alias="UDP_PORT")
    ws_enabled: bool = Field(default=True, validation_alias="WS_ENABLED")
    ws_port: int = Field(default=9001, validation_alias="WS_PORT")
    bson_enabled: bool = Field(default=True, validation_alias="BSON_ENABLED")
    bson_port: int = Field(default=9002, validation_alias="BSON_PORT")

    # Performance Configuration
    cache_ttl_seconds: int = Field(default=60, validation_alias="CACHE_TTL_SECONDS")
    max_events_in_memory: int = Field(default=10000, validation_alias="MAX_EVENTS_IN_MEMORY")
    gc_interval_hours: int = Field(default=24, validation_alias="GC_INTERVAL_HOURS")

    # Logging Configuration
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, validation_alias="LOG_FILE")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from comma-separated string"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @field_validator("cors_methods", mode="before")
    @classmethod
    def parse_cors_methods(cls, v):
        """Parse CORS methods from comma-separated string"""
        if isinstance(v, str):
            return [method.strip() for method in v.split(",")]
        return v

    @field_validator("cors_headers", mode="before")
    @classmethod
    def parse_cors_headers(cls, v):
        """Parse CORS headers from comma-separated string"""
        if isinstance(v, str):
            return [header.strip() for header in v.split(",")]
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @field_validator("server_port", "udp_port", "ws_port", "bson_port")
    @classmethod
    def validate_port(cls, v):
        """Validate port number"""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v


# Global configuration instance
_config: Optional[INDBConfig] = None


def get_config() -> INDBConfig:
    """Get or create global configuration instance"""
    global _config
    if _config is None:
        _config = INDBConfig()
    return _config


def reload_config() -> INDBConfig:
    """Reload configuration from environment"""
    global _config
    _config = INDBConfig()
    return _config
