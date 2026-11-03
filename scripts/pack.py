#!/usr/bin/env python3
"""
INDB packer — cut a version, pack the Docker image, publish it on the site.

Source of truth for the running version is core/constants.py VERSION.
The catalog lives in releases/manifest.json (shipped inside the API image)
and is copied to the sibling site as app/data/releases.json + public/releases.json.

  python3 scripts/pack.py --dry-run
  python3 scripts/pack.py --bump minor --title "Psycho" --note "Factor-1 pathfinding"
  python3 scripts/pack.py --version 0.8.0 --deploy --publish-site --deploy-site

Does not commit, does not push git, does not force-push Fly. Those stay explicit.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT.parent / "site"
CONSTANTS = ROOT / "core" / "constants.py"
MANIFEST = ROOT / "releases" / "manifest.json"
VERSION_RE = re.compile(r'^(VERSION\s*=\s*")([^"]+)(")', re.M)


def die(msg: str, code: int = 1) -> None:
    print(f"pack: {msg}", file=sys.stderr)
    sys.exit(code)


def run(cmd: List[str], cwd: Path, dry: bool) -> None:
    print(f"  $ {' '.join(cmd)}")
    if dry:
        return
    subprocess.run(cmd, cwd=cwd, check=True)


def git_sha() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def read_version() -> str:
    text = CONSTANTS.read_text()
    match = VERSION_RE.search(text)
    if not match:
        die(f"VERSION not found in {CONSTANTS}")
    return match.group(2)


def write_version(version: str) -> None:
    text = CONSTANTS.read_text()
    if not VERSION_RE.search(text):
        die(f"VERSION not found in {CONSTANTS}")
    CONSTANTS.write_text(VERSION_RE.sub(rf"\g<1>{version}\g<3>", text, count=1))


def bump(current: str, part: str) -> str:
    try:
        major, minor, patch = (int(x) for x in current.split("."))
    except ValueError:
        die(f"VERSION {current!r} is not semver X.Y.Z")
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        return f"{major}.{minor}.{patch + 1}"
    die(f"unknown bump {part!r}")
    return current


def load_manifest() -> Dict[str, Any]:
    if not MANIFEST.exists():
        return {"current": read_version(), "releases": []}
    return json.loads(MANIFEST.read_text())


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def stamp_latest(version: str, dry: bool) -> Dict[str, Any]:
    """Point the catalog at the latest alias image.py just wrote."""
    info_path = ROOT / "dist" / "latest.json"
    if dry:
        print(f"  latest indb-latest.tar.gz → {version}")
        return load_manifest()
    if not info_path.is_file():
        die("dist/latest.json missing after export")
    info = json.loads(info_path.read_text())
    if info.get("version") != version:
        die(f"latest.json is {info.get('version')} — expected {version}")
    manifest = load_manifest()
    manifest["published"] = version
    manifest["latest"] = info["latest"]
    for release in manifest.get("releases", []):
        if release.get("version") == version:
            release["download"] = info["archive"]
            release["latest"] = info["latest"]
            write_json(ROOT / "releases" / f"{version}.json", release)
    ordered = {
        "current": manifest.get("current", version),
        "published": manifest["published"],
        "latest": manifest["latest"],
        "releases": manifest.get("releases", []),
    }
    write_json(MANIFEST, ordered)
    print(f"  latest {info['latest']}")
    return ordered


def publish_site(manifest: Dict[str, Any], dry: bool) -> None:
    if not SITE.is_dir():
        die(f"sibling site not found at {SITE}")
    targets = [
        SITE / "app" / "data" / "releases.json",
        SITE / "public" / "releases.json",
    ]
    for path in targets:
        print(f"  site ← {path.relative_to(SITE.parent)}")
        if not dry:
            write_json(path, manifest)


def pack(args: argparse.Namespace) -> None:
    current = read_version()
    if args.version:
        version = args.version.lstrip("v")
    elif args.bump:
        version = bump(current, args.bump)
    else:
        version = current

    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        die(f"refusing {version!r} — need X.Y.Z")

    sha = git_sha()
    today = date.today().isoformat()
    notes = list(args.note or [])
    if not notes:
        notes = [args.title] if args.title else [f"INDB {version}"]

    release = {
        "version": version,
        "title": args.title or f"INDB {version}",
        "date": today,
        "git": sha,
        "image": f"indb:{version}",
        "notes": notes,
        "packed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    previous = load_manifest()
    others = [r for r in previous.get("releases", []) if r.get("version") != version]
    manifest = {"current": version, "releases": [release, *others]}
    if previous.get("published"):
        manifest["published"] = previous["published"]
    if previous.get("latest"):
        manifest["latest"] = previous["latest"]
    manifest = {
        "current": manifest["current"],
        **({"published": manifest["published"]} if "published" in manifest else {}),
        **({"latest": manifest["latest"]} if "latest" in manifest else {}),
        "releases": manifest["releases"],
    }

    print(f"pack {current} → {version}" + (" (dry-run)" if args.dry_run else ""))
    print(f"  title  {release['title']}")
    print(f"  git    {sha or '—'}")
    print(f"  image  indb:{version}")
    for note in notes:
        print(f"  note   {note}")

    if not args.dry_run:
        write_version(version)
        write_json(MANIFEST, manifest)
        write_json(ROOT / "releases" / f"{version}.json", release)

    if args.docker or args.export:
        run(
            [
                "docker",
                "build",
                "--build-arg",
                f"VERSION={version}",
                "-t",
                f"indb:{version}",
                "-t",
                "indb:latest",
                ".",
            ],
            ROOT,
            args.dry_run,
        )

    if args.export:
        export_cmd = [sys.executable, str(ROOT / "scripts" / "image.py"), "--export-only"]
        run(export_cmd, ROOT, args.dry_run)
        manifest = stamp_latest(version, args.dry_run)

    if args.publish_site or args.deploy_site:
        publish_site(manifest, args.dry_run)

    if args.deploy:
        run(["fly", "deploy", "--app", "indb"], ROOT, args.dry_run)

    if args.docs:
        run(["fly", "deploy", "--config", "fly.docs.toml", "--app", "indb-docs"], ROOT, args.dry_run)

    if args.deploy_site:
        run(["fly", "deploy", "--app", "indb-presentation"], SITE, args.dry_run)

    if args.tag:
        run(["git", "tag", "-a", f"v{version}", "-m", release["title"]], ROOT, args.dry_run)

    print("pack: done")
    print(f"  health will report {version}")
    print("  catalog  releases/manifest.json")
    if args.publish_site or args.deploy_site:
        print("  site     app/data/releases.json")


def main() -> None:
    parser = argparse.ArgumentParser(description="Pack an INDB version into Docker and onto the site.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--version", help="exact semver, e.g. 0.8.0")
    group.add_argument("--bump", choices=("major", "minor", "patch"), help="bump current VERSION")
    parser.add_argument("--title", help="short release title")
    parser.add_argument("--note", action="append", help="changelog line (repeatable)")
    parser.add_argument("--docker", action="store_true", help="docker build -t indb:VERSION")
    parser.add_argument(
        "--export",
        action="store_true",
        help="write dist/indb-VERSION/ and indb-latest.tar.gz (same bytes)",
    )
    parser.add_argument("--deploy", action="store_true", help="fly deploy --app indb")
    parser.add_argument("--docs", action="store_true", help="fly deploy docs")
    parser.add_argument("--publish-site", action="store_true", help="write releases.json into ../site")
    parser.add_argument("--deploy-site", action="store_true", help="fly deploy --app indb-presentation")
    parser.add_argument("--tag", action="store_true", help="git tag vVERSION (no push)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    pack(parser.parse_args())


if __name__ == "__main__":
    main()
