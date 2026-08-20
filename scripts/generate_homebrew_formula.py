#!/usr/bin/env python3
"""Generate a Homebrew formula for the vrg package by querying PyPI.

Fetches the latest version of vrg and all its dependencies from PyPI,
then outputs a complete Ruby formula to stdout. Uses only stdlib modules.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from typing import NamedTuple

PACKAGE_NAME = "vrg"
PYTHON_VERSION = "3.12"

# Dependencies that are part of the Python stdlib (for 3.11+) and should be skipped
STDLIB_PACKAGES = {"tomli"}

# Packages that require Rust to build from source (maturin-based).
# When any of these appear in the dependency tree, add `depends_on "rust" => :build`.
RUST_PACKAGES = {"rpds-py"}

# Packages that require Rust/C compilation and are already handled by Homebrew core
SKIP_PACKAGES: set[str] = set()


class Resource(NamedTuple):
    name: str
    url: str
    sha256: str


def fetch_pypi_json(package: str) -> dict:
    """Fetch package metadata from the PyPI JSON API."""
    url = f"https://pypi.org/pypi/{package}/json"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_sdist(data: dict) -> tuple[str, str]:
    """Extract the sdist URL and sha256 from PyPI release data."""
    urls = data["urls"]
    for entry in urls:
        if entry["packagetype"] == "sdist":
            return entry["url"], entry["digests"]["sha256"]
    raise ValueError(f"No sdist found for {data['info']['name']}")


def normalize_name(name: str) -> str:
    """Normalize a PyPI package name (PEP 503)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requires_dist(requires_dist: list[str] | None) -> list[str]:
    """Parse requires_dist entries, filtering out optional/conditional deps.

    Skips dependencies that:
    - Have 'extra ==' markers (optional dependencies)
    - Have python_version markers that exclude 3.12
    - Have platform markers that don't match macOS/Linux
    - Are in the stdlib for Python 3.11+
    """
    if not requires_dist:
        return []

    deps = []
    for req in requires_dist:
        # Skip extras (optional dependencies)
        if "extra ==" in req or "extra==" in req:
            continue

        # Skip platform-conditional deps (e.g., colorama on Windows only)
        if 'platform_system == "Windows"' in req or "platform_system == 'Windows'" in req:
            continue

        # Check for python_version markers
        # e.g., 'tomli>=2.0; python_version < "3.11"'
        if "python_version" in req:
            # If it requires python < 3.11 or < 3.12, skip for 3.12
            if re.search(r'python_version\s*<\s*["\']3\.(1[1-9]|[2-9])', req):
                continue
            # python_version < "3.10" or lower — skip
            if re.search(r'python_version\s*<\s*["\']3\.([0-9])["\']', req):
                continue

        # Extract just the package name (before any version specifier)
        name = re.split(r"[<>=!~;\s\[]", req)[0].strip()
        normalized = normalize_name(name)

        if normalized in STDLIB_PACKAGES or normalized in SKIP_PACKAGES:
            continue

        deps.append(normalized)

    return deps


def collect_dependencies(package: str) -> dict[str, Resource]:
    """Recursively collect all dependencies for a package."""
    resources: dict[str, Resource] = {}
    visited: set[str] = set()
    queue = [package]

    while queue:
        pkg = queue.pop(0)
        normalized = normalize_name(pkg)

        if normalized in visited:
            continue
        visited.add(normalized)

        try:
            data = fetch_pypi_json(pkg)
        except Exception as e:
            print(f"Warning: Failed to fetch {pkg}: {e}", file=sys.stderr)
            continue

        info = data["info"]

        # Don't add the root package as a resource
        if normalized != normalize_name(package):
            url, sha256 = get_sdist(data)
            resources[normalized] = Resource(name=normalized, url=url, sha256=sha256)

        # Parse and queue dependencies
        sub_deps = parse_requires_dist(info.get("requires_dist"))
        for dep in sub_deps:
            if dep not in visited:
                queue.append(dep)

    return resources


def generate_formula(package: str) -> str:
    """Generate the complete Homebrew formula."""
    # Fetch root package info
    data = fetch_pypi_json(package)
    info = data["info"]
    version = info["version"]
    url, sha256 = get_sdist(data)

    # Collect all dependency resources
    print(f"Collecting dependencies for {package} {version}...", file=sys.stderr)
    resources = collect_dependencies(package)
    print(f"Found {len(resources)} dependencies", file=sys.stderr)

    # Build formula
    lines = [
        "class Vrg < Formula",
        "  include Language::Python::Virtualenv",
        "",
        '  desc "Command-line interface for VergeOS infrastructure management"',
        '  homepage "https://github.com/verge-io/vrg"',
        f'  url "{url}"',
        f'  sha256 "{sha256}"',
        '  license "Apache-2.0"',
        "",
        '  depends_on "python@3.12"',
    ]

    # Add rust build dependency if any resource needs it
    if RUST_PACKAGES & set(resources):
        lines.append('  depends_on "rust" => :build')

    # Add resources sorted by name
    for name in sorted(resources):
        res = resources[name]
        lines.extend(
            [
                "",
                f'  resource "{res.name}" do',
                f'    url "{res.url}"',
                f'    sha256 "{res.sha256}"',
                "  end",
            ]
        )

    lines.extend(
        [
            "",
            "  def install",
            "    virtualenv_install_with_resources",
            "  end",
            "",
            "  test do",
            '    assert_match version.to_s, shell_output("#{bin}/vrg --version")',
            "  end",
            "end",
            "",  # trailing newline
        ]
    )

    return "\n".join(lines)


if __name__ == "__main__":
    formula = generate_formula(PACKAGE_NAME)
    print(formula)
