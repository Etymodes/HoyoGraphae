"""Application shell and shared font state."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtGui import QFont, QFontDatabase, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .fonts import FontInspectionError, FontMetadata, bundled_font_faces, inspect_font
from .i18n import LanguageManager
from .pages import FontLibraryPage, GlyphBrowserPage, HomePage, OcrPage, TextPreviewPage


@dataclass(frozen=True, slots=True)
class LoadedFont:
    metadata: FontMetadata
    family: str
    style: str
    application_font_id: int
    face_id: str | None = None

    def qfont(self, point_size: int) -> QFont:
        font = QFont(self.family)
        if self.style:
            font.setStyleName(self.style)
        font.setPointSize(point_size)
        return font


class FontStore(QObject):
    fonts_changed = Signal()
    current_changed = Signal(object)

    def __init__(self, language: LanguageManager) -> None:
        super().__init__()
        self.language = language
        self.fonts: list[LoadedFont] = []
        self.current: LoadedFont | None = None
        self.load_errors: dict[str, str] = {}
        self.load_bundled()

    def add(
        self,
        path: str,
        *,
        face_id: str | None = None,
        style: str = "",
        make_current: bool = True,
    ) -> LoadedFont:
        metadata = inspect_font(path)
        for index, loaded in enumerate(self.fonts):
            if loaded.metadata.path == metadata.path:
                if make_current:
                    self.select(index)
                return loaded

        font_id = QFontDatabase.addApplicationFont(str(metadata.path))
        if font_id < 0:
            raise FontInspectionError(self.language.text("font.qt_load_error"))
        families = QFontDatabase.applicationFontFamilies(font_id)
        if not families:
            QFontDatabase.removeApplicationFont(font_id)
            raise FontInspectionError(self.language.text("font.family_error"))

        loaded = LoadedFont(metadata, families[0], style, font_id, face_id)
        self.fonts.append(loaded)
        if make_current:
            self.current = loaded
        self.fonts_changed.emit()
        if make_current:
            self.current_changed.emit(loaded)
        return loaded

    def load_bundled(self) -> None:
        try:
            faces = bundled_font_faces()
        except FontInspectionError as exc:
            self.load_errors["manifest"] = str(exc)
            return

        first_loaded: LoadedFont | None = None
        for face in faces:
            try:
                loaded = self.add(
                    str(face.path),
                    face_id=face.face_id,
                    style=face.style,
                    make_current=False,
                )
            except FontInspectionError as exc:
                self.load_errors[face.face_id] = str(exc)
                continue
            if first_loaded is None:
                first_loaded = loaded

        if first_loaded is not None:
            self.current = first_loaded
            self.current_changed.emit(first_loaded)

    def select(self, row: int) -> None:
        if not 0 <= row < len(self.fonts):
            return
        selected = self.fonts[row]
        if selected != self.current:
            self.current = selected
            self.current_changed.emit(selected)


class MainWindow(QMainWindow):
    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()
        self.setWindowTitle("HoyoGraphae")
        self.resize(1280, 820)
        self.setMinimumSize(980, 680)

        resource_dir = Path(__file__).parent / "resources"
        window_icon_path = resource_dir / "hoyographae.ico"
        brand_icon_path = resource_dir / "hoyographae-icon-512.png"
        if window_icon_path.is_file():
            self.setWindowIcon(QIcon(str(window_icon_path)))

        self.language = LanguageManager(settings)
        self.store = FontStore(self.language)
        self.pages = QStackedWidget()
        self.home_page = HomePage(self.language)
        self.font_library_page = FontLibraryPage(self.store, self.language)
        self.glyph_browser_page = GlyphBrowserPage(self.store, self.language)
        self.text_preview_page = TextPreviewPage(self.store, self.language)
        self.ocr_page = OcrPage(self.language)
        for page in (
            self.home_page,
            self.font_library_page,
            self.glyph_browser_page,
            self.text_preview_page,
            self.ocr_page,
        ):
            self.pages.addWidget(page)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(238)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 24, 20, 20)
        sidebar_layout.setSpacing(12)

        if brand_icon_path.is_file():
            icon_label = QLabel()
            icon_label.setPixmap(
                QPixmap(str(brand_icon_path)).scaled(
                    68,
                    68,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            sidebar_layout.addWidget(icon_label)
        brand = QLabel("HoyoGraphae")
        brand.setObjectName("brand")
        self.tagline = QLabel()
        self.tagline.setObjectName("tagline")
        sidebar_layout.addWidget(brand)
        sidebar_layout.addWidget(self.tagline)
        sidebar_layout.addSpacing(14)

        self.navigation = QListWidget()
        self.navigation.setObjectName("navigation")
        self.navigation.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for _ in range(self.pages.count()):
            self.navigation.addItem(QListWidgetItem())
        self.navigation.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.navigation.setCurrentRow(0)
        sidebar_layout.addWidget(self.navigation, 1)

        footer = QLabel(f"LOCAL MVP  ·  {__version__}")
        footer.setObjectName("sidebarFooter")
        sidebar_layout.addWidget(footer)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)

        self.language.changed.connect(self.retranslate)
        self.retranslate()

    def retranslate(self, _language: str | None = None) -> None:
        self.tagline.setText(self.language.text("app.tagline"))
        navigation_keys = (
            "nav.home",
            "nav.font_library",
            "nav.glyphs",
            "nav.typesetter",
            "nav.ocr",
        )
        for index, key in enumerate(navigation_keys):
            self.navigation.item(index).setText(self.language.text(key))


STYLE_SHEET = """
QWidget {
    background: #081B2C;
    color: #DDF4FF;
    font-size: 14px;
}
#sidebar { background: #061522; border-right: 1px solid #1E4D68; }
#brand { color: #F3FBFF; font-size: 25px; font-weight: 700; }
#tagline, #sidebarFooter, #mutedLabel, #pageSubtitle { color: #87BBD2; }
#sidebarFooter { font-size: 11px; letter-spacing: 1px; }
#pageTitle { color: #F4FCFF; font-size: 28px; font-weight: 700; }
#pageSubtitle { font-size: 14px; }
#navigation { background: transparent; border: 0; outline: 0; }
#navigation::item { padding: 13px 12px; margin: 2px 0; border-radius: 7px; color: #A8CFDF; }
#navigation::item:selected { background: #123E59; color: #EAF9FF; border-left: 3px solid #6DDAFF; }
QPushButton {
    background: #123A53;
    border: 1px solid #2A6682;
    border-radius: 6px;
    padding: 8px 14px;
}
QPushButton:hover { background: #194B67; border-color: #69D3F8; }
QPushButton:disabled { color: #537488; background: #102636; border-color: #183C51; }
#primaryButton { background: #16749B; border-color: #62D7FF; color: white; font-weight: 600; }
QListWidget, QTableWidget, QTextEdit, QScrollArea, QSpinBox, QComboBox {
    background: #0D2639;
    border: 1px solid #24536B;
    border-radius: 7px;
    selection-background-color: #236486;
}
QListWidget::item { padding: 10px; }
QListWidget#fontInventory { background: #081B2C; alternate-background-color: #081B2C; }
QListWidget#fontInventory::item { background: #081B2C; color: #DDF4FF; }
QHeaderView::section { background: #102F45; border: 0; }
QScrollBar:vertical { background: #0A2031; width: 12px; }
QScrollBar::handle:vertical { background: #285B72; min-height: 28px; border-radius: 5px; }
#previewCanvas { background: #0B2234; }
#imageDropZone { background: #0D2639; border: 1px dashed #3B7894; border-radius: 8px; color: #6FA1B8; }
#noticeCard { background: #102F45; border: 1px solid #2A6682; border-radius: 8px; }
#noticeTitle { color: #7DE1FF; font-size: 17px; font-weight: 700; }
#sourceCharacterLabel { color: #87BBD2; font-size: 11px; }
QToolTip { background: #DDF4FF; color: #071824; border: 0; }
"""


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("HoyoGraphae")
    app.setOrganizationName("HoyoGraphae")
    app.setStyle("Fusion")
    app.setStyleSheet(STYLE_SHEET)
    window = MainWindow()
    window.show()
    return app.exec()
