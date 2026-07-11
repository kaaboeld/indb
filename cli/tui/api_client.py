"""HTTP client for INDB API endpoints used by the TUI."""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

import httpx

logger = logging.getLogger("indb.tui.api")

T = TypeVar("T")


class ApiClient:
    """Thread-safe synchronous API client."""

    def __init__(self, base_url: str, timeout: float = 8.0) -> None:
        self._lock = threading.RLock()
        self._timeout = timeout
        self.last_error: Optional[str] = None
        self.base_url = base_url.rstrip("/")
        self._client = self._new_client(self.base_url)

    def _new_client(self, base_url: str) -> httpx.Client:
        return httpx.Client(
            base_url=base_url.rstrip("/"),
            timeout=self._timeout,
            follow_redirects=True,
        )

    def reconfigure(self, base_url: str) -> None:
        with self._lock:
            self.base_url = base_url.rstrip("/")
            try:
                self._client.close()
            except Exception:
                pass
            self._client = self._new_client(self.base_url)
            self.last_error = None

    def close(self) -> None:
        with self._lock:
            try:
                self._client.close()
            except Exception:
                pass

    def _call(self, fn: Callable[[], T], fallback: T) -> T:
        try:
            with self._lock:
                result = fn()
            self.last_error = None
            return result
        except Exception as exc:
            self.last_error = str(exc)
            logger.debug("API call failed: %s", exc)
            return fallback

    def _unwrap(self, response: httpx.Response) -> Any:
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and "data" in payload:
            return payload.get("data")
        return payload

    def health(self) -> Dict[str, Any]:
        def _do() -> Dict[str, Any]:
            r = self._client.get("/health")
            r.raise_for_status()
            return r.json()

        return self._call(_do, {"status": "error", "error": self.last_error or "unreachable"})

    def health_v2(self) -> Dict[str, Any]:
        def _do() -> Dict[str, Any]:
            data = self._unwrap(self._client.get("/api/v2/health"))
            return data if isinstance(data, dict) else {}

        return self._call(_do, {"status": "error", "error": self.last_error or "unreachable"})

    def analytics_overview(self) -> Dict[str, Any]:
        def _do() -> Dict[str, Any]:
            data = self._unwrap(self._client.get("/api/v2/analytics/overview"))
            return data if isinstance(data, dict) else {}

        return self._call(_do, {})

    def analytics_insights(self) -> List[str]:
        def _do() -> List[str]:
            data = self._unwrap(self._client.get("/api/v2/analytics/insights"))
            return data if isinstance(data, list) else []

        return self._call(_do, [])

    def fusion_stats(self) -> Dict[str, Any]:
        def _do() -> Dict[str, Any]:
            data = self._unwrap(self._client.get("/api/v2/fusion/stats"))
            return data if isinstance(data, dict) else {}

        return self._call(_do, {})

    def events(self, limit: int = 50, **params: Any) -> List[Dict[str, Any]]:
        def _do() -> List[Dict[str, Any]]:
            data = self._unwrap(
                self._client.get("/api/v2/events", params={"limit": limit, **params})
            )
            return data if isinstance(data, list) else []

        return self._call(_do, [])

    def events_by_location(self, location: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self.events(
            limit=limit,
            filter_key="location",
            filter_value=location,
        )

    def events_mixed(
        self,
        per_source: int = 10,
        max_total: int = 50,
    ) -> List[Dict[str, Any]]:
        """Sample recent events from each top location (not only the newest batch)."""
        batch_size = max(3, per_source)

        def _do() -> List[Dict[str, Any]]:
            overview = self._unwrap(self._client.get("/api/v2/analytics/overview"))
            top_locations = (
                overview.get("database", {}).get("top_locations", {})
                if isinstance(overview, dict)
                else {}
            )
            if not top_locations:
                data = self._unwrap(
                    self._client.get("/api/v2/events", params={"limit": max_total})
                )
                return data if isinstance(data, list) else []

            merged: List[Dict[str, Any]] = []
            for location in top_locations:
                batch = self._unwrap(
                    self._client.get(
                        "/api/v2/events",
                        params={
                            "limit": batch_size,
                            "filter_key": "location",
                            "filter_value": location,
                        },
                    )
                )
                if isinstance(batch, list):
                    merged.extend(batch)

            merged.sort(key=lambda e: float(e.get("timestamp", 0)), reverse=True)
            return merged[:max_total]

        return self._call(_do, [])

    def search(self, q: str, limit: int = 20) -> List[Dict[str, Any]]:
        def _do() -> List[Dict[str, Any]]:
            data = self._unwrap(
                self._client.get("/api/v2/search", params={"q": q, "limit": limit})
            )
            return data if isinstance(data, list) else []

        return self._call(_do, [])

    def modules(self) -> List[Dict[str, Any]]:
        def _do() -> List[Dict[str, Any]]:
            r = self._client.get("/api/v2/modules")
            r.raise_for_status()
            payload = r.json()
            data = payload.get("data", payload)
            return data if isinstance(data, list) else []

        return self._call(_do, [])

    def protocols(self) -> Dict[str, Any]:
        def _do() -> Dict[str, Any]:
            r = self._client.get("/api/v2/system/protocols")
            r.raise_for_status()
            return r.json()

        return self._call(_do, {})

    def websocket_stats(self) -> Dict[str, Any]:
        def _do() -> Dict[str, Any]:
            data = self._unwrap(self._client.get("/api/v2/websocket/stats"))
            return data if isinstance(data, dict) else {}

        return self._call(_do, {})

    def raft_status(self) -> Dict[str, Any]:
        def _do() -> Dict[str, Any]:
            r = self._client.get("/raft/status")
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, dict) else {}

        return self._call(_do, {})

    def node_status(self, node_url: str) -> Tuple[bool, Dict[str, Any], Optional[str]]:
        try:
            with httpx.Client(base_url=node_url.rstrip("/"), timeout=8.0) as client:
                health = client.get("/health")
                health_ok = health.status_code == 200
                health_data = health.json() if health_ok else {}
                raft_data: Dict[str, Any] = {}
                try:
                    raft = client.get("/raft/status")
                    if raft.status_code == 200:
                        raft_data = raft.json()
                except Exception:
                    pass
                return health_ok, {**health_data, "raft": raft_data}, None
        except Exception as exc:
            return False, {}, str(exc)

    def interpret(
        self,
        *,
        mood: str,
        location: str,
        goal: str = "",
        limit: int = 10,
    ) -> Any:
        body: Dict[str, Any] = {
            "context": {"mood": mood, "location": location},
            "limit": limit,
        }
        if goal:
            body["context"]["goal"] = goal
        return self._call(
            lambda: self._unwrap(self._client.post("/api/v2/interpret", json=body)),
            {"error": self.last_error},
        )

    def prism_synthesize(self, query: str, limit: int = 10) -> Any:
        return self._call(
            lambda: self._unwrap(
                self._client.post(
                    "/api/v2/prism/synthesize",
                    json={"query": query, "limit": limit},
                )
            ),
            {"error": self.last_error},
        )

    def prism_instinct(self, query: str, adrenaline: float = 0.5) -> Any:
        return self._call(
            lambda: self._unwrap(
                self._client.post(
                    "/api/v2/prism/instinct",
                    json={"query": query, "adrenaline": adrenaline, "limit": 10},
                )
            ),
            {"error": self.last_error},
        )

    def lens_query(
        self,
        *,
        context_a: str,
        context_b: str,
        ratio: Optional[List[float]] = None,
        limit: int = 20,
    ) -> Any:
        return self._call(
            lambda: self._unwrap(
                self._client.post(
                    "/api/v2/lens/query",
                    json={
                        "context_a": context_a,
                        "context_b": context_b,
                        "ratio": ratio or [0.5, 0.5],
                        "limit": limit,
                    },
                )
            ),
            {"error": self.last_error},
        )

    def echo_resonate(self, seed_id: str, radius: float = 0.3) -> Any:
        return self._call(
            lambda: self._unwrap(
                self._client.post(
                    "/api/v2/echo/resonate",
                    json={"seed_id": seed_id, "radius": radius, "limit": 20},
                )
            ),
            {"error": self.last_error},
        )

    def deduce(self, query: str) -> Any:
        return self._call(
            lambda: self._unwrap(
                self._client.post(
                    "/api/v2/deduction/deduce",
                    json={"query": query, "limit": 15},
                )
            ),
            {"error": self.last_error},
        )

    def what_if(self, base_query: str, modifier: str, mode: str = "core") -> Any:
        return self._call(
            lambda: self._unwrap(
                self._client.post(
                    "/api/v2/what-if",
                    json={
                        "base_query_type": "search",
                        "base_params": {"q": base_query},
                        "what_if": modifier,
                        "mode": mode,
                    },
                )
            ),
            {"error": self.last_error},
        )

    def slice(self, query: str, what_if: str) -> Any:
        return self._call(
            lambda: self._unwrap(
                self._client.post(
                    "/api/v2/slice",
                    json={"query": query, "what_if": what_if, "limit": 20},
                )
            ),
            {"error": self.last_error},
        )

    def paradox_create(
        self,
        sources: List[str],
        generation_mode: str = "resonance_weighted",
        collapse_mode: str = "sample_once",
    ) -> Any:
        return self._call(
            lambda: self._unwrap(
                self._client.post(
                    "/api/v2/paradox",
                    json={
                        "sources": sources,
                        "generation_mode": generation_mode,
                        "collapse_mode": collapse_mode,
                    },
                )
            ),
            {"error": self.last_error},
        )

    def paradox_get(self, paradox_id: str, collapse: bool = True) -> Any:
        return self._call(
            lambda: self._unwrap(
                self._client.get(
                    f"/api/v2/paradox/{paradox_id}",
                    params={"collapse": str(collapse).lower()},
                )
            ),
            {"error": self.last_error},
        )

    def recovery_identity(self, key_id: str) -> Any:
        return self._call(
            lambda: self._unwrap(self._client.get(f"/api/v2/recovery/identity/{key_id}")),
            {"error": self.last_error},
        )
