import os
import requests
import time
import json

BASE_URL = os.environ.get("INDB_API_URL", "http://localhost:8000").rstrip("/")

def run_test():
    print("--- Verifying Phase 18: Distributed Consensus (Raft) ---\n")
    
    # 1. Check Status
    print("[Test 1] Node Status")
    resp = requests.get(f"{BASE_URL}/api/v2/cluster/status")
    if resp.status_code == 200:
        status = resp.json()
        print(f"PASS: Node is {status['state']} (Term {status['term']})")
        if status['state'] != "Leader":
             print("WARN: Expected Leader (bootstrapped mode)")
    else:
        print(f"FAIL: Status check failed {resp.status_code}")

    # 2. Test RPC (RequestVote)
    print("\n[Test 2] Internal RPC (RequestVote)")
    # Simulate a candidate with higher term asking for vote
    rpc_payload = {
        "method": "request_vote",
        "params": {
            "term": 999,
            "candidate_id": "mock-candidate",
            "last_log_index": 100,
            "last_log_term": 999
        }
    }
    
    resp = requests.post(f"{BASE_URL}/api/v2/cluster/rpc", json=rpc_payload)
    if resp.status_code == 200:
        result = resp.json()
        if result["vote_granted"]:
            print("PASS: Vote granted to higher term candidate")
            
            # Check if we stepped down to follower
            st = requests.get(f"{BASE_URL}/api/v2/cluster/status").json()
            if st["state"] == "Follower" and st["term"] == 999:
                 print("PASS: Node successfully stepped down to Follower")
            else:
                 print(f"FAIL: Node did not step down: {st}")
        else:
             print(f"FAIL: Vote denied: {result}")
    else:
        print(f"FAIL: RPC failed {resp.status_code} - {resp.text}")

    # 3. Join Peer
    print("\n[Test 3] Cluster Join")
    resp = requests.post(f"{BASE_URL}/api/v2/cluster/join", params={"peer_url": "http://node-2:8004"})
    if resp.status_code == 200:
        data = resp.json()
        if "http://node-2:8004" in data["peers"]:
            print("PASS: Peer added successfully")
        else:
            print("FAIL: Peer not found in response")
    else:
        print(f"FAIL: Join failed {resp.status_code}")

if __name__ == "__main__":
    try:
        run_test()
    except Exception as e:
        print(f"FATAL: {e}")
