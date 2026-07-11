"""
Application Factory (v2).

Centralizes FastAPI application creation, middleware configuration, and initializing services.
"""
import os
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse

logger = logging.getLogger("indb.app")
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from strawberry.fastapi import GraphQLRouter
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# Core Imports
from core.config import config
from core import constants
from core.instance import indb as kernel
from core.routing import ContentNegotiationRoute
from core.rate_limit import limiter
from core.middleware import (
    MetricsMiddleware, 
    ResponseSigningMiddleware, 
    EncryptionMiddleware, 
    BrotliMiddleware, 
    metrics_endpoint
)
from core.startup import register_startup_handlers
from core.models import HealthStatus

# Router Imports
from routes import query as query_router
from routes import events as events_router
from routes import websockets as websockets_router
from routes import health as health_router
from routes import system as system_router
from routes import analytics as analytics_router
from routes.lens import router as lens_router
from routes.contact import router as contact_router

# Interfaces
from interfaces.graphql.schema import schema as graphql_schema
from interfaces.mcp.server import create_mcp_app, get_streamable_lifespan
from interfaces.rest.loadbalancer import router as loadbalancer_router

# Raft
from core.raft.node import RaftNode
from core.raft.api import router as raft_router
import core.raft.api

def create_app() -> FastAPI:
    """
    Factory function for creating the INDB FastAPI application.
    """
    # --------------------------------------------------------------------------
    # Initialize Core Services (Raft) — done before lifespan so raft_node
    # is captured in the lifespan closure.
    # --------------------------------------------------------------------------
    raft_node = None
    raft_enabled = os.getenv("RAFT_ENABLED", "true").lower() == "true"

    if raft_enabled and config.RAFT_NODE_ID:
        logger.info("Raft consensus: initializing node=%s", config.RAFT_NODE_ID)
        cleaned_peers = [p for p in config.raft_peers_list if config.RAFT_NODE_ID not in p]

        raft_node = RaftNode(
            node_id=config.RAFT_NODE_ID,
            peers=cleaned_peers,
            storage_dir=config.DATA_DIR,
            kernel=kernel
        )

        core.raft.api.raft_node = raft_node
        kernel.db.set_raft(raft_node)
        logger.info("Raft consensus enabled (peers=%d)", len(cleaned_peers))
    else:
        logger.info("Raft consensus disabled — standalone mode")

    # --------------------------------------------------------------------------
    # Lifespan — replaces deprecated @app.on_event handlers
    # --------------------------------------------------------------------------
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # ── STARTUP ───────────────────────────────────────────────────────────
        logger.info("Running startup integrity checks...")
        try:
            from tests.integrity_check import run_integrity_checks
            if run_integrity_checks():
                logger.info("Startup integrity checks: all passed")
            else:
                logger.warning("Startup integrity checks: one or more FAILED (continuing)")
        except Exception as e:
            logger.warning("Could not run startup integrity checks: %s", e)

        if raft_node:
            logger.info("Starting Raft consensus node...")
            raft_node.start()

        from services.sources import source_manager
        await source_manager.start_all(kernel)

        streamable_lifespan = get_streamable_lifespan()
        if streamable_lifespan is not None:
            async with streamable_lifespan:
                yield  # ── Application runs here ─────────────────────────────────────
        else:
            yield  # ── Application runs here ─────────────────────────────────────

        # ── SHUTDOWN ──────────────────────────────────────────────────────────
        if raft_node:
            await raft_node.stop()
        from services.sources import source_manager  # noqa: F811 (reimport for clarity)
        await source_manager.stop_all()
        logger.info("Shutdown complete")

    # --------------------------------------------------------------------------
    # Create App Instance
    # --------------------------------------------------------------------------
    app = FastAPI(
        title="INDB Core Kernel",
        description=(
            f"{constants.INDB_PRODUCT_ACRONYM} — {constants.INDB_PRODUCT_NAME}. "
            "Cognitive memory (not archive). Inhale, exhale, resonate, interpret."
        ),
        version=constants.VERSION,
        docs_url=None,
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    
    # Set Global Route Class
    app.router.route_class = ContentNegotiationRoute
    
    # Inject Kernel into State
    app.state.indb = kernel
    
    # --------------------------------------------------------------------------
    # Middleware Configuration
    # --------------------------------------------------------------------------
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    # CORS
    if config.CORS_ENABLED:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=config.cors_origins_list,
            allow_credentials=config.CORS_ALLOW_CREDENTIALS,
            allow_methods=config.cors_methods_list,
            allow_headers=config.cors_headers_list,
        )

    # Custom Middleware Stack (Order: Outer -> Inner)
    # 1. Metrics (Outer)
    # 2. Compression
    # 3. Security (Inner)
    app.add_middleware(ResponseSigningMiddleware)
    app.add_middleware(EncryptionMiddleware)
    app.add_middleware(BrotliMiddleware, minimum_size=1000)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(MetricsMiddleware)

    # --------------------------------------------------------------------------
    # OpenTelemetry
    # --------------------------------------------------------------------------
    trace.set_tracer_provider(TracerProvider())

    otel_endpoint = config.OTEL_EXPORTER_OTLP_ENDPOINT

    if otel_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            span_processor = BatchSpanProcessor(OTLPSpanExporter())
            trace.get_tracer_provider().add_span_processor(span_processor)
            logger.info("OpenTelemetry enabled (OTLP -> %s)", otel_endpoint)
        except ImportError:
            logger.warning("OpenTelemetry OTLP exporter not installed — tracing disabled")
    else:
        # No endpoint configured — disable tracing silently (avoid console span spam in Docker logs)
        logger.debug("OpenTelemetry: no OTEL_EXPORTER_OTLP_ENDPOINT set — tracing disabled")

    # --------------------------------------------------------------------------
    # Register Routes
    # --------------------------------------------------------------------------
    app.add_route("/metrics", metrics_endpoint)
    
    # GraphQL
    graphql_app = GraphQLRouter(graphql_schema)
    app.include_router(graphql_app, prefix="/graphql")
    from routes import events, query, websockets, health, system, analytics, echo, prism, instinct, deduction, what_if, slice, subwave, recovery, paradox

    app.include_router(health.router)
    app.include_router(events.router)
    app.include_router(recovery.router)
    app.include_router(paradox.router)
    app.include_router(query.router)
    app.include_router(websockets.router)
    app.include_router(system.router)
    app.include_router(analytics.router)
    app.include_router(echo.router)
    app.include_router(prism.router)
    app.include_router(instinct.router)
    app.include_router(deduction.router)
    app.include_router(what_if.router)
    app.include_router(slice.router)
    app.include_router(subwave.router)
    app.include_router(lens_router)
    app.include_router(contact_router)
    
    # Interfaces — MCP SSE (Hermes, Cursor, etc.)
    # Mount at /mcp for simpler path (avoids urljoin issues with nested paths)
    app.mount("/mcp", create_mcp_app())
    app.mount("/api/v2/mcp", create_mcp_app())  # Legacy path
    app.include_router(raft_router)
    app.include_router(loadbalancer_router)

    # Static files (Swagger CSS etc.)
    _static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
    if os.path.isdir(_static_dir):
        app.mount("/static", StaticFiles(directory=_static_dir), name="static")

    # Web UI (WUI) — Vue dashboard at /wui/
    _wui_dist = os.path.join(os.path.dirname(__file__), "..", "wui", "dist")
    if os.path.isdir(_wui_dist):
        _wui_assets = os.path.join(_wui_dist, "assets")
        if os.path.isdir(_wui_assets):
            app.mount("/wui/assets", StaticFiles(directory=_wui_assets), name="wui_assets")

        @app.get("/wui", include_in_schema=False)
        @app.get("/wui/", include_in_schema=False)
        async def wui_index():
            return FileResponse(
                os.path.join(_wui_dist, "index.html"),
                media_type="text/html",
            )

    # Custom Swagger UI — default CDN CSS first, then our overrides on top
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui() -> HTMLResponse:
        _swagger_css = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css"
        _swagger_js  = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"
        html = f"""<!DOCTYPE html>
<html>
<head>
  <title>INDB API</title>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" type="text/css" href="{_swagger_css}">
  <link rel="stylesheet" type="text/css" href="/static/swagger-indb.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="{_swagger_js}"> </script>
  <script>
    const ui = SwaggerUIBundle({{
      url: "/openapi.json",
      dom_id: "#swagger-ui",
      presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
      layout: "BaseLayout",
      deepLinking: true,
      showExtensions: true,
      showCommonExtensions: true,
    }})
  </script>
</body>
</html>"""
        return HTMLResponse(html)

    # Root Endpoint
    @app.get("/")
    async def root():
        return {
            "name": "INDB Core Kernel",
            "version": constants.VERSION,
            "status": "operational",
            "endpoints": {
                "health": "/health",
                "api": "/api/v2/health",
                "docs": "/docs",
                "wui": "/wui/",
                "graphql": "/graphql",
                "metrics": "/metrics"
            }
        }

    # --------------------------------------------------------------------------
    # Lifecycle Handlers
    # --------------------------------------------------------------------------
    register_startup_handlers(app)

    return app
