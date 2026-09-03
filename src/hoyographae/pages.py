"""The four Qt Widgets pages used by the desktop MVP."""

from __future__ import annotations

import unicodedata
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QImageReader, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
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

from .fonts import SUPPORTED_EXTENSIONS, display_character, format_codepoint
from .rendering import render_text_image


def _page_title(title: str, subtitle: str) -> tuple[QLabel, QLabel]:
    heading = QLabel(title)
    heading.setObjectName("pageTitle")
    detail = QLabel(subtitle)
    detail.setObjectName("pageSubtitle")
    detail.setWordWrap(True)
    return heading, detail


class FontLibraryPage(QWidget):
    def __init__(self, store) -> None:
        super().__init__()
        self.store = store
        title, subtitle = _page_title(
            "字体库 · Font Library",
            "载入本机字体文件。文件只在当前会话中读取，不会被复制或修改。",
        )
        self.font_list = QListWidget()
        self.font_list.setAlternatingRowColors(True)
        self.font_list.currentRowChanged.connect(self.store.select)

        add_button = QPushButton("＋ 选择字体文件")
        add_button.setObjectName("primaryButton")
        add_button.clicked.connect(self._choose_fonts)

        self.summary = QLabel("尚未载入字体")
        self.summary.setObjectName("mutedLabel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addSpacing(8)
        layout.addWidget(add_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.font_list, 1)
        layout.addWidget(self.summary)

        self.store.fonts_changed.connect(self._refresh)
        self.store.current_changed.connect(self._show_current)

    def _choose_fonts(self) -> None:
        extensions = " ".join(f"*{suffix}" for suffix in sorted(SUPPORTED_EXTENSIONS))
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "选择字体文件",
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
            QMessageBox.warning(self, "部分字体未载入", "\n".join(failures))

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
            self.summary.setText("尚未载入字体")
            return
        self.summary.setText(
            f"当前：{loaded.metadata.display_name}  ·  "
            f"{len(loaded.metadata.codepoints):,} 个 Unicode 映射\n{loaded.metadata.path}"
        )


class GlyphBrowserPage(QWidget):
    PAGE_SIZE = 256
    COLUMN_COUNT = 8

    def __init__(self, store) -> None:
        super().__init__()
        self.store = store
        self._matches: tuple[int, ...] = ()
        self._page = 0

        title, subtitle = _page_title(
            "字形查阅 · Glyph Browser",
            "通过 fontTools 读取 cmap。可输入字符、U+编号或 Unicode 名称筛选。",
        )
        self.search = QTextEdit()
        self.search.setAcceptRichText(False)
        self.search.setPlaceholderText("筛选，例如：星、U+0041、LATIN CAPITAL")
        self.search.setFixedHeight(52)
        self.search.textChanged.connect(self._filter)

        self.table = QTableWidget(0, self.COLUMN_COUNT)
        self.table.horizontalHeader().hide()
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setShowGrid(False)

        self.previous_button = QPushButton("← 上一页")
        self.next_button = QPushButton("下一页 →")
        self.previous_button.clicked.connect(lambda: self._move_page(-1))
        self.next_button.clicked.connect(lambda: self._move_page(1))
        self.page_label = QLabel("请选择字体")
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
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self.search)
        layout.addWidget(self.table, 1)
        layout.addLayout(pager)

        self.store.current_changed.connect(self._font_changed)
        self._render_page()

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
            self.page_label.setText("请先在字体库中载入字体")
        else:
            self.page_label.setText(f"第 {self._page + 1} / {page_count} 页 · {total:,} 项")
        self.previous_button.setEnabled(self._page > 0)
        self.next_button.setEnabled(self._page + 1 < page_count)


