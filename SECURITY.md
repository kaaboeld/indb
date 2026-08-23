# Security Policy

INDB makes cryptographic claims — signed responses, client-side encrypted
`blind_payload`, identity by public `key_id`, tiered verification in Grain. Claims
like these are only worth anything if they are tested, so security research on INDB
is welcome and explicitly permitted by Section 3.2 of the [LICENSE](./LICENSE).

## Reporting a vulnerability

Email **security@indb.tech**. Do not open a public issue for a vulnerability.

Please include:

- affected version (`GET /health` returns it, or see `VERSION` in `core/constants.py`)
- deployment shape: standalone, Raft cluster, Docker Compose, Fly.io
- reproduction steps or a proof of concept
- the impact you believe it has

If you want an encrypted channel, say so in a first message without details and
you will get a public key to use.

### What to expect

| Stage | Target |
|-------|--------|
| Acknowledgement of your report | 72 hours |
| Initial assessment with severity | 7 days |
| Fix or documented mitigation for critical issues | 30 days |
| Coordinated public disclosure | after a fix ships, by agreement with you |

Credit is given by default in the release notes; tell us if you prefer to stay
anonymous.

## In scope

- **Black Box Contract.** Any way to store a `blind_payload` without a non-empty
  `location`, or with a `timestamp` outside the ±5 minute server window, or any way
  to make the engine read, log, index or correlate blind content.
- **Signature handling.** Forging a server response signature, making `signed` and
  `valid` report a state that is not true, or getting a private key, seed or shared
  secret accepted by the recovery API — recovery must work on public `key_id` only.
- **Grain verification.** Producing a `verified` verdict from evidence that does not
  support it, or bypassing the tier selection logic.
- **Reputation and Fusion.** Inflating signal mass by flooding, evading the repeat
  ingest penalty, or overturning a signed axiom by volume of low-reputation events.
- **Raft cluster.** Committing an event without quorum, splitting the log, or
  forcing state divergence between nodes.
- **Interfaces.** Authentication and authorisation flaws, injection and traversal in
  the HTTP, GraphQL, WebSocket, gRPC, UDP and MCP surfaces.
- **Container and deployment defaults** shipped in this repository that are unsafe
  out of the box.

## Out of scope

- Denial of service by raw volume. Sustained cluster throughput is 19–28 events per
  second by design; saturating it is a documented property, not a vulnerability.
- Anything requiring a compromised client device. Everything INDB guarantees ends at
  the Client Trust Boundary: the server holds no client keys and cannot protect a key
  that client code leaks into logs, a crash reporter or an analytics SDK.
- Missing hardening headers with no demonstrated impact, and reports produced solely
  by an automated scanner without a working proof of concept.
- Social engineering and physical access.

## Key management notes for operators

- `indb.key` is the AES-256-GCM master key of the storage engine — 32 random bytes,
  generated on first start if absent. It is listed in `.gitignore`; never commit it,
  never bake it into an image, and back it up out of band. Losing it means losing the
  encrypted store.
- Server signing keys live in environment variables. The public key is meant to be
  published; the private key must not appear in logs, images or the docs build.
- Client signing keys never leave the client. The API rejects private keys, seeds and
  shared secrets by design, so do not attempt to send them for recovery.
- TLS termination and network exposure are the operator's responsibility — see
  `docs/TLS_SETUP.md` and `docs/RAFT_CLUSTER_DEPLOYMENT.md`.

## Supported versions

Security fixes go to the current minor release only. Older versions get a written
mitigation, not a backport.

## Supply chain

`cyclonedx-bom` is a declared dependency; an SBOM can be produced with:

```bash
cyclonedx-py requirements requirements.txt -o sbom.json
```

Third-party components and their licences are listed in
[THIRD_PARTY_NOTICES.md](./THIRD_PARTY_NOTICES.md).
