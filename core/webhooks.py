
import aiohttp
import asyncio
import logging
from typing import List, Dict, Any

logger = logging.getLogger("indb.webhooks")

class WebhookManager:
    """
    Manages and dispatches webhooks.
    Stores subscriptions in-memory (for now).
    """
    def __init__(self):
        self.subscribers: List[str] = []

    def register(self, url: str):
        if url not in self.subscribers:
            self.subscribers.append(url)
            logger.info(f"Webhook registered: {url}")

    def unregister(self, url: str):
        if url in self.subscribers:
            self.subscribers.remove(url)
            logger.info(f"Webhook unregistered: {url}")

    async def dispatch(self, event: Dict[str, Any]):
        """
        Dispatch event to all subscribers asynchronously.
        """
        if not self.subscribers:
            return

        payload = {
            "type": "event.created",
            "data": event
        }

        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in self.subscribers:
                tasks.append(self._send(session, url, payload))
            await asyncio.gather(*tasks)

    async def _send(self, session, url, payload):
        try:
            async with session.post(url, json=payload, timeout=5) as resp:
                if resp.status >= 400:
                    logger.warning(f"Webhook failed {url}: {resp.status}")
        except Exception as e:
            logger.error(f"Webhook error {url}: {e}")
