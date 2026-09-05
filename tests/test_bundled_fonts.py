import hashlib
import json
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

import hoyographae
from scripts.build_fonts import FontBuildError, _publish_output


EXPECTED_SOURCES = {
    "amphoreus-circuit",
    "deshret-inscription",
    "font-ainee",
    "inazuma-brush",
    "khaenriah-sun",
    "star-rail-neue",
    "sumeru-scribe",
    "teyvat-black",
    "xianzhou-seal",
    "zzz-a",
    "zzz-system",
}


def test_bundled_font_manifest_matches_valid_font_files() -> None:
    package_root = Path(hoyographae.__file__).parent
    font_root = package_root / "resources" / "fonts"
    manifest = json.loads((font_root / "manifest.json").read_text(encoding="utf-8"))
    assert "commercial use" in (font_root / "LICENSE.txt").read_text(encoding="utf-8")

    assert manifest["schema_version"] == 1
    assert {source["source_id"] for source in manifest["sources"]} == EXPECTED_SOURCES

    faces = [face for source in manifest["sources"] for face in source["faces"]]
    assert len(faces) == 29
    assert len({face["face_id"] for face in faces}) == len(faces)

    expected_files = {face["file"] for face in faces}
    actual_files = {path.name for path in font_root.glob("*.ttf")}
    assert actual_files == expected_files

    for face in faces:
        font_path = font_root / face["file"]
        assert hashlib.sha256(font_path.read_bytes()).hexdigest() == face["sha256"]

        with TTFont(font_path, lazy=True) as font:
            assert font["name"].getBestFamilyName() == face["family"]
            assert font["name"].getBestSubFamilyName() == face["style"]
            assert len(font.getBestCmap() or {}) == face["codepoint_count"]
            assert face["codepoint_count"] > 0


def test_font_publisher_refuses_to_delete_unmanaged_files(tmp_path: Path) -> None:
    generated_root = tmp_path / "generated"
    output_root = tmp_path / "output"
    generated_root.mkdir()
    output_root.mkdir()
    (generated_root / "manifest.json").write_text("{}", encoding="utf-8")
    unmanaged = output_root / "keep-me.txt"
    unmanaged.write_text("user data", encoding="utf-8")

    with pytest.raises(FontBuildError, match="unmanaged"):
        _publish_output(generated_root, output_root)

    assert unmanaged.read_text(encoding="utf-8") == "user data"
