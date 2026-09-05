from pathlib import Path

import pytest
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

from hoyographae.fonts import (
    FontInspectionError,
    display_character,
    inspect_font,
    validate_font_path,
)


def _make_test_font(path: Path) -> None:
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder([".notdef", "A"])
    builder.setupCharacterMap({0x41: "A"})

    glyphs = {}
    for name in (".notdef", "A"):
        pen = TTGlyphPen(None)
        glyphs[name] = pen.glyph()
    builder.setupGlyf(glyphs)
    builder.setupHorizontalMetrics({".notdef": (600, 0), "A": (600, 0)})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable(
        {
            "familyName": "HoyoGraphae Test",
            "styleName": "Regular",
            "uniqueFontIdentifier": "HoyoGraphae Test Regular",
            "fullName": "HoyoGraphae Test Regular",
            "psName": "HoyoGraphaeTest-Regular",
        }
    )
    builder.setupOS2()
    builder.setupPost()
    builder.setupMaxp()
    builder.save(path)


def test_inspect_font_reads_name_and_cmap(tmp_path: Path) -> None:
    font_path = tmp_path / "test.ttf"
    _make_test_font(font_path)

    metadata = inspect_font(font_path)

    assert metadata.display_name == "HoyoGraphae Test"
    assert metadata.codepoints == (0x41,)
    assert metadata.path == font_path.resolve()


def test_validate_font_path_rejects_missing_and_unknown_files(tmp_path: Path) -> None:
    with pytest.raises(FontInspectionError, match="不存在"):
        validate_font_path(tmp_path / "missing.ttf")

    text_path = tmp_path / "not-a-font.txt"
    text_path.write_text("no", encoding="utf-8")
    with pytest.raises(FontInspectionError, match="不支持"):
        validate_font_path(text_path)


def test_display_character() -> None:
    assert display_character(0x41) == "A"
    assert display_character(0x0A) == "·"
