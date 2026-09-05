"""Qt Widgets pages used by the desktop application."""

from __future__ import annotations

import unicodedata
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QImageReader, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import __version__
from .fonts import SUPPORTED_EXTENSIONS, display_character, format_codepoint
from .i18n import LanguageManager
from .rendering import render_text_image


def _page_title(title: str, subtitle: str) -> tuple[QLabel, QLabel]:
    heading = QLabel(title)
    heading.setObjectName("pageTitle")
    detail = QLabel(subtitle)
    detail.setObjectName("pageSubtitle")
    detail.setWordWrap(True)
    return heading, detail


class HomePage(QWidget):
    def __init__(self, language: LanguageManager) -> None:
        super().__init__()
        self.language = language
        self.title, self.subtitle = _page_title("", "")

        self.intro = QLabel()
        self.intro.setWordWrap(True)

        feature_card = QFrame()
        feature_card.setObjectName("noticeCard")
        feature_layout = QVBoxLayout(feature_card)
        self.features_title = QLabel()
        self.features_title.setObjectName("noticeTitle")
        self.features = QLabel()
        self.features.setWordWrap(True)
        feature_layout.addWidget(self.features_title)
        feature_layout.addWidget(self.features)

        settings_card = QFrame()
        settings_card.setObjectName("noticeCard")
        settings_layout = QVBoxLayout(settings_card)
        self.settings_title = QLabel()
        self.settings_title.setObjectName("noticeTitle")
        self.language_label = QLabel()
        self.language_combo = QComboBox()
        self.language_combo.addItem("简体中文", "zh_CN")
        self.language_combo.addItem("English", "en_US")
        language_row = QHBoxLayout()
        language_row.addWidget(self.language_label)
        language_row.addWidget(self.language_combo)
        language_row.addStretch()
        settings_layout.addWidget(self.settings_title)
        settings_layout.addLayout(language_row)

        self.version = QLabel()
        self.version.setObjectName("mutedLabel")
        self.notice = QLabel()
        self.notice.setObjectName("mutedLabel")
        self.notice.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.intro)
        layout.addWidget(feature_card)
        layout.addWidget(settings_card)
        layout.addStretch()
        layout.addWidget(self.version)
        layout.addWidget(self.notice)

        self.language_combo.currentIndexChanged.connect(self._select_language)
        self.language.changed.connect(self.retranslate)
        self.retranslate()

    def _select_language(self, index: int) -> None:
        language = self.language_combo.itemData(index)
        if language:
            self.language.set_language(language)

    def retranslate(self, _language: str | None = None) -> None:
        self.title.setText(self.language.text("home.title"))
        self.subtitle.setText(self.language.text("home.subtitle"))
        self.intro.setText(self.language.text("home.intro"))
        self.features_title.setText(self.language.text("home.features_title"))
        self.features.setText(self.language.text("home.features"))
        self.settings_title.setText(self.language.text("home.settings_title"))
        self.language_label.setText(self.language.text("home.language_label"))
        self.version.setText(self.language.text("home.version", version=__version__))
        self.notice.setText(self.language.text("home.notice"))

        index = self.language_combo.findData(self.language.language)
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(index)
        self.language_combo.blockSignals(False)


