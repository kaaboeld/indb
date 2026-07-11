"""Async subprocess runner for operational scripts."""

from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional


LogCallback = Callable[[str], None]


@dataclass(frozen=True)
class ScriptSpec:
    label: str
    emoji: str
    command: List[str]
    cwd: Optional[Path] = None


def default_scripts(project_root: Path) -> List[ScriptSpec]:
    """Production-safe scripts — read-only against the configured API."""
    py = sys.executable
    root = project_root
    return [
        ScriptSpec("Integrity Check", "🩺", [py, "tests/integrity_check.py"], root),
        ScriptSpec("Explore DB", "🔍", [py, "scripts/explore_db.py"], root),
        ScriptSpec("Audit Protocols", "🛡️", [py, "scripts/audit_protocols.py"], root),
        ScriptSpec("Analyze Sources", "📊", [py, "scripts/analyze_books.py"], root),
        ScriptSpec("Query Examples", "💬", [py, "scripts/query_examples.py"], root),
        ScriptSpec(
            "Hermes Integration",
            "🦉",
            ["bash", "scripts/test_hermes_integration.sh"],
            root,
        ),
    ]


async def stream_process(
    command: List[str],
    cwd: Path,
    on_line: LogCallback,
    env: Optional[dict] = None,
) -> int:
    """Run a subprocess and stream stdout/stderr lines to callback."""
    merged_env = {**os.environ, **(env or {})}
    proc = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=merged_env,
    )

    async def _drain(stream: asyncio.StreamReader, prefix: str) -> None:
        if stream is None:
            return
        while True:
            line = await stream.readline()
            if not line:
                break
            text = line.decode(errors="replace").rstrip()
            if text:
                on_line(f"{prefix}{text}" if prefix else text)

    await asyncio.gather(
        _drain(proc.stdout, ""),
        _drain(proc.stderr, "[ERR] "),
    )
    return await proc.wait()


async def run_pytest(cwd: Path, on_line: LogCallback) -> int:
    return await stream_process(
        [sys.executable, "-m", "pytest", "tests/unit", "-v", "--tb=short"],
        cwd,
        on_line,
    )


async def run_audit(cwd: Path, on_line: LogCallback) -> int:
    audit_sh = cwd / "run_audit.sh"
    if audit_sh.is_file():
        return await stream_process(["bash", str(audit_sh)], cwd, on_line)
    return await stream_process(
        [sys.executable, "scripts/audit_protocols.py"],
        cwd,
        on_line,
    )
