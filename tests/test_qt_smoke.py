import os

import pytest


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QApplication

from hoyographae.app import MainWindow
from hoyographae.rendering import render_text_image


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def test_main_window_starts_without_loaded_fonts(application) -> None:
    window = MainWindow()
    try:
        assert window.pages.count() == 4
        assert window.store.fonts == []
        assert window.store.current is None
    finally:
        window.close()


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