class FontLibraryPage(QWidget):
    def __init__(self, store, language: LanguageManager) -> None:
        super().__init__()
        self.store = store
        self.language = language
        self.title, self.subtitle = _page_title("", "")
        self.font_list = QListWidget()
        self.font_list.setAlternatingRowColors(True)
        self.font_list.currentRowChanged.connect(self.store.select)

        self.add_button = QPushButton()
        self.add_button.setObjectName("primaryButton")
        self.add_button.clicked.connect(self._choose_fonts)

        self.summary = QLabel()
        self.summary.setObjectName("mutedLabel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addSpacing(8)
        layout.addWidget(self.add_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.font_list, 1)
        layout.addWidget(self.summary)

        self.store.fonts_changed.connect(self._refresh)
        self.store.current_changed.connect(self._show_current)
        self.language.changed.connect(self.retranslate)
        self.retranslate()

    def _choose_fonts(self) -> None:
        extensions = " ".join(f"*{suffix}" for suffix in sorted(SUPPORTED_EXTENSIONS))
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            self.language.text("font.dialog_title"),
            "",
            f"Fonts ({extensions});;All files (*)",
        )
        failures: list[str] = []
        for path in paths:
            try:
                self.store.add(path)
            except ValueError as exc:
                failures.append(f"{Path(path).name}: {exc}")
        if failures:
            QMessageBox.warning(
                self,
                self.language.text("font.warning_title"),
                "\n".join(failures),
            )

    def _refresh(self) -> None:
        selected_path = self.store.current.metadata.path if self.store.current else None
        self.font_list.blockSignals(True)
        self.font_list.clear()
        selected_row = -1
        for row, loaded in enumerate(self.store.fonts):
            item = QListWidgetItem(loaded.metadata.display_name)
            item.setToolTip(str(loaded.metadata.path))
            self.font_list.addItem(item)
            if loaded.metadata.path == selected_path:
                selected_row = row
        self.font_list.setCurrentRow(selected_row)
        self.font_list.blockSignals(False)

    def _show_current(self, loaded) -> None:
        if loaded is None:
            self.summary.setText(self.language.text("font.empty"))
            return
        self.summary.setText(
            self.language.text(
                "font.current",
                name=loaded.metadata.display_name,
                count=len(loaded.metadata.codepoints),
                path=loaded.metadata.path,
            )
        )

    def retranslate(self, _language: str | None = None) -> None:
        self.title.setText(self.language.text("font.title"))
        self.subtitle.setText(self.language.text("font.subtitle"))
        self.add_button.setText(self.language.text("font.add"))
        self._show_current(self.store.current)


