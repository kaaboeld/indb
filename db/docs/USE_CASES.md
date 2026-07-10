# INDB: Use Cases

Five applications where INDB's architecture — signed memory, paradox-aware synthesis, zero-knowledge storage — fits naturally.

---

## 1. Legal Evidence Chain

**Problem:** Courts, arbitration, and compliance require immutable evidence. PDFs can be edited, logs altered, timestamps faked. "Who said what, when?" becomes a matter of trust.

**How INDB fits:**
- Every event is Ed25519-signed at ingestion. Tampering is mathematically detectable.
- Deduction builds evidence chains: temporal, spatial, thematic. "Event A preceded B at location X."
- Blind store for sensitive content: the system proves *presence* (something was here, at this time, at this place) without revealing *content*. Client holds the key.
- Prism surfaces competing readings — useful when opposing counsel interprets the same evidence differently.

---

## 2. Healthcare Audit & Compliance

**Problem:** Healthcare providers must prove: *who accessed what, when, and why*. HIPAA, GDPR, and audit requirements demand tamper-proof logs. Patient data must be protected — but *presence* (that a record existed at a time and place) must be provable for liability and compliance.

**How INDB fits:**
- Blind store for patient-sensitive content. Hospital encrypts; INDB stores. No key on server. No backdoor. Architecturally.
- Signed memory — every access, every query, every export is cryptographically signed. Audit trail cannot be altered.
- Echo — find similar cases (anonymized, token-level) for research without exposing raw data.
- Deduction — chain access events: "User A accessed record X, then User B accessed related record Y within 5 minutes."

---

## 3. Financial Services & Regulatory Audit

**Problem:** Banks, fintechs, and asset managers must prove transaction history, decision trails, and compliance. Regulators want: *show us exactly what happened, and prove it wasn't changed*.

**How INDB fits:**
- Immutable event log — every transaction, every decision, every alert is an event. Once written, cryptographically signed. Cannot be rewritten.
- Fusion — repetitive noise (e.g. heartbeat pings) compresses. Signal (anomalies, large transfers) stays distinct.
- Instinct — real-time anomaly detection. Adrenaline mode for alerts; analytical mode for deep review.
- Deduction — build chains: "Transfer A → Account B → Withdrawal C." Evidence synthesis for investigations.

---

## 4. Journalism & Source Verification

**Problem:** Deepfakes, manipulated media, and narrative warfare make source verification critical. Newsrooms need: *prove this was captured at this time and place, and that it hasn't been altered*.

**How INDB fits:**
- Signed ingestion — reporter uploads evidence (photo, quote, document). INDB signs at ingestion. Timestamp + location anchored. Tampering = detectable.
- Blind store — protect source identity. Store encrypted; reveal only when source authorizes. System proves *something was submitted* without revealing *what* until release.
- Prism — competing readings. When a quote is ambiguous, surface alternatives instead of forcing one interpretation.
- Echo — find related coverage, similar events, thematic resonance across the corpus.

---

## 5. IoT & Edge Intelligence

**Problem:** Sensors, vehicles, and industrial systems generate high-frequency, low-latency data. Traditional databases: too slow, too heavy. Need: ingest at <1ms, fuse noise, surface anomalies, and keep a signed record for compliance.

**How INDB fits:**
- UDP ingestion — ~0.87ms latency. Fire-and-forget for sensors.
- gRPC streaming — efficient binary upload for images, audio, large payloads.
- Fusion — repetitive sensor readings (e.g. "temperature 22°C" every second) compress. Anomalies stay distinct.
- Instinct — adrenaline mode for real-time alerts. Location match, critical tokens, owner signature.
- Signed memory — every event signed. For insurance, liability, and regulatory: *prove what the sensor saw*.
