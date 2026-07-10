"""Static checks for the presentation deck."""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRESENTATION_HTML = PROJECT_ROOT / "presentation" / "migrant-archive-slides.html"


def _deck_html() -> str:
    return PRESENTATION_HTML.read_text(encoding="utf-8")


def test_presentation_deck_has_expected_section_count():
    html = _deck_html()

    assert len(re.findall(r"<section\b", html)) == 13


def test_presentation_references_local_media_assets():
    html = _deck_html()
    media_refs = re.findall(r'src="media/([^"]+)"', html)

    assert media_refs
    assert all(media_ref.endswith(".mov") for media_ref in media_refs)


def test_presentation_does_not_reference_local_screen_recording():
    html = _deck_html()

    assert "Screen Recording" not in html


def test_numeric_slide_jump_is_cleared_by_other_navigation():
    html = _deck_html()

    assert "function clearNumberBuffer()" in html
    assert html.count("clearNumberBuffer();") >= 5
    assert "numTimer = setTimeout(commitNumber, 700);" in html


def test_obvious_slide_copy_regressions_are_absent():
    html = _deck_html()

    assert "Multilingual</span>" not in html
    assert "<span class=\"bullet-key\">acces</span>" not in html
    assert "spanish agent" not in html
    assert "k3 retrieval" not in html
    assert "Multilingual access" in html
    assert "Spanish agent" in html
    assert "top-3 retrieval" in html