class GlyphBrowserPage(QWidget):
    PAGE_SIZE = 256
    COLUMN_COUNT = 8

    def __init__(self, store, language: LanguageManager) -> None:
        super().__init__()
        self.store = store
        self.language = language
        self._matches: tuple[int, ...] = ()
        self._page = 0

        self.title, self.subtitle = _page_title("", "")
        self.search = QTextEdit()
        self.search.setAcceptRichText(False)
        self.search.setFixedHeight(52)
        self.search.textChanged.connect(self._filter)

        self.table = QTableWidget(0, self.COLUMN_COUNT)
        self.table.horizontalHeader().hide()
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)

        self.previous_button = QPushButton()
        self.next_button = QPushButton()
        self.previous_button.clicked.connect(lambda: self._move_page(-1))
        self.next_button.clicked.connect(lambda: self._move_page(1))
        self.page_label = QLabel()
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pager = QHBoxLayout()
        pager.addWidget(self.previous_button)
        pager.addStretch()
        pager.addWidget(self.page_label)
        pager.addStretch()
        pager.addWidget(self.next_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.search)
        layout.addWidget(self.table, 1)
        layout.addLayout(pager)

        self.store.current_changed.connect(self._font_changed)
        self.language.changed.connect(self.retranslate)
        self.retranslate()

    def _font_changed(self, loaded) -> None:
        self.search.clear()
        self._matches = loaded.metadata.codepoints if loaded else ()
        self._page = 0
        self._render_page()

    def _filter(self) -> None:
        loaded = self.store.current
        if loaded is None:
            self._matches = ()
        else:
            query = self.search.toPlainText().strip()
            source = loaded.metadata.codepoints
            if not query:
                self._matches = source
            elif query.upper().startswith("U+"):
                try:
                    target = int(query[2:], 16)
                except ValueError:
                    self._matches = ()
                else:
                    self._matches = (target,) if target in source else ()
            elif len(query) == 1:
                target = ord(query)
                self._matches = (target,) if target in source else ()
            else:
                needle = query.upper()
                self._matches = tuple(
                    codepoint
                    for codepoint in source
                    if needle in unicodedata.name(chr(codepoint), "")
                )
        self._page = 0
        self._render_page()

    def _move_page(self, direction: int) -> None:
        self._page += direction
        self._render_page()

    def _render_page(self) -> None:
        total = len(self._matches)
        page_count = max(1, (total + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self._page = min(max(0, self._page), page_count - 1)
        start = self._page * self.PAGE_SIZE
        visible = self._matches[start : start + self.PAGE_SIZE]
        rows = (len(visible) + self.COLUMN_COUNT - 1) // self.COLUMN_COUNT

        self.table.clearContents()
        self.table.setRowCount(rows)
        for column in range(self.COLUMN_COUNT):
            self.table.setColumnWidth(column, 104)

        loaded = self.store.current
        display_font = QFont(loaded.family if loaded else "")
        display_font.setPointSize(25)
        for offset, codepoint in enumerate(visible):
            row, column = divmod(offset, self.COLUMN_COUNT)
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(3, 5, 3, 5)
            cell_layout.setSpacing(1)

            glyph_label = QLabel(display_character(codepoint))
            glyph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            glyph_label.setFont(display_font)
            codepoint_label = QLabel(format_codepoint(codepoint))
            codepoint_label.setObjectName("codepointLabel")
            codepoint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            cell_layout.addWidget(glyph_label, 1)
            cell_layout.addWidget(codepoint_label)
            cell.setToolTip(unicodedata.name(chr(codepoint), "Unnamed character"))
            self.table.setCellWidget(row, column, cell)
            self.table.setRowHeight(row, 82)

        if loaded is None:
            self.page_label.setText(self.language.text("glyph.load_font"))
        else:
            self.page_label.setText(
                self.language.text(
                    "glyph.page",
                    page=self._page + 1,
                    pages=page_count,
                    count=total,
                )
            )
        self.previous_button.setEnabled(self._page > 0)
        self.next_button.setEnabled(self._page + 1 < page_count)

    def retranslate(self, _language: str | None = None) -> None:
        self.title.setText(self.language.text("glyph.title"))
        self.subtitle.setText(self.language.text("glyph.subtitle"))
        self.search.setPlaceholderText(self.language.text("glyph.search"))
        self.previous_button.setText(self.language.text("glyph.previous"))
        self.next_button.setText(self.language.text("glyph.next"))
        self._render_page()


class TextPreviewPage(QWidget):
    def __init__(self, store, language: LanguageManager) -> None:
        super().__init__()
        self.store = store
        self.language = language
        self.foreground = QColor("#EAF8FF")
        self.background = QColor("#102B46")

        self.title, self.subtitle = _page_title("", "")
        self.editor = QTextEdit("HoyoGraphae\n提瓦特字形实验室")
        self.editor.setAcceptRichText(False)
        self.editor.textChanged.connect(self._update_preview)

        self.size_input = QSpinBox()
        self.size_input.setRange(8, 240)
        self.size_input.setValue(72)
        self.size_input.setSuffix(" pt")
        self.size_input.valueChanged.connect(self._update_preview)

        self.foreground_button = QPushButton()
        self.background_button = QPushButton()
        self.foreground_button.clicked.connect(self._choose_foreground)
        self.background_button.clicked.connect(self._choose_background)

        self.transparent = QCheckBox()
        self.transparent.toggled.connect(self._transparency_changed)

        self.export_button = QPushButton()
        self.export_button.setObjectName("primaryButton")
        self.export_button.clicked.connect(self._export)

        controls = QHBoxLayout()
        self.size_label = QLabel()
        controls.addWidget(self.size_label)
        controls.addWidget(self.size_input)
        controls.addWidget(self.foreground_button)
        controls.addWidget(self.background_button)
        controls.addWidget(self.transparent)
        controls.addStretch()
        controls.addWidget(self.export_button)

        self.font_status = QLabel()
        self.font_status.setObjectName("mutedLabel")
        self.preview = QLabel()
        self.preview.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.preview.setObjectName("previewCanvas")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.preview)

        content = QGridLayout()
        content.setColumnStretch(0, 1)
        content.setColumnStretch(1, 2)
        content.addWidget(self.editor, 0, 0)
        content.addWidget(scroll, 0, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addLayout(controls)
        layout.addWidget(self.font_status)
        layout.addLayout(content, 1)

        self.store.current_changed.connect(self._font_changed)
        self.language.changed.connect(self.retranslate)
        self._sync_color_buttons()
        self.retranslate()

    def _font(self) -> QFont:
        font = QFont(self.store.current.family if self.store.current else "")
        font.setPointSize(self.size_input.value())
        return font

    def _render(self):
        background = None if self.transparent.isChecked() else self.background
        return render_text_image(
            self.editor.toPlainText(),
            self._font(),
            self.foreground,
            background,
            width=1000,
            padding=40,
        )

    def _font_changed(self, loaded) -> None:
        self.font_status.setText(
            self.language.text("typesetter.current_font", name=loaded.metadata.display_name)
            if loaded
            else self.language.text("typesetter.default_font")
        )
        self._update_preview()

    def _update_preview(self) -> None:
        image = self._render()
        self.preview.setPixmap(QPixmap.fromImage(image))
        self.preview.setMinimumSize(image.size())

    def _choose_foreground(self) -> None:
        color = QColorDialog.getColor(
            self.foreground,
            self,
            self.language.text("typesetter.foreground_dialog"),
        )
        if color.isValid():
            self.foreground = color
            self._sync_color_buttons()
            self._update_preview()

    def _choose_background(self) -> None:
        color = QColorDialog.getColor(
            self.background,
            self,
            self.language.text("typesetter.background_dialog"),
        )
        if color.isValid():
            self.background = color
            self._sync_color_buttons()
            self._update_preview()

    def _transparency_changed(self, transparent: bool) -> None:
        self.background_button.setEnabled(not transparent)
        self._update_preview()

    def _sync_color_buttons(self) -> None:
        self.foreground_button.setStyleSheet(f"border-bottom: 4px solid {self.foreground.name()};")
        self.background_button.setStyleSheet(f"border-bottom: 4px solid {self.background.name()};")

    def _export(self) -> None:
        if not self.editor.toPlainText():
            QMessageBox.information(
                self,
                self.language.text("typesetter.no_text_title"),
                self.language.text("typesetter.no_text"),
            )
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.language.text("typesetter.export_dialog"),
            "HoyoGraphae.png",
            "PNG image (*.png)",
        )
        if not path:
            return
        if Path(path).suffix.lower() != ".png":
            path += ".png"
        if not self._render().save(path, "PNG"):
            QMessageBox.critical(
                self,
                self.language.text("typesetter.export_error_title"),
                self.language.text("typesetter.export_error", path=path),
            )
            return
        QMessageBox.information(
            self,
            self.language.text("typesetter.export_done_title"),
            self.language.text("typesetter.export_done", path=path),
        )

    def retranslate(self, _language: str | None = None) -> None:
        self.title.setText(self.language.text("typesetter.title"))
        self.subtitle.setText(self.language.text("typesetter.subtitle"))
        self.size_label.setText(self.language.text("typesetter.size"))
        self.foreground_button.setText(self.language.text("typesetter.foreground"))
        self.background_button.setText(self.language.text("typesetter.background"))
        self.transparent.setText(self.language.text("typesetter.transparent"))
        self.export_button.setText(self.language.text("typesetter.export"))
        self._font_changed(self.store.current)


class OcrPage(QWidget):
    def __init__(self, language: LanguageManager) -> None:
        super().__init__()
        self.language = language
        self.selected_path: str | None = None
        self.title, self.subtitle = _page_title("", "")
        self.choose_button = QPushButton()
        self.choose_button.setObjectName("primaryButton")
        self.choose_button.clicked.connect(self._choose_image)

        self.path_label = QLabel()
        self.path_label.setObjectName("mutedLabel")
        self.path_label.setWordWrap(True)
        self.image_preview = QLabel()
        self.image_preview.setObjectName("imageDropZone")
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMinimumSize(560, 340)

        notice = QFrame()
        notice.setObjectName("noticeCard")
        notice_layout = QVBoxLayout(notice)
        self.notice_title = QLabel()
        self.notice_title.setObjectName("noticeTitle")
        self.notice_text = QLabel()
        self.notice_text.setWordWrap(True)
        notice_layout.addWidget(self.notice_title)
        notice_layout.addWidget(self.notice_text)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.choose_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.path_label)
        layout.addWidget(self.image_preview, 1)
        layout.addWidget(notice)

        self.language.changed.connect(self.retranslate)
        self.retranslate()

    def _choose_image(self) -> None:
        patterns = " ".join(
            f"*.{bytes(item).decode('ascii')}" for item in QImageReader.supportedImageFormats()
        )
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.language.text("ocr.dialog_title"),
            "",
            f"Images ({patterns});;All files (*)",
        )
        if not path:
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, self.language.text("ocr.read_error"), path)
            return
        self.selected_path = path
        self.path_label.setText(path)
        self.image_preview.setPixmap(
            pixmap.scaled(
                760,
                440,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def retranslate(self, _language: str | None = None) -> None:
        self.title.setText(self.language.text("ocr.title"))
        self.subtitle.setText(self.language.text("ocr.subtitle"))
        self.choose_button.setText(self.language.text("ocr.choose"))
        self.notice_title.setText(self.language.text("ocr.notice_title"))
        self.notice_text.setText(self.language.text("ocr.notice"))
        if self.selected_path is None:
            self.path_label.setText(self.language.text("ocr.no_image"))
            self.image_preview.setText(self.language.text("ocr.preview"))
