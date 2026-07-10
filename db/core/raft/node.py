
import time
import asyncio
import logging
import random
from typing import List, Dict, Any, Optional
from core.raft.state import RaftState, RaftStorage
from core.raft.transport import RaftTransport

logger = logging.getLogger("indb.raft")

class RaftNode:
    """
    Raft Consensus Node Implementation (v0.4.0).
    Features: Persistence (WAL), Log Consistency, Commit Index.
    """
    
    def __init__(self, node_id: str, peers: List[str], storage_dir: str = ".", transport: RaftTransport = None, kernel: Any = None):
        self.node_id = node_id
        # Filter out self from peers (Fix #5)
        self.peers = [p for p in peers if node_id not in p] 
        self.transport = transport or RaftTransport()
        self.kernel = kernel # Link to State Machine (INDB)
        
        # persistent state
        self.storage = RaftStorage(storage_dir)
        
        # Volatile state
        self.state = RaftState.FOLLOWER
        self.current_leader = None
        self.last_heartbeat = time.time()
        
        self.commit_index = -1 # Highest log entry known to be committed
        self.last_applied = -1 # Highest log entry applied to state machine
        
        # Leader Volatile State
        self.next_index = {} # For each peer, index of next log entry to send
        self.match_index = {} # For each peer, index of highest log entry known to be replicated
        
        # Election settings (Fix #1: Proper Raft timing)
        self.election_timeout_range = (5.0, 10.0)  # 5-10s for Docker network (was 60-90s)
        self.election_deadline = time.time() + self._get_random_timeout()
        
        self._running = False
        self._loop_task = None
        
    @property
    def current_term(self):
        return self.storage.current_term
        
    @property
    def voted_for(self):
        return self.storage.voted_for
        
    @property
    def log(self):
        return self.storage.log

    def _get_random_timeout(self) -> float:
        return random.uniform(*self.election_timeout_range)
        
    def start(self):
        """Start background consensus loop."""
        self._running = True
        self._loop_task = asyncio.create_task(self._run_loop())
        logger.info("Raft node %s started (term=%d)", self.node_id, self.current_term)
        
    async def stop(self):
        """Stop consensus loop."""
        self._running = False
        if self._loop_task:
            await self._loop_task
            
    async def _run_loop(self):
        """Main event loop."""
        while self._running:
            now = time.time()
            
            if self.state == RaftState.FOLLOWER:
                if now > self.election_deadline:
                    logger.info("Raft: election timeout on node=%s — starting election", self.node_id)
                    await self._start_election()
                    
            elif self.state == RaftState.LEADER:
                # Send Heartbeats (Fix #1: 100ms = election_timeout/50)
                if now - self.last_heartbeat > 0.1:
                    await self._send_heartbeats()
                    self.last_heartbeat = time.time()
                    
            # Apply committed entries
            await self._apply_commits()
            
            await asyncio.sleep(0.1)

    async def _start_election(self):
        """Transition to Candidate and request votes."""
        self.state = RaftState.CANDIDATE
        new_term = self.current_term + 1
        self.storage.save_state(new_term, self.node_id) # Vote for self & Persist
        
        votes = 1 
        self.election_deadline = time.time() + self._get_random_timeout()
        
        logger.info("Raft: starting election for term %d on node=%s", self.current_term, self.node_id)

        # Single-node cluster: immediately become leader
        if len(self.peers) == 0:
            logger.info("Raft: single-node cluster — becoming leader immediately")
            self._become_leader()
            return

        for peer in self.peers:
            granted = await self.transport.request_vote(
                peer,
                self.current_term,
                self.node_id,
                self.storage.get_last_log_index(),
                self.storage.get_last_log_term()
            )
            if granted:
                votes += 1

        total_nodes = len(self.peers) + 1
        quorum = (total_nodes // 2) + 1

        if votes >= quorum:
            logger.info(
                "Raft: won election — %d/%d votes (quorum=%d) on node=%s — becoming leader",
                votes, total_nodes, quorum, self.node_id,
            )
            self._become_leader()
        else:
            logger.warning(
                "Raft: lost election — %d/%d votes (needed %d) on node=%s — reverting to follower",
                votes, total_nodes, quorum, self.node_id,
            )
            self.state = RaftState.FOLLOWER


    def _become_leader(self):
        self.state = RaftState.LEADER
        self.current_leader = self.node_id

        # Append a no-op entry in the current term (Figure 8 fix).
        # Without this, commit_index stays at -1 after restart because all
        # existing log entries have old terms and fail the safety check:
        #   log[N].term == currentTerm
        # The no-op forces the check to pass, unblocking all commits.
        noop_entry = {"type": "noop", "term": self.current_term, "command": None}
        self.storage.append_entry(noop_entry)
        logger.info(
            "Raft: node=%s became leader at term=%d — no-op appended to unblock commit",
            self.node_id, self.current_term,
        )

        # Reinitialize leader state
        last_log_idx = self.storage.get_last_log_index()
        for peer in self.peers:
            self.next_index[peer] = last_log_idx + 1
            self.match_index[peer] = -1
            
        asyncio.create_task(self._send_heartbeats())

    async def _send_heartbeats(self):
        """Send logs to peers based on next_index."""
        for peer in self.peers:
            prev_log_index = self.next_index.get(peer, 0) - 1
            prev_log_term = 0
            
            if prev_log_index >= 0 and prev_log_index < len(self.log):
                prev_log_term = self.log[prev_log_index].get("term", 0)
                
            entries = self.log[self.next_index.get(peer, 0):]
            
            success = await self.transport.append_entries(
                peer, 
                self.current_term, 
                self.node_id, 
                entries,
                prev_log_index,
                prev_log_term,
                self.commit_index
            )
            
            if success:
                if entries:
                    # Update match index
                    self.match_index[peer] = prev_log_index + len(entries)
                    self.next_index[peer] = self.match_index[peer] + 1
                    # Check if we can commit
                    self._update_commit_index()
            else:
                # Failed (latency or inconsistency)
                # Simple optimization: decrement next_index
                if self.next_index.get(peer, 0) > 0:
                   self.next_index[peer] -= 1

    def _update_commit_index(self):
        """If a majority matches N, and log[N].term == currentTerm, set commitIndex = N."""
        # Single-node cluster: commit everything immediately
        if len(self.peers) == 0:
            last_log_idx = self.storage.get_last_log_index()
            if last_log_idx > self.commit_index:
                self.commit_index = last_log_idx
                logger.debug(
                    "Raft (single-node): commit index advanced to %d", self.commit_index
                )
            return
        
        # Multi-node cluster: find match indexes
        indexes = sorted(list(self.match_index.values()) + [self.storage.get_last_log_index()])
        majority_idx = indexes[len(indexes) // 2]  # Medianish (simplified)
        
        if majority_idx > self.commit_index:
            # Check term safety rule (Figure 8)
            if majority_idx < len(self.log) and self.log[majority_idx]['term'] == self.current_term:
                self.commit_index = majority_idx
                # print(f"Raft: Commit Index Advanced to {self.commit_index}")

    async def _apply_commits(self):
        """Apply committed entries to State Machine (INDB Kernel)."""
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            if self.last_applied >= len(self.log):
                break
                
            entry = self.log[self.last_applied]
            command = entry.get('command')

            # Skip no-op entries — they exist only to advance commit_index (Figure 8 fix)
            if entry.get('type') == 'noop':
                logger.debug(
                    "Raft: applied no-op at index=%d (term=%s)",
                    self.last_applied, entry.get('term'),
                )
                continue

            if self.kernel and command:
                 try:
                     db = self.kernel.db
                     result = db.apply_event(command)
                 except Exception as e:
                     logger.error(
                         "Raft: failed to apply log entry at index=%d: %s",
                         self.last_applied, e, exc_info=True,
                     )

    async def replicate(self, command: Dict[str, Any]) -> bool:
        """Client API: Replicate a new command/event."""
        if self.state != RaftState.LEADER:
            return False
            
        # Wrap in Log Entry structure
        entry = {
            "term": self.current_term,
            "command": command,
            "timestamp": time.time()
        }
        
        self.storage.append_entry(entry)
        
        # Update commit index (especially important for single-node)
        self._update_commit_index()
        
        # Wait for commit (Simplified: busy wait or event)

        # In prod, we'd use a Future.
        # For now, we return True assuming eventual consistency or wait briefly
        return True
        
    # --- RPC Handlers ---
    
    def on_request_vote(self, term: int, candidate_id: str, last_log_index: int = -1, last_log_term: int = 0) -> bool:
        """Handle RequestVote RPC."""
        # 1. Update Term
        if term > self.current_term:
            self.storage.save_state(term, None)
            self.state = RaftState.FOLLOWER
            
        # 2. Reject if term < currentTerm
        if term < self.current_term:
            return False
            
        # 3. Log Currency Check (Fix #4: Raft §5.4.1)
        my_last_index = self.storage.get_last_log_index()
        my_last_term = self.storage.get_last_log_term()
        
        # Candidate's log must be at least as up-to-date as ours
        log_ok = (last_log_term > my_last_term) or \
                 (last_log_term == my_last_term and last_log_index >= my_last_index)
        
        if not log_ok:
            return False  # Candidate's log is stale
            
        # 4. Grant Vote if null or already voted for candidate
        if (self.storage.voted_for is None or self.storage.voted_for == candidate_id):
            self.storage.save_state(self.current_term, candidate_id)
            self.election_deadline = time.time() + self._get_random_timeout()
            return True
            
        return False
        
    def on_append_entries(self, term: int, leader_id: str, entries: List, prev_log_index: int, prev_log_term: int, leader_commit: int) -> bool:
        """Handle AppendEntries RPC."""
        if term > self.current_term:
            self.storage.save_state(term, None)
            self.state = RaftState.FOLLOWER
            
        if term < self.current_term:
            return False
            
        self.state = RaftState.FOLLOWER
        self.current_leader = leader_id
        self.election_deadline = time.time() + self._get_random_timeout()
        
        # Consistency Check
        if prev_log_index > -1:
             if prev_log_index >= len(self.log):
                 return False # Log mismatch (missing entries)
             if self.log[prev_log_index].get('term') != prev_log_term and prev_log_term != 0: 
                 # Term mismatch -> Conflict
                 # Delete conflicting entries
                 self.storage.overwrite_log(self.log[:prev_log_index])
                 return False

        # Append New Entries
        if entries:
            # Idempotency check?
            # Simplified: just extend
            for e in entries:
                self.storage.append_entry(e)
            
        # Update Commit Index
        if leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, self.storage.get_last_log_index())
            
        return True
