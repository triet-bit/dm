"""Smoke tests for the initial project package."""

from instacart_mining import __version__


def test_package_version() -> None:
    """The package exposes a semantic version."""
    assert __version__ == "0.1.0"
