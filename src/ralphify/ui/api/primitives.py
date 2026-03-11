"""REST endpoints for browsing and editing primitives."""
from __future__ import annotations

import base64
import shutil
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException

from ralphify._frontmatter import (
    CHECK_MARKER,
    CONTEXT_MARKER,
    INSTRUCTION_MARKER,
    PROMPT_MARKER,
    parse_frontmatter,
    serialize_frontmatter,
)
from ralphify.checks import discover_checks, run_check
from ralphify.contexts import discover_contexts
from ralphify.instructions import discover_instructions
from ralphify.prompts import discover_prompts
from ralphify.ui.models import CheckTestResponse, PrimitiveResponse, PrimitiveUpdate

router = APIRouter()

# Mapping from kind to (discover function, marker filename)
_KIND_MAP = {
    "checks": (discover_checks, CHECK_MARKER),
    "contexts": (discover_contexts, CONTEXT_MARKER),
    "instructions": (discover_instructions, INSTRUCTION_MARKER),
    "prompts": (discover_prompts, PROMPT_MARKER),
}


def _decode_project_dir(encoded: str) -> Path:
    """Decode a base64-encoded project directory path."""
    try:
        return Path(base64.urlsafe_b64decode(encoded).decode())
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid base64 project_dir")


def _resolve_kind(kind: str) -> tuple:
    """Look up *kind* in the registry, raising 400 if unknown.

    Returns ``(discover_fn, marker_filename)``.
    """
    try:
        return _KIND_MAP[kind]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Unknown kind: {kind}")


def _response_from_marker(marker_file: Path, kind: str, name: str) -> PrimitiveResponse:
    """Read a marker file, parse its frontmatter, and build a response.

    Centralises the read-parse-respond pattern used by list/get (via
    ``_primitive_to_response``), update, and create endpoints so the
    response construction logic lives in one place.
    """
    fm, body = parse_frontmatter(marker_file.read_text())
    return PrimitiveResponse(
        kind=kind,
        name=name,
        enabled=fm.get("enabled", True),
        content=body,
        frontmatter=fm,
    )


def _primitive_to_response(prim, kind: str) -> PrimitiveResponse:
    """Convert a discovered primitive to a response model."""
    marker = _KIND_MAP[kind][1]
    marker_file = prim.path / marker
    if not marker_file.exists():
        return PrimitiveResponse(
            kind=kind, name=prim.name, enabled=prim.enabled,
            content="", frontmatter={},
        )
    return _response_from_marker(marker_file, kind, prim.name)


@router.get(
    "/projects/{project_dir}/primitives",
    response_model=list[PrimitiveResponse],
)
async def list_primitives(project_dir: str) -> list[PrimitiveResponse]:
    """List all primitives for a project."""
    root = _decode_project_dir(project_dir)
    results: list[PrimitiveResponse] = []
    for kind, (discover_fn, _marker) in _KIND_MAP.items():
        for prim in discover_fn(root):
            results.append(_primitive_to_response(prim, kind))
    return results


@router.get(
    "/projects/{project_dir}/primitives/{kind}/{name}",
    response_model=PrimitiveResponse,
)
async def get_primitive(project_dir: str, kind: str, name: str) -> PrimitiveResponse:
    """Read a specific primitive."""
    discover_fn, _marker = _resolve_kind(kind)
    root = _decode_project_dir(project_dir)
    for prim in discover_fn(root):
        if prim.name == name:
            return _primitive_to_response(prim, kind)
    raise HTTPException(status_code=404, detail="Primitive not found")


@router.put(
    "/projects/{project_dir}/primitives/{kind}/{name}",
    response_model=PrimitiveResponse,
)
async def update_primitive(
    project_dir: str, kind: str, name: str, body: PrimitiveUpdate
) -> PrimitiveResponse:
    """Update a primitive's content and/or frontmatter."""
    _discover_fn, marker = _resolve_kind(kind)
    root = _decode_project_dir(project_dir)
    marker_file = root / ".ralph" / kind / name / marker
    if not marker_file.exists():
        raise HTTPException(status_code=404, detail="Primitive not found")

    marker_file.write_text(serialize_frontmatter(body.frontmatter or {}, body.content))
    return _response_from_marker(marker_file, kind, name)


@router.post(
    "/projects/{project_dir}/primitives/{kind}",
    response_model=PrimitiveResponse,
    status_code=201,
)
async def create_primitive(
    project_dir: str, kind: str, body: PrimitiveUpdate
) -> PrimitiveResponse:
    """Scaffold a new primitive.

    The primitive name is derived from the frontmatter 'name' field,
    which must be present.
    """
    _discover_fn, marker = _resolve_kind(kind)
    if not body.frontmatter or "name" not in body.frontmatter:
        raise HTTPException(
            status_code=400,
            detail="frontmatter must include a 'name' field",
        )
    root = _decode_project_dir(project_dir)
    name = body.frontmatter["name"]
    prim_dir = root / ".ralph" / kind / name
    if prim_dir.exists():
        raise HTTPException(status_code=409, detail="Primitive already exists")

    prim_dir.mkdir(parents=True)
    marker_file = prim_dir / marker

    marker_file.write_text(serialize_frontmatter(body.frontmatter or {}, body.content))
    return _response_from_marker(marker_file, kind, name)


@router.delete("/projects/{project_dir}/primitives/{kind}/{name}", status_code=204)
async def delete_primitive(project_dir: str, kind: str, name: str) -> None:
    """Delete a primitive directory."""
    _resolve_kind(kind)
    root = _decode_project_dir(project_dir)
    prim_dir = root / ".ralph" / kind / name
    if not prim_dir.exists():
        raise HTTPException(status_code=404, detail="Primitive not found")
    shutil.rmtree(prim_dir)


@router.post(
    "/projects/{project_dir}/primitives/checks/{name}/test",
    response_model=CheckTestResponse,
)
async def test_check(project_dir: str, name: str) -> CheckTestResponse:
    """Run a single check and return the result."""
    root = _decode_project_dir(project_dir)
    for check in discover_checks(root):
        if check.name == name:
            start = time.monotonic()
            result = run_check(check, root)
            duration = time.monotonic() - start
            return CheckTestResponse(
                passed=result.passed,
                exit_code=result.exit_code,
                output=result.output,
                timed_out=result.timed_out,
                duration=round(duration, 2),
            )
    raise HTTPException(status_code=404, detail="Check not found")
