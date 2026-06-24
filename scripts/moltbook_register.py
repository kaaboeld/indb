#!/usr/bin/env python3
"""
moltbook_register.py — Register INDB as an agent on Moltbook.

Run once to get your API key:
    python scripts/moltbook_register.py

What it does:
  1. Sends a registration request to Moltbook
  2. Prints the claim link (you verify via tweet/X)
  3. Polls until the claim is confirmed
  4. Saves MOLTBOOK_API_KEY to your .env file

After this, restart the server — the connector activates automatically.
"""
import os
import sys
import time
from pathlib import Path

import httpx

BASE = "https://www.moltbook.com/api/v1"
ENV_FILE = Path(__file__).parent.parent / ".env"


def save_api_key(api_key: str) -> None:
    """Append or update MOLTBOOK_API_KEY in the .env file."""
    lines = []
    found = False

    if ENV_FILE.exists():
        lines = ENV_FILE.read_text().splitlines()
        for i, line in enumerate(lines):
            if line.startswith("MOLTBOOK_API_KEY="):
                lines[i] = f"MOLTBOOK_API_KEY={api_key}"
                found = True
                break

    if not found:
        lines.append(f"MOLTBOOK_API_KEY={api_key}")

    ENV_FILE.write_text("\n".join(lines) + "\n")
    print(f"\n✅  API key saved to {ENV_FILE}")


def register() -> None:
    print("=" * 60)
    print("INDB → Moltbook Agent Registration")
    print("=" * 60)

    agent_name = input("Agent name for Moltbook (e.g. 'indb-assistant'): ").strip()
    if not agent_name:
        print("Agent name is required.")
        sys.exit(1)

    description = input("Short description (optional): ").strip()

    print(f"\n📡  Registering '{agent_name}' on Moltbook...")

    with httpx.Client(timeout=15.0) as client:
        # Step 1: Register
        resp = client.post(
            f"{BASE}/agents/register",
            json={"name": agent_name, "description": description or "INDB — Intelligent Network Database"},
        )

        if resp.status_code not in (200, 201):
            print(f"❌  Registration failed: HTTP {resp.status_code}")
            print(resp.text[:400])
            sys.exit(1)

        data = resp.json()
        api_key = data.get("api_key") or data.get("data", {}).get("api_key", "")
        claim_url = data.get("claim_url") or data.get("data", {}).get("claim_url", "")

        if not api_key:
            print("❌  No API key in response. Check Moltbook docs for updated registration flow.")
            print(resp.text[:600])
            sys.exit(1)

        print(f"\n🔑  API key received: {api_key[:8]}...")
        if claim_url:
            print(f"\n🔗  Claim link:\n    {claim_url}")
            print("\n⬆️  Tweet/post this link to verify ownership, then continue.\n")
            input("Press Enter after you've verified...")

        # Step 2: Poll until claimed
        print("\n⏳  Waiting for claim confirmation...")
        for attempt in range(30):
            time.sleep(5)
            status_resp = client.get(
                f"{BASE}/agents/status",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if status_resp.status_code == 200:
                status = status_resp.json().get("status", "")
                if status == "claimed":
                    print("✅  Agent claimed!")
                    break
                print(f"   [{attempt+1}/30] Status: {status} — still waiting...")
            else:
                print(f"   [{attempt+1}/30] Status check HTTP {status_resp.status_code}")
        else:
            print("⚠️  Timed out waiting for claim. Key is still valid — just run the server when claimed.")

    save_api_key(api_key)

    print("\n" + "=" * 60)
    print("Done! Restart the INDB server to activate the Moltbook connector.")
    print("=" * 60)


if __name__ == "__main__":
    register()
