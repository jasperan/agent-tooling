"""Test that optional dependency groups are properly defined."""

import sys

def test_pyproject_has_openhands_extra():
    """Verify openhands extra exists in pyproject.toml."""
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)
    extras = config["project"]["optional-dependencies"]
    assert "openhands" in extras
    assert "docker" in extras
    assert "pidev" in extras

def test_pyproject_all_includes_openhands():
    """Verify 'all' extra includes openhands."""
    if sys.version_info >= (3, 11):
        import tomllib
    else:
        import tomli as tomllib
    with open("pyproject.toml", "rb") as f:
        config = tomllib.load(f)
    all_deps = config["project"]["optional-dependencies"]["all"]
    all_str = " ".join(all_deps)
    assert "openhands" in all_str
