# Architecture

## System Components

| Component | Responsibility |
|-----------|----------------|
| **Kernel** | Central orchestrator, manages lifecycle. Pure Python, dependency-free. |
| **Memory Manager** | Manages `MemoryStream`, handles Entropy Pruning (archiving low-mass events). |
| **Fusion Engine** | Background thread pool for similarity search using DBSCAN and Semantic Embeddings. |
| **JIT Renderer** | Decoupled Interpretation Service. Derives meaning from events at runtime. |
| **Source Registry** | **[NEW]** Epistemological Authority. Verification of event origin, type (Sensor/AI), and reputation. |
| **Services** | Pluggable logic modules (ML, Analytics, Cognitive Firewall). |
| **Source modules** | Hermes, Moltbook, etc. — pluggable. System works when any module is enabled or disabled. |
| **Protocols** | Interfaces for outside world: HTTP (8003), UDP (8004), gRPC (50051), GraphQL, WebSocket. |

## Data Flow

1.  **Ingest**: Data enters via HTTP/UDP/gRPC.
2.  **Origin Check**: **[NEW]** Source Registry validates `source_id` and checks Reputation/Signature.
3.  **Fusion Check**: Fusion Engine checks for similar events in the buffer (Weighted by Source Reputation).
4.  **Persistence**: Event is appended to `MemoryStream` (RAM) and `indb.bin` (Disk, Encrypted).
4.  **Replication**: 
    - Leader writes to `raft.log`.
    - Parallel RPCs sents to Followers.
    - Upon Quorum, entry is Committed.
5.  **Retrieval**: `interpret()` request arrives at HTTP Protocol.
6.  **Firewall**: `CognitiveFirewall` inspects event against Context rules.
7.  **JIT Render**: `JITRenderer` Service scores/mutates events based on Context (Decoupled from Storage).
8.  **Response**: Signed and compressed response is returned to Agent.

## Storage Format
- **Memory**: Python Objects (`Event` class).
- **Disk**: 
    - `indb.bin`: Custom binary format (Encrypted BSON chunks).
    - `raft.log`: Write-Ahead Log (WAL) for Consensus State (MessagePack).
        - Header: Magic Bytes + Version
        - Payload: ChaCha20-Poly1305 Encrypted BSON chunks (indb.bin only)
