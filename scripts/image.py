#!/usr/bin/env python3
"""
Build the product image the site is selling, export a portable folder.

Same VERSION as /health and https://indb.tech/#releases.
Landing, docs, growth are not in the image.

  python3 scripts/image.py              # build + dist/indb-X.Y.Z/
  python3 scripts/image.py --export-only
  # copy that folder anywhere:
  ./run.sh
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT.parent / "site"
CONSTANTS = ROOT / "core" / "constants.py"
MANIFEST = ROOT / "releases" / "manifest.json"
DIST = ROOT / "dist"
PUBLIC = "https://indb.tech/releases"
VERSION_RE = re.compile(r'^(VERSION\s*=\s*")([^"]+)(")', re.M)


def die(msg: str, code: int = 1) -> None:
    print(f"image: {msg}", file=sys.stderr)
    sys.exit(code)


def version() -> str:
    text = CONSTANTS.read_text()
    match = VERSION_RE.search(text)
    if not match:
        die(f"VERSION not found in {CONSTANTS}")
    return match.group(2)


def site_current() -> str:
    for path in (
        SITE / "app" / "data" / "releases.json",
        SITE / "public" / "releases.json",
    ):
        if path.is_file():
            data = json.loads(path.read_text())
            return str(data.get("current") or "")
    return ""


def run(cmd: list[str]) -> None:
    print(f"  $ {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, check=True)


def build(ver: str) -> None:
    run(
        [
            "docker",
            "build",
            "--build-arg",
            f"VERSION={ver}",
            "-t",
            f"indb:{ver}",
            "-t",
            "indb:latest",
            ".",
        ]
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def same_file(left: Path, right: Path) -> bool:
    try:
        a, b = left.stat(), right.stat()
    except OSError:
        return False
    return a.st_dev == b.st_dev and a.st_ino == b.st_ino


def link_or_copy(src: Path, dest: Path) -> None:
    if same_file(src, dest):
        return
    if dest.exists() or dest.is_symlink():
        dest.unlink()
    try:
        os.link(src, dest)
    except OSError:
        shutil.copy2(src, dest)


def write_latest(ver: str, archive: Path) -> dict:
    """Public names for one cut: indb-X.Y.Z.tar.gz and indb-latest.tar.gz.

    latest is the same bytes. The next pack replaces that name.
    """
    checksum = sha256(archive)
    DIST.mkdir(parents=True, exist_ok=True)
    versioned = DIST / f"indb-{ver}.tar.gz"
    latest = DIST / "indb-latest.tar.gz"
    link_or_copy(archive, versioned)
    link_or_copy(archive, latest)
    (DIST / f"indb-{ver}.sha256").write_text(f"{checksum}  indb-{ver}.tar.gz\n")
    (DIST / "indb-latest.sha256").write_text(f"{checksum}  indb-latest.tar.gz\n")
    payload = {
        "version": ver,
        "image": f"indb:{ver}",
        "also": "indb:latest",
        "archive": f"{PUBLIC}/indb-{ver}.tar.gz",
        "latest": f"{PUBLIC}/indb-latest.tar.gz",
        "checksum": f"{PUBLIC}/indb-latest.sha256",
        "sha256": checksum,
        "bytes": archive.stat().st_size,
    }
    (DIST / "latest.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(f"image: latest  indb-latest.tar.gz  is  indb:{ver}")
    print(f"  {payload['latest']}")
    print(f"  {payload['archive']}")
    return payload


def export(ver: str) -> Path:
    bundle = DIST / f"indb-{ver}"
    if bundle.exists():
        shutil.rmtree(bundle)
    bundle.mkdir(parents=True)

    archive = bundle / "image.tar.gz"
    print(f"  docker save indb:{ver} indb:latest → {archive.relative_to(ROOT)}")
    save = subprocess.Popen(
        ["docker", "save", f"indb:{ver}", "indb:latest"],
        stdout=subprocess.PIPE,
        cwd=ROOT,
    )
    assert save.stdout is not None
    with gzip.open(archive, "wb", compresslevel=6) as out:
        shutil.copyfileobj(save.stdout, out)
    if save.wait() != 0:
        die("docker save failed")

    checksum = sha256(archive)
    (bundle / "SHA256SUMS").write_text(f"{checksum}  image.tar.gz\n")
    (bundle / "VERSION").write_text(f"{ver}\n")

    release = {
        "version": ver,
        "image": f"indb:{ver}",
        "artifact": f"dist/indb-{ver}/image.tar.gz",
        "sha256": checksum,
        "bytes": archive.stat().st_size,
        "packed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "demo": "https://api.indb.tech",
        "site": "https://indb.tech",
    }
    (bundle / "release.json").write_text(
        json.dumps(release, indent=2, ensure_ascii=False) + "\n"
    )

    (bundle / "run.sh").write_text(
        f"""#!/bin/sh
# Load the portable INDB image and run it like postgres.
set -eu
DIR=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
NAME="${{INDB_NAME:-indb}}"
IMAGE="indb:{ver}"

docker load -i "$DIR/image.tar.gz"

if docker inspect "$NAME" >/dev/null 2>&1; then
  echo "image: container $NAME already exists — docker start $NAME" >&2
  docker start "$NAME"
else
  docker run -d --name "$NAME" \\
    -p "${{PORT:-8000}}:8000" \\
    -p "${{UDP_PORT:-9001}}:9001/udp" \\
    -p "${{GRPC_PORT:-50051}}:50051" \\
    -v "${{INDB_VOLUME:-indb-data}}:/data" \\
    -e AUTH_MODE="${{AUTH_MODE:-OPEN}}" \\
    -e DATA_DIR=/data \\
    "$IMAGE"
fi

echo "INDB {ver}  http://127.0.0.1:${{PORT:-8000}}/health"
echo "WUI         http://127.0.0.1:${{PORT:-8000}}/wui/"
echo "same cut as https://api.indb.tech"
"""
    )
    (bundle / "run.sh").chmod((bundle / "run.sh").stat().st_mode | 0o111)

    print(f"image: portable bundle {bundle.relative_to(ROOT)}")
    print(f"  {archive.name}  {archive.stat().st_size} bytes")
    print(f"  sha256  {checksum}")
    write_latest(ver, archive)
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the current INDB image and export a portable folder."
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="do not build — save whatever indb:VERSION is already tagged",
    )
    args = parser.parse_args()

    ver = version()
    sold = site_current()
    print(f"image: kernel {ver}")
    if sold and sold != ver:
        die(f"site catalog is {sold} — pack --publish-site before exporting")
    if sold:
        print(f"image: site   v{sold}  (matches)")

    if not args.export_only:
        build(ver)
    else:
        inspect = subprocess.run(
            ["docker", "image", "inspect", f"indb:{ver}"],
            cwd=ROOT,
            capture_output=True,
        )
        if inspect.returncode != 0:
            die(f"indb:{ver} is not built — run without --export-only")

    export(ver)
    print("image: done")
    print(f"  copy  dist/indb-{ver}/")
    print(f"  run   dist/indb-{ver}/run.sh")


if __name__ == "__main__":
    main()
