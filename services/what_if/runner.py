"""
What-If runner: executes base query and calls LLM for hypothetical prediction.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Any, Dict, Optional

from core.constants import (
    WHAT_IF_HERMES_TIMEOUT,
    WHAT_IF_LLM_UNAVAILABLE,
    WHAT_IF_OLLAMA_MODEL_DEFAULT,
    WHAT_IF_OLLAMA_URL_DEFAULT,
)

logger = logging.getLogger("indb.what_if")

OLLAMA_URL = os.getenv("OLLAMA_URL", WHAT_IF_OLLAMA_URL_DEFAULT)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", WHAT_IF_OLLAMA_MODEL_DEFAULT)
HERMES_TIMEOUT = int(os.getenv("WHAT_IF_HERMES_TIMEOUT", str(WHAT_IF_HERMES_TIMEOUT)))


def _call_ollama(prompt: str) -> Optional[str]:
    """Call Ollama API for completion."""
    try:
        import urllib.request
        body = json.dumps({
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=HERMES_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
            return data.get("response", "").strip()
    except Exception as e:
        logger.warning("Ollama call failed: %s", e)
        return None


def _call_hermes(prompt: str) -> Optional[str]:
    """Fallback: Hermes subprocess."""
    try:
        result = subprocess.run(
            ["hermes", "chat", "-Q", "-q", prompt],
            capture_output=True,
            text=True,
            timeout=HERMES_TIMEOUT,
        )
        if result.returncode == 0 and result.stdout:
            return result.stdout.strip()[:4000]
        return None
    except FileNotFoundError:
        logger.debug("Hermes CLI not found")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("Hermes timeout")
        return None
    except Exception as e:
        logger.warning("Hermes call failed: %s", e)
        return None


def run_what_if(base_result_summary: str, what_if: str) -> str:
    """
    Build prompt and call LLM for hypothetical prediction.
    Tries Ollama first, then Hermes subprocess.

    Works with any abstract hypothetical — romantic, counterfactual, situational.
    The task: apply the hypothetical context to the cognitive graph; describe
    how interpretation would shift. Do not change facts.
    """
    prompt = (
        "Given INDB base query result (JSON below) — a cognitive graph of events, interpretations, and links.\n\n"
        f"{base_result_summary}\n\n"
        f"Hypothetical: «{what_if}»\n\n"
        "Task: do NOT change facts. Apply this hypothetical as a contextual shift.\n"
        "How would the interpretation change? Describe the logic of changes.\n"
        "2–5 sentences. Do not invent facts — work only with what is in the result."
    )
    prediction = _call_ollama(prompt)
    if not prediction:
        prediction = _call_hermes(prompt)
    if not prediction:
        return WHAT_IF_LLM_UNAVAILABLE
    return prediction


def _summarize_for_llm(data: Any) -> str:
    """Convert base result to a short summary for the LLM prompt."""
    if isinstance(data, dict):
        # Truncate for prompt size
        s = json.dumps(data, ensure_ascii=False, default=str)[:2000]
        return s[:2000] + ("..." if len(s) > 2000 else "")
    if isinstance(data, list):
        return json.dumps(data[:10], ensure_ascii=False, default=str)[:2000]
    return str(data)[:2000]
