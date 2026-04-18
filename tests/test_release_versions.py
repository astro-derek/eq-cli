from __future__ import annotations

import pytest

from eq_cli.release_versions import select_retained_versions


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
