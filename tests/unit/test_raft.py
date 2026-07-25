
import pytest
import asyncio
import tempfile
import shutil
import os
from unittest.mock import MagicMock, AsyncMock
from core.raft.node import RaftNode, RaftState
from core.raft.transport import RaftTransport

class TestRaftConsensus:
    """Test Raft Consensus Logic (v0.4.0)."""
    
    @pytest.fixture
    def node_env(self):
        """Setup Raft Node with temp storage."""
        temp_dir = tempfile.mkdtemp()
        transport = MagicMock(spec=RaftTransport)
        # Defaults
        transport.request_vote = AsyncMock(return_value=True)
        transport.append_entries = AsyncMock(return_value=True)
        
        kernel = MagicMock()
        kernel.db.ingest = AsyncMock(return_value=True)
        
        node = RaftNode("node1", ["http://node2", "http://node3"], storage_dir=temp_dir, transport=transport, kernel=kernel)
        
        yield node
        
        # Teardown
        shutil.rmtree(temp_dir)
        if node._loop_task:
            node._loop_task.cancel()
    
    @pytest.mark.asyncio
    async def test_initial_state(self, node_env):
        node = node_env
        assert node.state == RaftState.FOLLOWER
        assert node.current_term == 0
        assert node.voted_for is None
        assert len(node.log) == 0
        assert os.path.exists(node.storage.state_file) is False # Lazy create or init?
        
    @pytest.mark.asyncio
    async def test_leader_election_win(self, node_env):
        """Test winning an election."""
        node = node_env
        node.storage.save_state = MagicMock(wraps=node.storage.save_state)
        
        # Trigger election manually
        await node._start_election()
        
        # Verify persistence occurred
        assert node.storage.save_state.called
        assert node.current_term == 1
        assert node.state == RaftState.LEADER
        assert node.current_leader == "node1"
        
        # Verify RPCs sent
        assert node.transport.request_vote.call_count == 2
        
    @pytest.mark.asyncio
    async def test_leader_election_loss(self, node_env):
        """Test losing an election."""
        node = node_env
        node.transport.request_vote = AsyncMock(return_value=False) # Everyone votes NO
        
        await node._start_election()
        
        assert node.state == RaftState.FOLLOWER
        assert node.current_leader is None
        # Term increments even if lost
        assert node.current_term == 1 
        
    def test_on_request_vote_valid(self, node_env):
        """Test voting for a valid candidate."""
        node = node_env
        
        # Candidate term is higher
        granted = node.on_request_vote(term=1, candidate_id="node2")
        
        assert granted is True
        assert node.voted_for == "node2"
        assert node.current_term == 1
        # Check disk persistence
        assert node.storage.current_term == 1
        assert node.storage.voted_for == "node2"
        
    def test_on_request_vote_reject_unknown_candidate(self, node_env):
        node = node_env
        granted = node.on_request_vote(term=5, candidate_id="attacker")
        assert granted is False
        assert node.voted_for is None

    def test_on_append_entries_reject_unknown_leader(self, node_env):
        node = node_env
        success = node.on_append_entries(
            term=5,
            leader_id="attacker",
            entries=[],
            prev_log_index=-1,
            prev_log_term=0,
            leader_commit=0,
        )
        assert success is False
        
    def test_on_request_vote_reject_old_term(self, node_env):
        """Test rejecting vote from old term."""
        node = node_env
        node.storage.save_state(2, None) # Current term 2
        
        granted = node.on_request_vote(term=1, candidate_id="node2")
        
        assert granted is False
        
    @pytest.mark.asyncio
    async def test_replication_lifecycle(self, node_env):
        """Test full cycle: Client -> Replicate -> Log -> Commit -> Apply."""
        node = node_env
        node.state = RaftState.LEADER # Force leader
        
        # 1. Client calls replicate
        cmd = {"id": "evt1", "data": "test"}
        success = await node.replicate(cmd)
        
        assert success is True
        assert len(node.log) == 1
        entry = node.log[0]
        assert entry["command"] == cmd
        assert entry["term"] == 0 # Default term
        
        # 2. Simulate Heartbeat success -> Update Commit Index
        # Mock receiving match_index from peers
        # match_index is 0-based. So if we have 1 entry at index 0, match_index is 0.
        node.match_index = {'http://node2': 0, 'http://node3': 0} 
        node.log[0]['term'] = node.current_term # Ensure term matches for safety check
        
        node._update_commit_index()
        assert node.commit_index == 0 # Index of first entry
        
        # 3. Apply Commits
        await node._apply_commits()
        
        # 4. Verify Kernel Ingest Called
        node.kernel.db.ingest.assert_called_once()
        call_args = node.kernel.db.ingest.call_args[1]
        assert call_args['location'] == cmd.get('location') # None in this case

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
