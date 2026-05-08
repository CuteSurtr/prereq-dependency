"""Hello-world test so CI is green from day 1."""

from backend import __version__


def test_version() -> None:
    assert __version__ == "0.1.0"
