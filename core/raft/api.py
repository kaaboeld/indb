from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from core.raft.node import RaftNode
from core.raft.auth import require_raft_rpc_token

router = APIRouter(prefix="/raft", tags=["Raft Consensus"])

# Global Raft Node Reference (injected from main.py)
raft_node: Optional[RaftNode] = None

class VoteRequest(BaseModel):
    term: int
    candidate_id: str
    last_log_index: int = -1
    last_log_term: int = 0

class AppendRequest(BaseModel):
    term: int
    leader_id: str
    entries: List[Dict[str, Any]]
    prev_log_index: int = -1
    prev_log_term: int = 0
    leader_commit: int = 0

@router.post("/vote", dependencies=[Depends(require_raft_rpc_token)])
async def request_vote(req: VoteRequest):
    if not raft_node:
        raise HTTPException(503, "Raft Node not initialized")
    
    granted = raft_node.on_request_vote(
        req.term, 
        req.candidate_id,
        req.last_log_index,
        req.last_log_term
    )
    return {"term": raft_node.current_term, "vote_granted": granted}

@router.post("/append", dependencies=[Depends(require_raft_rpc_token)])
async def append_entries(req: AppendRequest):
    if not raft_node:
        raise HTTPException(503, "Raft Node not initialized")
        
    success = raft_node.on_append_entries(
        req.term, 
        req.leader_id, 
        req.entries,
        req.prev_log_index,
        req.prev_log_term,
        req.leader_commit
    )
    return {"term": raft_node.current_term, "success": success}

@router.get("/status")
async def raft_status():
    if not raft_node:
        return {"status": "disabled"}
    return {
        "status": "active",
        "node_id": raft_node.node_id,
        "state": raft_node.state.value,
        "term": raft_node.current_term,
        "leader": raft_node.current_leader,
        "log_size": len(raft_node.log),
        "commit_index": raft_node.commit_index,
        "peers": raft_node.peers
    }
