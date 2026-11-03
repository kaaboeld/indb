# INDB Semantic Type System

INDB 0.10.0 treats data types not just as storage formats, but as **semantic primitives**. The type system models the complexity of "Thought Processing" — where data has location, structure, and varying levels of transparency.

This system is strictly enforced in `core/types.py` and extends beyond standard JSON.

## 1. The Type Primitives

The core set of types covers the spectrum from physical grounding to abstract privacy.

| Type | Semantic Role | Python Representative | Validation Constraint |
|------|--------------|-----------------------|-----------------------|
| **`blind`** | **The Secret**. Opaque, client-encrypted data. | `str` (Base64) | `encoding="base64"` |
| **`binary`** | **The Payload**. Raw binary data (images, files, media). | `bytes` | `max_size`, `mime_type` |
| **`location`** | **The Anchor**. Spatial grounding via OSM. | `LocationField` | `lat` (-90..90), `lon` (-180..180), `osm_id` (optional) |
| **`struct`** | **The Graph**. Nested complexity. | `dict` | Recursively validated |
| **`bigint`** | **The Scale**. Nanosecond precision/crypto. | `int` | > 2^53 supported |
| **`string`** | **The Narrative**. Textual content. | `str` | `max_length`, `regex` |
| **`number`** | **The Value**. Quantifiable data. | `float`, `int` | `min`, `max` |
| **`null`** | **The Void**. Absence of data. | `None` | - |

---

## 2. Conceptual Deep Dive

### 2.1 The Anchor: `location`
In INDB, **Space is Index**. Thoughts do not exist in a vacuum; they are "grounded" in reality.
- **Concept**: A `location` field transforms a passive record into an active spatial entity. It allows the Cognitive Engine to answer: *"How relevant is this thought to where I am right now?"*
- **Optimization**: Built for **OpenStreetMap (OSM)**. Supports coordinates (`lat`/`lon`) and validated references to real-world objects via `osm_id` — Nodes, Ways, and Relations.

**Two formats are accepted:**
```json
// Simple string path (virtual namespacing)
{ "location": "books/Dostoevsky/ThePrince" }

// Full OSM object (geo-spatial anchor)
{ "location": { "lat": 55.7558, "lon": 37.6173, "osm_id": "node/1234567" } }
```

**OSM tokens** in `raw_data_anchor` use the prefix `osm:` (e.g. `osm:London, UK`) and are penalised during fusion scoring to prevent over-clustering on the same real-world location.

### 2.2 The Secret: `blind`
INDB acknowledges that some thoughts are private. The `blind` type introduces the concept of **Zero-Knowledge Storage**.
- **Concept**: A "Black Box" container. The database guarantees **Opacity**.
  - **Nobody without the key can see the data** — not even we, the database operators. The server has no decryption key; this is architectural, not policy.
  - **Server View**: Sees only a sealed box (Base64 string). It *cannot* open it, index its contents, or use it for "Cognitive Processing".
  - **What we do record**: **where** and **when** — the fact of presence is fixed. Location and timestamp are mandatory when `blind_payload` is set.

#### The Black Box Contract

> *"You may hide what is inside. You may not hide that you were here."*

When `blind_payload` is present on an event, two fields become **mandatory**:

| Field | Requirement | Reason |
|-------|-------------|--------|
| `location` | Required | Spatial accountability — the fact of presence is anchored |
| `timestamp` | Within ±5 min of server time | Replay attack prevention — old captured events are rejected |

This is enforced at the kernel level (`routes/events.py`). There is no bypass.

**Why this matters:** Zero-knowledge storage does not mean zero accountability. The content is yours alone. The fact that you were here, when, and where — belongs to the record.

  - **Client View**: Possesses the key. Sees the raw semantic content.
- **Behavior**: The JIT Renderer and Emotional Firewall inherently **skip** `blind` fields, mathematically ensuring that sensitive data never leaks into derived narratives.

#### User Story: The "Therapy Safe"
> *Alice uses an AI Agent to organize her life. She trusts the agent to schedule meetings but wants to store her therapy session notes in the same system without the AI "reading" or "analyzing" them to suggest products. She uses the `blind` type.*

#### Flow: Zero-Knowledge Lifecycle

1. **Encryption (Client Side)**
   Alice's client generates a random 32-byte key (kept locally).
   ```python
   # Client logic
   key = generate_key() # 0xAF3...
   note = "Discussed childhood anxiety."
   nonce = generate_nonce()
   ciphertext = chacha20_encrypt(note, key, nonce)
   blind_blob = base64(nonce + ciphertext)
   ```

2. **Ingest (Transport)**
   Client sends the blob. The server sees only the blob.
   `POST /api/v2/events`
   ```json
   {
       "location": "Dr. Smith's Office",
       "blind_payload": "8f3... (opaque base64) ...a92"
   }
   ```

3. **Storage (Persistence)**
   INDB stores the event.
   - `Location` is indexed (so Alice can search "Dr. Smith").
   - `blind_payload` is stored effectively as a binary blob.
   - **Crucially**: The "Cognitive Engine" scanning for "Anxiety" sees nothing in the payload. It only sees "Event at Dr. Smith's".

4. **Retrieval (Access)**
   Alice requests her history.
   `GET /api/v2/events?context=therapy`
   Server returns the encrypted blob intact.

