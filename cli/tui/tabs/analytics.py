"""Analytics tab — fusion, insights, tokens, performance."""

from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from cli.tui.helpers import pretty_json, top_items
from cli.tui.widgets import OutputLog, StatsBar


class AnalyticsTab(Widget):
    DEFAULT_CSS = """
    AnalyticsTab {
        layout: vertical;
        height: 100%;
    }
    AnalyticsTab #analytics-stats {
        margin-bottom: 1;
    }
    AnalyticsTab #analytics-insights {
        height: auto;
        max-height: 6;
        margin-bottom: 1;
        padding: 0 1;
        border: solid $surface-lighten-1;
    }
    AnalyticsTab #analytics-detail {
        height: 1fr;
        min-height: 10;
    }
    """

    def compose(self) -> ComposeResult:
        yield StatsBar(
            "Health",
            "Locations",
            "Tokens",
            "Fusion Rate",
            "WS Clients",
            id="analytics-stats",
        )
        yield Static("Insights loading…", id="analytics-insights")
        yield OutputLog(id="analytics-detail", highlight=True)

    async def load_data(self) -> None:
        api = self.app.api
        overview, fusion, insights, ws = await asyncio.gather(
            asyncio.to_thread(api.analytics_overview),
            asyncio.to_thread(api.fusion_stats),
            asyncio.to_thread(api.analytics_insights),
            asyncio.to_thread(api.websocket_stats),
        )
        self._update(overview, fusion, insights, ws)

    def _update(
        self,
        overview: dict,
        fusion: dict,
        insights: list,
        ws: dict,
    ) -> None:
        db = overview.get("database", {})
        tokens = overview.get("tokens", {})
        fusion_overview = overview.get("fusion", {})
        health = overview.get("health_score", "—")

        fusion_rate = fusion_overview.get("fusion_rate", "—")
        if isinstance(fusion, dict):
            metrics = fusion.get("metrics", {})
            if metrics.get("fusion_rate") is not None:
                fusion_rate = metrics["fusion_rate"]

        self.query_one("#analytics-stats", StatsBar).set_values(
            str(health),
            str(db.get("unique_locations", "—")),
            str(tokens.get("unique_tokens", tokens.get("total_tokens", "—"))),
            f"{fusion_rate}%",
            str(ws.get("active_connections", ws.get("connections", "—"))),
        )

        insight_box = self.query_one("#analytics-insights", Static)
        if insights:
            insight_box.update("\n".join(f"• {i}" for i in insights[:4]))
        elif not overview:
            insight_box.update(f"⚠ No analytics ({self.app.api.last_error or 'unknown'})")
        else:
            insight_box.update("No insights yet")

        detail = self.query_one("#analytics-detail", OutputLog)
        detail.clear()
        sections = {
            "Database": db,
            "Fusion Overview": fusion_overview,
            "Fusion Stats": fusion,
            "Temporal": overview.get("temporal", {}),
            "Performance": overview.get("performance", {}),
            "Cognitive": overview.get("cognitive", {}),
            "WebSocket": ws,
        }
        for title, data in sections.items():
            if data:
                detail.write(f"══ {title} ══")
                if isinstance(data, dict) and any(
                    isinstance(v, dict) for v in data.values()
                ):
                    detail.write(pretty_json(data, limit=2000))
                elif isinstance(data, dict):
                    flat = {
                        k: v for k, v in data.items() if not isinstance(v, (dict, list))
                    }
                    for line in top_items(flat, 12):
                        detail.write(line)
                    for key, val in data.items():
                        if isinstance(val, dict):
                            detail.write(f"  [{key}]")
                            for sub in top_items(val, 6):
                                detail.write(sub)
                else:
                    detail.write(pretty_json(data, limit=2000))
