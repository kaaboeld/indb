# Reddit — r/selfhosted

**Submit:** https://www.reddit.com/r/selfhosted/submit

**Flair:** `Software` or `Show and Tell`

---

## Title

```
INDB – self-hosted interpretational engine: signed memory, blind storage, Grain identity verification
```

---

## Post body

```
We built INDB as an alternative to "just another database." Self-host friendly (Docker Compose, Fly). Designed for when you need:

- **Signed memory** — events optionally Ed25519-signed; recovery by public key_id (private key never on server)
- **Blind store** — zero-knowledge blind_payload: you encrypt, we store. No key on server. Architecturally.
- **Grain** — identity verification across noise: from strict signatures to Echo×reputation to statistical fingerprint (like SynthID concept, in-kernel)
- **Paradox-aware** — Prism surfaces contradictions instead of hiding them
- **Cognitive layer** — Echo, Instinct, Deduction, Fusion compression

Modeled after human memory: inhale, exhale, axiom. Multi-protocol (HTTP, UDP, gRPC, WebSocket). WUI at /wui/.

Use cases: audit trails, compliance, journalism, IoT, anywhere you need prove-it-happened without exposing content.

Live demo: https://indb.tech
API: https://api.indb.tech/docs
Full docs: https://docs.indb.tech
Grain: https://docs.indb.tech/GRAIN/

Would love feedback from anyone running their own infra — especially self-hosters who care about signed exports and blind zones.
```

---

## Comment if asked «open source?»

```
Core is proprietary; API and docs are public. You can self-host the binary via Docker. Happy to share architecture details — the blind contract and Grain tiers are documented openly because they're structural guarantees, not secret sauce.
```
