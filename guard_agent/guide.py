"""VeloC guide loader — provides API reference documentation.

Wraps the bundled veloc_guide.md document with section extraction
so the MCP server and CLI can return specific sections on demand.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path


# The guide lives alongside the existing agent code.
_GUIDE_PATHS = [
    Path(__file__).parent / "guides" / "veloc_guide.md",
    Path(__file__).parent.parent / "agents" / "veloc" / "guides" / "veloc_guide.md",
]


def _find_guide() -> Path | None:
    for p in _GUIDE_PATHS:
        if p.is_file():
            return p
    return None


def load_full_guide() -> str:
    """Return the complete VeloC guide text."""
    path = _find_guide()
    if path is None:
        return ""
    return path.read_text(encoding="utf-8")


def list_sections() -> list[str]:
    """Return the list of top-level (##) section headings in the guide."""
    text = load_full_guide()
    if not text:
        return []
    return re.findall(r"^##\s+(.+)$", text, re.MULTILINE)


def get_section(section_name: str) -> str | None:
    """Extract a specific section by its heading name.

    Returns the section content (including the heading), or None if not found.
    """
    text = load_full_guide()
    if not text:
        return None

    pattern = re.compile(
        r"(^##\s+" + re.escape(section_name) + r".*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(text)
    if match:
        return match.group(1).strip()
    return None


def get_api_reference(language: str = "c") -> str | None:
    """Return the C or C++ API reference section."""
    if language.lower() in ("cpp", "c++", "cxx"):
        return get_section("C++ API Reference") or get_section("C++ API")
    return get_section("C API Reference") or get_section("C API")


def get_guide_json(section: str = "", list_sections_flag: bool = False) -> str:
    """Return guide content as JSON — compatible with the existing agent tool format.

    Args:
        section: Optional section heading to retrieve.
        list_sections_flag: When True, return only section headings.

    Returns:
        JSON string with {"sections": [...]} or {"content": "..."} or {"error": ...}.
    """
    if list_sections_flag:
        return json.dumps({"sections": list_sections()})

    if not section:
        text = load_full_guide()
        if not text:
            return json.dumps({"error": "VeloC guide not found"})
        return json.dumps({"content": text})

    content = get_section(section)
    if content:
        return json.dumps({"content": content})

    # Section not found — return full guide with a note.
    text = load_full_guide()
    return json.dumps({
        "content": text,
        "note": f"Section '{section}' not found; returning full guide.",
    })
