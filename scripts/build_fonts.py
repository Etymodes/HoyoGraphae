"""Build the bundled TrueType fonts from the tracked Glyphs sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from fontTools.designspaceLib import DesignSpaceDocument
from fontTools.ttLib import TTFont


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPOSITORY_ROOT / "src" / "hoyographae" / "resources" / "fonts"
EXPECTED_TOOLCHAIN = {
    "fontmake": "3.12.1",
    "glyphsLib": "6.14.0",
    "fonttools": "4.64.0",
}


@dataclass(frozen=True, slots=True)
class FontSource:
    source_id: str
    filename: str
    build_mode: str
    expected_faces: int


FONT_SOURCES = (
    FontSource("amphoreus-circuit", "Amphoreus-Circuit.glyphs", "instances", 5),
    FontSource("deshret-inscription", "Deshret-Inscription.glyphs", "master", 1),
    FontSource("font-ainee", "Font-Ainee.glyphs", "master", 1),
    FontSource("inazuma-brush", "Inazuma-Brush.glyphs", "instances", 1),
    FontSource("khaenriah-sun", "Khaenriah-Sun.glyphs", "instances", 2),
    FontSource("star-rail-neue", "Star-Rail-Neue.glyphs", "star-rail", 10),
    FontSource("sumeru-scribe", "Sumeru-Scribe.glyphs", "instances", 1),
    FontSource("teyvat-black", "Teyvat-Black.glyphs", "master", 1),
    FontSource("xianzhou-seal", "Xianzhou-Seal.glyphs", "instances", 5),
    FontSource("zzz-a", "ZZZ-A.glyphs", "master", 1),
    FontSource("zzz-system", "ZZZ-System.glyphs", "master", 1),
)


class FontBuildError(RuntimeError):
    """Raised when a source cannot produce its expected bundled faces."""


def _toolchain_versions() -> dict[str, str]:
    result: dict[str, str] = {}
    for package, expected in EXPECTED_TOOLCHAIN.items():
        try:
            actual = version(package)
        except PackageNotFoundError as exc:
            raise FontBuildError(
                f"Missing build dependency {package}=={expected}. "
                "Install requirements-font-build.txt first."
            ) from exc
        if actual != expected:
            raise FontBuildError(
                f"Unsupported {package} version {actual}; expected {expected}."
            )
        result[package] = actual
    return result


def _run_fontmake(arguments: list[str]) -> None:
    environment = os.environ.copy()
    environment["SOURCE_DATE_EPOCH"] = "0"
    completed = subprocess.run(
        [sys.executable, "-m", "fontmake", *arguments],
        cwd=REPOSITORY_ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode:
        raise FontBuildError(completed.stdout.rstrip())


def _build_star_rail(source_path: Path, work_root: Path, output_dir: Path) -> None:
    designspace_path = work_root / "StarRailNeue.designspace"
    master_dir = work_root / "masters"
    _run_fontmake(
        [
            "-g",
            str(source_path),
            "-o",
            "ufo",
            "--master-dir",
            str(master_dir),
            "--designspace-path",
            str(designspace_path),
        ]
    )

    document = DesignSpaceDocument.fromfile(designspace_path)
    serif_axes = [axis for axis in document.axes if axis.tag == "srif"]
    if len(serif_axes) != 1:
        raise FontBuildError("Star Rail Neue must contain exactly one srif axis.")
    serif_axis = serif_axes[0]
    if (serif_axis.minimum, serif_axis.default, serif_axis.maximum) != (0, 0, 0):
        raise FontBuildError("The Star Rail Neue srif compatibility rule is outdated.")
    serif_axis.maximum = 1
    document.write(designspace_path)

    _run_fontmake(
        [
            "-m",
            str(designspace_path),
            "-o",
            "ttf",
            "-i",
            "--output-dir",
            str(output_dir),
            "--no-autohint",
            "--keep-overlaps",
        ]
    )


def _build_source(spec: FontSource, work_root: Path) -> list[Path]:
    source_path = REPOSITORY_ROOT / "src" / spec.filename
    if not source_path.is_file():
        raise FontBuildError(f"Missing source: {source_path}")

    source_work = work_root / spec.source_id
    output_dir = source_work / "output"
    output_dir.mkdir(parents=True)

    if spec.build_mode == "star-rail":
        _build_star_rail(source_path, source_work, output_dir)
    else:
        mode_argument = "-M" if spec.build_mode == "master" else "-i"
        _run_fontmake(
            [
                "-g",
                str(source_path),
                "-o",
                "ttf",
                mode_argument,
                "--output-dir",
                str(output_dir),
                "--master-dir",
                "{tmp}",
                "--instance-dir",
                "{tmp}",
                "--no-autohint",
                "--keep-overlaps",
            ]
        )

    fonts = sorted(output_dir.glob("*.ttf"))
    if len(fonts) != spec.expected_faces:
        raise FontBuildError(
            f"{spec.filename} produced {len(fonts)} TTF files; "
            f"expected {spec.expected_faces}."
        )
    return fonts


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def _inspect_face(spec: FontSource, font_path: Path) -> dict[str, object]:
    with TTFont(font_path, lazy=True) as font:
        family = font["name"].getBestFamilyName()
        style = font["name"].getBestSubFamilyName()
        codepoint_count = len(font.getBestCmap() or {})
    if not family or not style or not codepoint_count:
        raise FontBuildError(f"Incomplete OpenType metadata: {font_path.name}")

    return {
        "face_id": f"{spec.source_id}--{_slug(font_path.stem)}",
        "file": font_path.name,
        "family": family,
        "style": style,
        "codepoint_count": codepoint_count,
        "sha256": hashlib.sha256(font_path.read_bytes()).hexdigest(),
    }


def _build_manifest(work_root: Path, toolchain: dict[str, str]) -> tuple[Path, dict]:
    bundled_root = work_root / "bundled"
    bundled_root.mkdir()
    shutil.copyfile(
        REPOSITORY_ROOT / "LICENSES" / "HoYo-Glyphs-NONCOMMERCIAL.txt",
        bundled_root / "LICENSE.txt",
    )
    sources = []
    output_names: set[str] = set()
    face_ids: set[str] = set()

    for index, spec in enumerate(FONT_SOURCES, start=1):
        print(f"[{index}/{len(FONT_SOURCES)}] {spec.filename}", flush=True)
        built_fonts = _build_source(spec, work_root)
        faces = []
        for built_font in built_fonts:
            if built_font.name in output_names:
                raise FontBuildError(f"Duplicate output filename: {built_font.name}")
            output_names.add(built_font.name)
            destination = bundled_root / built_font.name
            shutil.copyfile(built_font, destination)
            face = _inspect_face(spec, destination)
            if face["face_id"] in face_ids:
                raise FontBuildError(f"Duplicate face ID: {face['face_id']}")
            face_ids.add(str(face["face_id"]))
            faces.append(face)
        sources.append(
            {
                "source_id": spec.source_id,
                "source_file": f"src/{spec.filename}",
                "build_mode": spec.build_mode,
                "faces": faces,
            }
        )

    manifest = {
        "schema_version": 1,
        "format": "TrueType",
        "toolchain": toolchain,
        "sources": sources,
    }
    manifest_path = bundled_root / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return bundled_root, manifest


def _compare_output(generated_root: Path, output_root: Path) -> None:
    generated = {path.name: path.read_bytes() for path in generated_root.iterdir()}
    existing = (
        {path.name: path.read_bytes() for path in output_root.iterdir() if path.is_file()}
        if output_root.is_dir()
        else {}
    )
    if generated != existing:
        changed = sorted(set(generated) ^ set(existing))
        changed.extend(
            sorted(
                name
                for name in set(generated) & set(existing)
                if generated[name] != existing[name]
            )
        )
        raise FontBuildError("Bundled fonts are out of date: " + ", ".join(changed))


def _publish_output(generated_root: Path, output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    generated_names = {path.name for path in generated_root.iterdir()}
    manifest_path = output_root / "manifest.json"
    previously_generated = {"LICENSE.txt", "manifest.json"}
    if manifest_path.is_file():
        try:
            previous = json.loads(manifest_path.read_text(encoding="utf-8"))
            previously_generated.update(
                face["file"]
                for source in previous["sources"]
                for face in source["faces"]
            )
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise FontBuildError(
                f"Refusing to replace an invalid existing manifest: {manifest_path}"
            ) from exc

    unmanaged = sorted(
        path.name
        for path in output_root.iterdir()
        if path.is_file() and path.name not in previously_generated
    )
    if unmanaged:
        raise FontBuildError(
            "Refusing to delete unmanaged output files: " + ", ".join(unmanaged)
        )

    for stale_name in previously_generated - generated_names:
        stale_path = output_root / stale_name
        if stale_path.is_file():
            stale_path.unlink()
    for generated in generated_root.iterdir():
        shutil.copyfile(generated, output_root / generated.name)


def build_fonts(output_root: Path, check: bool) -> int:
    toolchain = _toolchain_versions()
    with tempfile.TemporaryDirectory(prefix="hoyographae-font-build-") as temporary:
        generated_root, manifest = _build_manifest(Path(temporary), toolchain)
        if check:
            _compare_output(generated_root, output_root)
            action = "FONT_BUILD_CHECK_OK"
        else:
            _publish_output(generated_root, output_root)
            action = "FONT_BUILD_OK"

    face_count = sum(len(source["faces"]) for source in manifest["sources"])
    print(action)
    print(f"SOURCES={len(manifest['sources'])}")
    print(f"FACES={face_count}")
    print(f"OUTPUT={output_root}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    try:
        return build_fonts(arguments.output_dir.resolve(), arguments.check)
    except FontBuildError as exc:
        print(f"FONT_BUILD_ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
