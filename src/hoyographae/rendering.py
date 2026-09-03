"""Render typed text to a PNG-ready Qt image."""

from __future__ import annotations

from math import ceil

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QTextCharFormat, QTextCursor, QTextDocument


def render_text_image(
    text: str,
    font: QFont,
    foreground: QColor,
    background: QColor | None,
    *,
    width: int = 1200,
    padding: int = 48,
) -> QImage:
    """Return an ARGB image whose background may be fully transparent."""

    usable_width = max(1, width - padding * 2)
    document = QTextDocument()
    document.setDocumentMargin(0)
    document.setDefaultFont(font)
    document.setPlainText(text or " ")
    document.setTextWidth(usable_width)

    cursor = QTextCursor(document)
    cursor.select(QTextCursor.SelectionType.Document)
    character_format = QTextCharFormat()
    character_format.setForeground(foreground)
    cursor.mergeCharFormat(character_format)

    height = max(1, ceil(document.size().height()) + padding * 2)
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(background.rgba() if background is not None else Qt.GlobalColor.transparent)

    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    painter.translate(padding, padding)
    document.drawContents(painter)
    painter.end()
    return image

