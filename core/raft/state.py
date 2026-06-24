import os
import json
import logging
import msgpack
from enum import Enum
from typing import List, Dict, Any, Optional

logger = logging.getLogger("indb.raft.storage")

class RaftState(Enum):
    FOLLOWER = "Follower"
    CANDIDATE = "Candidate"
    LEADER = "Leader"

class RaftStorage:
    """
    Persistent storage for Raft state (Term, Vote, Log).
    Uses a simple file-based approach (WAL-lite).
    """
    
    def __init__(self, storage_dir: str = "."):
        self.storage_dir = storage_dir
        self.state_file = os.path.join(storage_dir, "raft_state.json")
        self.log_file = os.path.join(storage_dir, "raft.log")
        
        # In-memory cache
        self.current_term = 0
        self.voted_for = None
        self.log: List[Dict[str, Any]] = []
        
        self._load()
        
    def _load(self):
        """Load state from disk on startup."""
        # Load Term & Vote
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.current_term = data.get("current_term", 0)
                    self.voted_for = data.get("voted_for")
            except Exception as e:
                logger.warning("Failed to load Raft state from %s: %s", self.state_file, e)

        # Load Log (MessagePack for efficiency)
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "rb") as f:
                    self.log = msgpack.load(f)
            except Exception as e:
                logger.warning("Failed to load Raft log from %s: %s", self.log_file, e)
                self.log = []

    def save_state(self, term: int, voted_for: Optional[str]):
        """Persist term and vote atomically."""
        self.current_term = term
        self.voted_for = voted_for
        
        data = {"current_term": term, "voted_for": voted_for}
        tmp_file = self.state_file + ".tmp"
        with open(tmp_file, "w") as f:
            json.dump(data, f)
        os.replace(tmp_file, self.state_file) # Atomic rename

    def append_entry(self, entry: Dict[str, Any]):
        """Append a single entry to the log."""
        self.log.append(entry)
        self._flush_log()
        
    def overwrite_log(self, new_log: List[Dict[str, Any]]):
        """Overwrite the entire log (e.g., during snapshot or conflict)."""
        self.log = new_log
        self._flush_log()
        
    def _flush_log(self):
        """Flush entire log to disk."""
        # Note: Production Raft would append, not rewrite entire file.
        # This is compliant with v0.4.0 specs.
        tmp_file = self.log_file + ".tmp"
        with open(tmp_file, "wb") as f:
            msgpack.dump(self.log, f)
        os.replace(tmp_file, self.log_file)
        
    def get_last_log_index(self) -> int:
        return len(self.log) - 1 # 0-indexed internally, but Raft is 1-indexed usually? 
                                 # We'll use 0-based for list access, verify logic in Node.
                                 
    def get_last_log_term(self) -> int:
        if not self.log:
            return 0
        return self.log[-1].get("term", 0)

