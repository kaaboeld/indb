import httpx
import asyncio
from typing import Dict, Any, Optional

class RaftTransport:
    """Transport layer for Raft communication (HTTP implementation)."""
    
    def __init__(self, timeout: float = 0.5, max_retries: int = 2):  # Fix #3: 500ms timeout (was 10s)
        self.timeout = timeout
        self.max_retries = max_retries
        
    async def _send_rpc(self, method: str, target_url: str, endpoint: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generic RPC sender with retry logic."""
        url = f"{target_url}/raft/{endpoint}"
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    if method == "POST":
                        resp = await client.post(url, json=payload)
                    else:
                        resp = await client.get(url, params=payload)
                        
                    resp.raise_for_status()
                    return resp.json()
            except Exception as e:
                # print(f"RPC Fail {endpoint} -> {target_url} (Attempt {attempt+1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(0.05 * (attempt + 1)) # Linear backoff
        return None

    async def request_vote(self, target_url: str, term: int, candidate_id: str, last_log_index: int = -1, last_log_term: int = 0) -> bool:
        """Send RequestVote RPC."""
        payload = {
            "term": term, 
            "candidate_id": candidate_id,
            "last_log_index": last_log_index,
            "last_log_term": last_log_term
        }
        resp = await self._send_rpc("POST", target_url, "vote", payload)
        if resp:
            return resp.get("vote_granted", False)
        return False
            
    async def append_entries(self, target_url: str, term: int, leader_id: str, entries: list, prev_log_index: int = 0, prev_log_term: int = 0, leader_commit: int = 0) -> bool:
        """Send AppendEntries RPC (Heartbeat/Replication)."""
        payload = {
            "term": term, 
            "leader_id": leader_id,
            "entries": entries,
            "prev_log_index": prev_log_index,
            "prev_log_term": prev_log_term,
            "leader_commit": leader_commit
        }
        resp = await self._send_rpc("POST", target_url, "append", payload)
        if resp:
            return resp.get("success", False)
        return False