class TextPreviewPage(QWidget):
    def __init__(self, store) -> None:
        super().__init__()
        self.store = store
        self.foreground = QColor("#EAF8FF")
        self.background = QColor("#102B46")

        title, subtitle = _page_title(
            "实时打字 · Live Typesetter",
            "键盘输入会使用当前字体实时排版，并可导出透明或纯色背景 PNG。",
        )
        self.editor = QTextEdit("HoyoGraphae\n提瓦特字形实验室")
        self.editor.setAcceptRichText(False)
        self.editor.textChanged.connect(self._update_preview)

        self.size_input = QSpinBox()
        self.size_input.setRange(8, 240)
        self.size_input.setValue(72)
        self.size_input.setSuffix(" pt")
        self.size_input.valueChanged.connect(self._update_preview)

        self.foreground_button = QPushButton("文字颜色")
        self.background_button = QPushButton("背景颜色")
        self.foreground_button.clicked.connect(self._choose_foreground)
        self.background_button.clicked.connect(self._choose_background)

        self.transparent = QCheckBox("透明背景")
        self.transparent.toggled.connect(self._transparency_changed)

        export_button = QPushButton("导出 PNG")
        export_button.setObjectName("primaryButton")
        export_button.clicked.connect(self._export)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("字号"))
        controls.addWidget(self.size_input)
        controls.addWidget(self.foreground_button)
        controls.addWidget(self.background_button)
        controls.addWidget(self.transparent)
        controls.addStretch()
        controls.addWidget(export_button)

        self.font_status = QLabel("当前使用系统默认字体")
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
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(controls)
        layout.addWidget(self.font_status)
        layout.addLayout(content, 1)

        self.store.current_changed.connect(self._font_changed)
        self._sync_color_buttons()
        self._update_preview()

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
            f"当前字体：{loaded.metadata.display_name}" if loaded else "当前使用系统默认字体"
        )
        self._update_preview()

    def _update_preview(self) -> None:
        image = self._render()
        self.preview.setPixmap(QPixmap.fromImage(image))
        self.preview.setMinimumSize(image.size())

    def _choose_foreground(self) -> None:
        color = QColorDialog.getColor(self.foreground, self, "选择文字颜色")
        if color.isValid():
            self.foreground = color
            self._sync_color_buttons()
            self._update_preview()

    def _choose_background(self) -> None:
        color = QColorDialog.getColor(self.background, self, "选择背景颜色")
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
            QMessageBox.information(self, "没有文本", "请先输入要导出的文本。")
            return
        path, _ = QFileDialog.getSaveFileName(self, "导出 PNG", "HoyoGraphae.png", "PNG image (*.png)")
        if not path:
            return
        if Path(path).suffix.lower() != ".png":
            path += ".png"
        if not self._render().save(path, "PNG"):
            QMessageBox.critical(self, "导出失败", f"无法写入：{path}")
            return
        QMessageBox.information(self, "导出完成", f"PNG 已保存：\n{path}")


class OcrPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        title, subtitle = _page_title(
            "图片文字识别 · Image OCR",
            "选择图片用于后续识别流程。当前 MVP 尚未包含 OCR 推理模型。",
        )
        choose_button = QPushButton("选择图片")
        choose_button.setObjectName("primaryButton")
        choose_button.clicked.connect(self._choose_image)

        self.path_label = QLabel("尚未选择图片")
        self.path_label.setObjectName("mutedLabel")
        self.path_label.setWordWrap(True)
        self.image_preview = QLabel("图片预览")
        self.image_preview.setObjectName("imageDropZone")
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setMinimumSize(560, 340)

        notice = QFrame()
        notice.setObjectName("noticeCard")
        notice_layout = QVBoxLayout(notice)
        notice_title = QLabel("OCR 模型尚未接入")
        notice_title.setObjectName("noticeTitle")
        notice_text = QLabel(
            "OCR model is not connected yet. 当前版本不会生成、猜测或伪造识别结果；"
            "后续将从明确选定的本地模型接入。"
        )
        notice_text.setWordWrap(True)
        notice_layout.addWidget(notice_title)
        notice_layout.addWidget(notice_text)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(choose_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.path_label)
        layout.addWidget(self.image_preview, 1)
        layout.addWidget(notice)

    def _choose_image(self) -> None:
        patterns = " ".join(
            f"*.{bytes(item).decode('ascii')}" for item in QImageReader.supportedImageFormats()
        )
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择待识别图片",
            "",
            f"Images ({patterns});;All files (*)",
        )
        if not path:
            return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.warning(self, "无法读取图片", path)
            return
        self.path_label.setText(path)
        self.image_preview.setPixmap(
            pixmap.scaled(
                760,
                440,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
