"""Font-file inspection that is independent from the Qt user interface."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from fontTools.ttLib import TTFont, TTLibError


SUPPORTED_EXTENSIONS = frozenset({".ttf", ".otf"})


class FontInspectionError(ValueError):
    """Raised when a selected file cannot be used as a font."""


@dataclass(frozen=True, slots=True)
class FontMetadata:
    path: Path
    display_name: str
    codepoints: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class BundledFontFace:
    face_id: str
    path: Path
    style: str


def bundled_font_faces() -> tuple[BundledFontFace, ...]:
    """Read the generated package manifest without depending on the working directory."""

    font_root = Path(__file__).parent / "resources" / "fonts"
    try:
        manifest = json.loads(
            (font_root / "manifest.json").read_text(encoding="utf-8")
        )
        return tuple(
            BundledFontFace(
                face_id=face["face_id"],
                path=font_root / face["file"],
                style=face["style"],
            )
            for source in manifest["sources"]
            for face in source["faces"]
        )
    except (KeyError, OSError, TypeError, json.JSONDecodeError) as exc:
        raise FontInspectionError(f"无法读取内置字体清单：{exc}") from exc


def validate_font_path(path: str | Path) -> Path:
    font_path = Path(path).expanduser()
    if not font_path.is_file():
        raise FontInspectionError(f"字体文件不存在：{font_path}")
    if font_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise FontInspectionError(f"不支持 {font_path.suffix or '无扩展名'}；支持：{supported}")
    return font_path.resolve()


def _font_name(font: TTFont) -> str | None:
    if "name" not in font:
        return None
    name_table = font["name"]
    family = name_table.getBestFamilyName()
    style = name_table.getBestSubFamilyName()
    if not family:
        return None
    if style and style.casefold() not in {"regular", "normal"}:
        return f"{family} {style}"
    return family


def _collect_font(font: TTFont, codepoints: set[int], names: list[str]) -> None:
    best_cmap = font.getBestCmap() or {}
    codepoints.update(
        value
        for value in best_cmap
        if 0 <= value <= 0x10FFFF and not 0xD800 <= value <= 0xDFFF
    )
    name = _font_name(font)
    if name and name not in names:
        names.append(name)


def inspect_font(path: str | Path) -> FontMetadata:
    """Read family metadata and the Unicode cmap from a supported font file."""

    font_path = validate_font_path(path)
    codepoints: set[int] = set()
    names: list[str] = []

    try:
        font = TTFont(font_path, lazy=True)
        try:
            _collect_font(font, codepoints, names)
        finally:
            font.close()
    except (TTLibError, OSError, ImportError) as exc:
        raise FontInspectionError(f"无法读取字体：{exc}") from exc

    display_name = " / ".join(names) if names else font_path.stem
    return FontMetadata(font_path, display_name, tuple(sorted(codepoints)))


def display_character(codepoint: int) -> str:
    character = chr(codepoint)
    return character if character.isprintable() and not character.isspace() else "·"