5. **Decryption (Client Side)**
   Alice's client uses the local key to unlock the memory.
   ```python
   # Client logic
   blob = response.json().get("blind_payload")
   nonce, ciphertext = split(base64_decode(blob))
   original_note = chacha20_decrypt(ciphertext, key, nonce)
   print(original_note) # "Discussed childhood anxiety."
   ```

### 2.3 The Payload: `binary`
INDB supports raw binary data for media, files, and large payloads.
- **Concept**: The `binary` type allows storage of non-textual data (images, videos, audio, documents) alongside structured events.
  - **Server View**: Stores raw bytes efficiently using msgpack binary format.
  - **Client View**: Can upload/download binary data via gRPC streaming or HTTP multipart.
- **Use Cases**:
  - **Media Storage**: Photos, videos, audio recordings
  - **Document Attachments**: PDFs, Word docs, spreadsheets
  - **Sensor Data**: Raw binary sensor readings, telemetry
  - **Encrypted Files**: Pre-encrypted files stored as opaque blobs

#### User Story: The "Sensor Logger"
> *Bob's IoT device captures high-frequency sensor data (accelerometer, gyroscope) at 1000Hz. Instead of converting to JSON (expensive), he sends raw binary packets directly to INDB via gRPC streaming.*

#### Flow: Binary Data Lifecycle

1. **Capture (Client Side)**
   ```python
   # Client logic
   sensor_data = read_accelerometer()  # bytes: [0x3F, 0x80, ...]
   ```

2. **Ingest (gRPC Stream)**
   Client streams binary chunks via gRPC.
   ```python
   stub.IngestBinary(
       event_id="sensor_001",
       binary_payload=sensor_data,
       metadata={"sensor": "accelerometer", "frequency": 1000}
   )
   ```

3. **Storage (Autonomous)**
   INDB stores binary data in `indb.bin` using msgpack's binary type.
   - Efficient: No base64 encoding overhead
   - Searchable: Metadata is indexed, binary is opaque
   - Encrypted: AES-256-GCM protects the entire file

4. **Retrieval (Streaming)**
   Client requests binary data.
   ```python
   response = stub.GetBinary(event_id="sensor_001")
   original_data = response.binary_payload
   ```

**Key Differences: `binary` vs `blind`**
- **`binary`**: Server knows it's binary, can validate size/type, but doesn't interpret content
- **`blind`**: Server doesn't even know what's inside (client-encrypted)

### 2.4 The Graph: `struct`
Thoughts are rarely flat key-value pairs. They have depth.
- **Concept**: `struct` allows for recursive nesting, modeling complex relationships (e.g., a `Memory` containing a `Context` which contains a `Trigger`).
- **Validation**: Unlike a generic JSON object, a `struct` can have a strict internal schema, ensuring that even complex nested thoughts adhere to the system's logic.

---

## 3. Schema Definition

Schemas define the "Shape of Thought". They are constructed using `FieldSchema`.

```python
from core.types import FieldType, FieldSchema

# A complex "Secure Journal Entry" schema
journal_schema = FieldSchema(
    name="entry",
    field_type=FieldType.STRUCT,
    nested_schema={
        "timestamp": FieldSchema("ts", FieldType.BIGINT),
        "location": FieldSchema("geo", FieldType.LOCATION),
        # The content is hidden from the DB core
        "content": FieldSchema("data", FieldType.BLIND, constraints={"algo": "chacha20"}),
        "tags": FieldSchema("meta", FieldType.STRING, constraints={"max_length": 10})
    }
)
```

## 4. Type Inference

For ease of use (`ingest`), INDB includes an inference engine (`infer_type`) that guesses the semantic intent of raw data:
- Dictionary with `lat`/`lon` keys → **`FieldType.LOCATION`**
- Integer > 2^53 → **`FieldType.BIGINT`**
- Base64-like string (if configured) → **`FieldType.BLIND`** (Context dependent)
- Nested Dictionary → **`FieldType.STRUCT`**
- Raw bytes object → **`FieldType.BINARY`**

## 5. Binary Data Examples

### Image Storage
```python
# Store image with event. The anchor and the location are the two required fields;
# the bytes themselves ride along in binary_payload and are never serialised to JSON.
with open("photo.jpg", "rb") as f:
    image_data = f.read()

event = Event(
    raw_data_anchor=["sunset", "photo"],
    location="camera/roof",
    binary_payload=image_data,
)
```

### gRPC Streaming
```python
# Stream large file in chunks
def upload_file(filename):
    with open(filename, "rb") as f:
        while chunk := f.read(1024 * 1024):  # 1MB chunks
            yield IngestRequest(
                binary_payload=chunk,
                metadata={"filename": filename}
            )
```

### Over HTTP

There is no multipart upload. `POST /api/v2/events` takes JSON, and raw bytes have no field
there — binary reaches the store through gRPC, or as `blind_payload`: base64 of a payload
the client encrypted itself, which the server indexes by metadata and never reads.

```bash
curl -X POST http://localhost:8000/api/v2/events \
  -H "Content-Type: application/json" \
  -d '{
    "raw_data_anchor": ["document", "invoice"],
    "location": "archive/2026",
    "blind_payload": "'"$(base64 -i encrypted.bin | tr -d '\n')"'"
  }'
```
