# Cognitive Firewall (v0.10.0)

The **Cognitive Firewall** is an active defense layer that filters, redacts, or blocks events based on the current Context. Unlike a standard network firewall which filters by IP/Port, the Cognitive Firewall filters by **Meaning** and **State**.

## 1. Core Concepts

*   **Rule-Based**: Rules are defined as `Condition -> Action`.
*   **Context-Aware**: Rules matches against both the Event properties (e.g., `tag`, `location`) AND the System Context (e.g. `mood`, `security_level`).
*   **Actions**:
    *   `BLOCK`: Event is hidden completely.
    *   `REDACT`: Event is visible, but sensitive fields (like tokens or narrative) are masked.
    *   `WARN`: Event is flagged as potentially harmful/irrelevant.
    *   `ALLOW`: Explicit pass.

## 2. Rule Structure (JSON)

Firewall profiles are stored as JSON files.

```json
[
  {
    "name": "Block Debug in Production",
    "condition": {
      "context.status": "Production",
      "event.tag": "DEBUG"
    },
    "action": "block",
    "priority": 100
  },
  {
    "name": "Redact PII in Public",
    "condition": {
      "context.security_level": "Public",
      "event.raw_data_anchor": "regex:(email|phone)"
    },
    "action": "redact",
    "redaction_fields": ["raw_data_anchor", "narrative"],
    "priority": 90
  }
]
```

## 3. CLI Usage

You can manage firewall profiles using the `indb-cli`.

### Generate a Profile
Create a new firewall rules file from a template.

```bash
# Generate a strict profile for production
python3 -m cli.indb_cli firewall generate --name=production --template=strict
```

This creates `firewall_production.json`.

### Test a Profile
Simulate how a firewall behaves under specific contexts.

```bash
# Test if 'DEBUG' events are blocked when mood is 'Production'
python3 -m cli.indb_cli firewall test \
  --file=firewall_production.json \
  --context='{"status": "Production"}'
```

## 4. Examples

### Scenario: Therapy Session
**Goal**: Allow processing of traumatic memories that are usually blocked.

1.  **Context**: `{"mode": "Therapy"}`
2.  **Rule**:
    ```json
    {
      "name": "Allow Trauma",
      "condition": {"context.mode": "Therapy"},
      "action": "allow",
      "priority": 1000
    }
    ```

### Scenario: Public Demo
**Goal**: Hide all personal identifiers and internal system logs.

1.  **Context**: `{"security_level": "Public"}`
2.  **Rule**:
    ```json
    {
      "name": "Public Safety",
      "condition": {"context.security_level": "Public", "event.tag": "PRIVATE"},
      "action": "block"
    }
    ```
