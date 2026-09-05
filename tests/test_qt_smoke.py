import os
from dataclasses import replace

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QApplication

import hoyographae.app as app_module
from hoyographae.app import FontStore, MainWindow
from hoyographae.fonts import bundled_font_faces
from hoyographae.i18n import LanguageManager
from hoyographae.rendering import render_text_image


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def test_main_window_starts_on_home_with_bundled_fonts(application, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    bundled = bundled_font_faces()
    window = MainWindow(settings)
    try:
        assert window.pages.count() == 5
        assert window.pages.currentWidget() is window.home_page
        assert window.navigation.item(0).text() == "首页"
        assert len(window.store.fonts) == 29
        assert window.store.current is window.store.fonts[0]
        assert [font.face_id for font in window.store.fonts] == [
            face.face_id for face in bundled
        ]
        assert [font.style for font in window.store.fonts] == [
            face.style for face in bundled
        ]
        assert window.store.load_errors == {}
        assert window.font_library_page.font_list.count() == 29
        assert window.glyph_browser_page._matches == window.store.current.metadata.codepoints
        assert window.text_preview_page._font().styleName() == window.store.current.style
    finally:
        window.close()


def test_one_bundled_font_failure_does_not_block_the_rest(
    application, monkeypatch, tmp_path
) -> None:
    faces = bundled_font_faces()[:2]
    broken = replace(faces[0], path=tmp_path / "missing.ttf")
    monkeypatch.setattr(app_module, "bundled_font_faces", lambda: (broken, faces[1]))

    store = FontStore(
        LanguageManager(
            QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
        )
    )

    assert [font.face_id for font in store.fonts] == [faces[1].face_id]
    assert store.current is store.fonts[0]
    assert list(store.load_errors) == [broken.face_id]


def test_language_combo_updates_every_page_and_persists(application, tmp_path) -> None:
    path = tmp_path / "settings.ini"
    window = MainWindow(QSettings(str(path), QSettings.Format.IniFormat))
    try:
        window.home_page.language_combo.setCurrentIndex(1)
        application.processEvents()

        assert window.language.language == "en_US"
        assert window.navigation.item(0).text() == "Home"
        assert window.font_library_page.title.text() == "Font Library"
        assert window.glyph_browser_page.title.text() == "Glyph Browser"
        assert window.text_preview_page.title.text() == "Live Typesetter"
        assert window.ocr_page.title.text() == "Image OCR"
    finally:
        window.close()

    restored = MainWindow(QSettings(str(path), QSettings.Format.IniFormat))
    try:
        assert restored.language.language == "en_US"
        assert restored.home_page.language_combo.currentData() == "en_US"
    finally:
        restored.close()


def test_renderer_can_create_transparent_png(application, tmp_path) -> None:
    image = render_text_image(
        "HoyoGraphae",
        QFont(),
        QColor("#ffffff"),
        None,
        width=480,
        padding=24,
    )
    output = tmp_path / "preview.png"

    assert image.hasAlphaChannel()
    assert image.pixelColor(0, 0).alpha() == 0
    assert image.save(str(output), "PNG")
    assert output.stat().st_size > 0
