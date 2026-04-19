from __future__ import annotations

import re
from collections.abc import Iterable

_SEMVER_PATTERN = re.compile(r"^v?(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)$")


def _parse_semver(value: str) -> tuple[int, int, int] | None:
    """Parse a semantic version like 1.2.3 or v1.2.3."""
    match = _SEMVER_PATTERN.fullmatch(value.strip())
    if match is None:
        return None
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
    )


def select_retained_versions(
    current_version: str,
    release_versions: Iterable[str],
) -> list[str]:
    """Select retained static-page versions for deployment.

    Retention policy:
    - keep every release in the current major version line
    - keep only the latest release for each previous major line
    - include the current version even if it is not a published release yet
    """
    current = _parse_semver(current_version)
    if current is None:
        raise ValueError(f"Invalid current version: {current_version!r}")

    current_major, current_minor, current_patch = current
    kept: set[tuple[int, int, int]] = {(current_major, current_minor, current_patch)}
    latest_previous_by_major: dict[int, tuple[int, int, int]] = {}

    for raw_version in release_versions:
        parsed = _parse_semver(raw_version)
        if parsed is None:
            continue
        major, _minor, _patch = parsed
        if major == current_major:
            kept.add(parsed)
            continue
        if major > current_major:
            continue
        previous = latest_previous_by_major.get(major)
        if previous is None or parsed > previous:
            latest_previous_by_major[major] = parsed

    kept.update(latest_previous_by_major.values())
    return [
        f"{major}.{minor}.{patch}"
        for major, minor, patch in sorted(kept, reverse=True)
    ]


def extract_versions_from_manifest(manifest: object) -> list[str]:
    """Extract version strings from a versions/index.json-style payload.

    Expected manifest shape:
        {
            "current": "1.0.4",
            "retained": [{"version": "1.0.3", "path": "/versions/v1.0.3/"}],
        }

    Invalid/missing fields and entries are ignored.
    """
    if not isinstance(manifest, dict):
        return []

    versions: list[str] = []
    current = manifest.get("current")
    if isinstance(current, str):
        versions.append(current)

    retained = manifest.get("retained")
    if isinstance(retained, list):
        for entry in retained:
            if not isinstance(entry, dict):
                continue
            version = entry.get("version")
            if isinstance(version, str):
                versions.append(version)

    return versions
