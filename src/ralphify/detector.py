"""Auto-detect project type from manifest files.

Used during ``ralph init`` to report the detected language ecosystem.
Checks for common manifest files (package.json, pyproject.toml, etc.)
and returns a short label like "python" or "node".
"""

from pathlib import Path


# Manifest file → project type label, checked in order.
# To add a new ecosystem, add one entry here.
_PROJECT_MARKERS: dict[str, str] = {
    "package.json": "node",
    "pyproject.toml": "python",
    "Cargo.toml": "rust",
    "go.mod": "go",
}


def detect_project(path: Path = Path(".")) -> str:
    """Detect project type by checking for manifest files.

    Checks for ``package.json`` (node), ``pyproject.toml`` (python),
    ``Cargo.toml`` (rust), ``go.mod`` (go) in order.  Returns the
    first match, or ``"generic"`` if none are found.
    """
    for filename, project_type in _PROJECT_MARKERS.items():
        if (path / filename).exists():
            return project_type
    return "generic"
