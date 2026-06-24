"""Tests for speaker extraction from video descriptions and titles.

Covers:
  - _extract_speakers_from_description for multiple description patterns
  - _normalize_math_bold unicode normalization
  - _speaker_from_metadata description-first fallback behavior
"""

import sys
from pathlib import Path

# Allow imports from backend/agents.
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "agents"))

import pytest

from tools import (
    _extract_speakers_from_description,
    _normalize_math_bold,
    _get_channel_and_speakers,
)


# Real description snippets extracted from data/raw/whisper/*.json.

DESCRIPTION_PARTICIPANTES = """\n🌍 Participantes:\n\n📌 Lucía Mbomío Rubio (@luciambomio)\nPeriodista, escritora y referente del pensamiento afrofeminista en España.\n\n📌 Safia El Aaddam (@hijadeinmigrantes)\nComunicadora, activista antirracista y escritora.\n\n📌 Desirée Bela-Lobedde (@desireebelal) – Moderadora\nActivista afrofeminista, escritora y divulgadora.\n"""

DESCRIPTION_NOS_ACOMPANAN = """\nNos acompañan:\n👉🏾 𝐍𝐚𝐝𝐢𝐚 𝐉𝐚𝐛𝐫: Activista palestina-Siria. Se graduó en el Departamento de Inglés.\n\n👉🏾 𝐌𝐨𝐡𝐚𝐦𝐚𝐝 𝐁𝐢𝐭𝐚𝐫𝐢: Poeta, traductor, escritor y periodista palestino de Siria.\n\n📍𝗠𝗼𝗱𝗲𝗿𝗮: 𝗩𝗶𝘃𝗶 𝗔𝗹𝗳𝗼𝗻𝘀í𝗻 @vivialfonsin\nEscritora cubana radicada en Barcelona.\n"""

DESCRIPTION_CONVOCA_A = """\n📍 𝐕𝐨𝐜𝐞𝐬: ¿𝐇𝐚𝐜𝐢𝐚 𝐝ó𝐧𝐝𝐞 𝐯𝐚 𝐥𝐚 𝐩𝐫𝐨𝐝𝐮𝐜𝐜𝐢ó𝐧 𝐜𝐮𝐥𝐭𝐮𝐫𝐚𝐥 𝐦𝐢𝐠𝐫𝐚𝐧𝐭𝐞 𝐞𝐧 𝐞𝐥 𝐄𝐬𝐭𝐚𝐝𝐨 𝐄𝐬𝐩𝐚ñ𝐨𝐥? Es un conversatorio que convoca a: 𝐕𝐢𝐯𝐢 𝐀𝐥𝐟𝐨𝐧𝐬í𝐧, 𝐌𝐨𝐡𝐚 𝐆𝐞𝐫𝐞𝐡𝐨𝐮, 𝐃𝐚𝐠𝐦𝐚𝐫𝐲 𝐎𝐥í𝐯𝐚𝐫 𝐲 𝐒𝐢𝐥𝐯𝐢𝐚 𝐑𝐚𝐦í𝐫𝐞𝐳, en un diálogo distendido.\n"""

DESCRIPTION_MODERA = """\n📍𝗠𝗼𝗱𝗲𝗿𝗮: 𝗩𝗶𝘃𝗶 𝗔𝗹𝗳𝗼𝗻𝘀í𝗻 @vivialfonsin\nEscritora cubana radicada en Barcelona.\n"""

TITLE_CON = "Escrituras Otras con Lucía Mbomío, Safia El Aaddam y Desirée Bela-Lobedde | FILMIG 2025"


class TestExtractSpeakersFromDescription:
    """Unit tests for backend/agents/tools.py::_extract_speakers_from_description."""

    def test_extract_speakers_participantes_section(self):
        result = _extract_speakers_from_description(DESCRIPTION_PARTICIPANTES)

        assert "Lucía Mbomío Rubio" in result
        assert "Safia El Aaddam" in result
        assert "Desirée Bela-Lobedde" in result

    def test_extract_speakers_nos_acompanan(self):
        result = _extract_speakers_from_description(DESCRIPTION_NOS_ACOMPANAN)

        assert "Nadia Jabr" in result
        assert "Mohamad Bitari" in result

    def test_extract_speakers_convoca_a(self):
        result = _extract_speakers_from_description(DESCRIPTION_CONVOCA_A)

        assert "Vivi Alfonsín" in result
        assert "Moha Gerehou" in result
        assert "Dagmary Olívar" in result
        assert "Silvia Ramírez" in result

    def test_extract_speakers_modera(self):
        result = _extract_speakers_from_description(DESCRIPTION_MODERA)

        assert "Vivi Alfonsín" in result

    def test_extract_speakers_from_title(self):
        result = _extract_speakers_from_description("", title=TITLE_CON)

        assert "Lucía Mbomío" in result
        assert "Safia El Aaddam" in result
        assert "Desirée Bela-Lobedde" in result

    def test_extract_speakers_title_without_list_ignored(self):
        result = _extract_speakers_from_description("", title="Conference on migration with one speaker")

        assert result == ""

    def test_extract_speakers_empty_description(self):
        result = _extract_speakers_from_description("")

        assert result == ""

    def test_get_channel_and_speakers_fallback(self):
        """When description has no speaker patterns, channel is returned and speakers is empty."""
        metadata = {"channel": "Plataforma Cero", "uploader": "Plataforma Cero"}
        channel, speakers = _get_channel_and_speakers(
            metadata, description="Just a plain description without any markers."
        )

        assert channel == "Plataforma Cero"
        assert speakers == ""

    def test_get_channel_and_speakers_with_extraction(self):
        """When description has speaker patterns, both channel and speakers are returned."""
        metadata = {"channel": "Plataforma Cero"}
        channel, speakers = _get_channel_and_speakers(
            metadata, description=DESCRIPTION_PARTICIPANTES,
        )

        assert channel == "Plataforma Cero"
        assert "Lucía Mbomío Rubio" in speakers
        assert "Safia El Aaddam" in speakers


class TestNormalizeMathBold:
    """Unit tests for backend/agents/tools.py::_normalize_math_bold."""

    def test_normalize_math_bold(self):
        bold_input = "𝐍𝐚𝐝𝐢𝐚 𝐉𝐚𝐛𝐫 𝐌𝐨𝐡𝐚𝐦𝐚𝐝 𝐁𝐢𝐭𝐚𝐫𝐢"
        result = _normalize_math_bold(bold_input)

        assert result == "Nadia Jabr Mohamad Bitari"

    def test_normalize_math_bold_mixed(self):
        mixed = "𝐇𝐨𝐥𝐚 Vivi Alfonsín"
        result = _normalize_math_bold(mixed)

        assert result == "Hola Vivi Alfonsín"

    def test_normalize_math_bold_empty(self):
        assert _normalize_math_bold("") == ""
