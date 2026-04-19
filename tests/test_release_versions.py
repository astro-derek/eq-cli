from __future__ import annotations

import pytest

from eq_cli.release_versions import (
    extract_versions_from_manifest,
    select_retained_versions,
)


def test_select_retained_versions_keeps_current_major_and_latest_previous() -> None:
    """Retention should keep all current-major versions and one per older major."""
    retained = select_retained_versions(
        current_version="3.0.2",
        release_versions=[
            "v1.0.0",
            "1.4.0",
            "2.0.0",
            "2.3.1",
            "3.0.0",
            "3.0.1",
        ],
    )

    assert retained == ["3.0.2", "3.0.1", "3.0.0", "2.3.1", "1.4.0"]


def test_select_retained_versions_ignores_invalid_and_future_versions() -> None:
    """Non-semver and future-major versions should be ignored."""
    retained = select_retained_versions(
        current_version="2.1.0",
        release_versions=["foo", "v2", "3.0.0", "v2.0.0", "1.9.9"],
    )

    assert retained == ["2.1.0", "2.0.0", "1.9.9"]


def test_select_retained_versions_rejects_invalid_current_version() -> None:
    """Current version must be a valid semantic version."""
    with pytest.raises(ValueError, match="Invalid current version"):
        select_retained_versions(current_version="2.1", release_versions=["2.0.0"])


def test_extract_versions_from_manifest_includes_current_and_retained() -> None:
    """Manifest versions should include current and retained entries."""
    versions = extract_versions_from_manifest(
        {
            "current": "1.0.4",
            "retained": [
                {"version": "1.0.3", "path": "/versions/v1.0.3/"},
                {"version": "1.0.2", "path": "/versions/v1.0.2/"},
            ],
        }
    )

    assert versions == ["1.0.4", "1.0.3", "1.0.2"]


def test_extract_versions_from_manifest_ignores_unexpected_entries() -> None:
    """Unexpected manifest shapes should not raise and should be ignored."""
    versions = extract_versions_from_manifest(
        {
            "current": 104,
            "retained": [
                None,
                {"version": "1.0.3"},
                {"path": "/versions/v1.0.2/"},
                "1.0.1",
            ],
        }
    )

    assert versions == ["1.0.3"]
