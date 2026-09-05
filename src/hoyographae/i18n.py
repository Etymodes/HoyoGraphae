"""Small runtime translation service for the desktop application."""

from __future__ import annotations

from PySide6.QtCore import QObject, QSettings, Signal


DEFAULT_LANGUAGE = "zh_CN"
SUPPORTED_LANGUAGES = ("zh_CN", "en_US")
SETTINGS_KEY = "interface/language"

TRANSLATIONS = {
    "zh_CN": {
        "app.tagline": "字形与文字实验室",
        "nav.home": "首页",
        "nav.font_library": "字体管理",
        "nav.glyphs": "字形查阅",
        "nav.typesetter": "实时打字",
        "nav.ocr": "图片识别",
        "home.title": "HoyoGraphae",
        "home.subtitle": "米哈游游戏架空文字综合工作台",
        "home.intro": (
            "集中查阅、输入和导出游戏中的人工重建架空文字。"
            "项目已内置首批字体，并将逐步加入组合式书写系统和专用 OCR。"
        ),
        "home.features_title": "主要功能",
        "home.features": "字体管理 · 字形正反查 · 实时排版与图片导出 · 图片文字识别",
        "home.settings_title": "设置",
        "home.language_label": "应用语言",
        "home.version": "当前版本：{version}",
        "home.notice": "非官方同人项目，与米哈游及其关联方没有隶属、赞助或背书关系。",
        "font.title": "字体管理",
        "font.subtitle": "只读显示应用内置字体与加载状态；按游戏整理的目录界面将在后续切片替换当前列表。",
        "font.empty": "没有可用的内置字体",
        "font.inventory": "已载入 {count} 个内置字体；仅供应用当前进程使用，不会自动安装到 Windows。",
        "font.load_failures": "内置字体载入失败：{count} 项",
        "font.qt_load_error": "Qt 无法载入该字体用于屏幕预览",
        "font.family_error": "字体没有可用的 family 名称",
        "glyph.title": "字形查阅",
        "glyph.subtitle": "将普通输入字符与所选架空字体中的字形并列查阅。",
        "glyph.font": "查阅字体",
        "glyph.search": "按输入字符筛选，例如：A",
        "glyph.previous": "← 上一页",
        "glyph.next": "下一页 →",
        "glyph.load_font": "没有可用的内置字体",
        "glyph.page": "第 {page} / {pages} 页 · {count:,} 项",
        "typesetter.title": "实时打字",
        "typesetter.subtitle": "键盘输入会使用当前字体实时排版，并可导出透明或纯色背景 PNG。",
        "typesetter.size": "字号",
        "typesetter.foreground": "文字颜色",
        "typesetter.background": "背景颜色",
        "typesetter.transparent": "透明背景",
        "typesetter.export": "导出 PNG",
        "typesetter.default_font": "没有可用的内置字体；当前使用系统默认字体",
        "typesetter.current_font": "当前字体：{name}",
        "typesetter.foreground_dialog": "选择文字颜色",
        "typesetter.background_dialog": "选择背景颜色",
        "typesetter.no_text_title": "没有文本",
        "typesetter.no_text": "请先输入要导出的文本。",
        "typesetter.export_dialog": "导出 PNG",
        "typesetter.export_error_title": "导出失败",
        "typesetter.export_error": "无法写入：{path}",
        "typesetter.export_done_title": "导出完成",
        "typesetter.export_done": "PNG 已保存：\n{path}",
        "ocr.title": "图片文字识别",
        "ocr.subtitle": "选择图片用于后续识别流程；当前版本尚未包含 OCR 推理模型。",
        "ocr.choose": "选择图片",
        "ocr.no_image": "尚未选择图片",
        "ocr.preview": "图片预览",
        "ocr.notice_title": "OCR 模型尚未接入",
        "ocr.notice": "当前版本不会生成、猜测或伪造识别结果；后续将接入明确选定的本地模型。",
        "ocr.dialog_title": "选择待识别图片",
        "ocr.read_error": "无法读取图片",
    },
    "en_US": {
        "app.tagline": "Glyph & Script Studio",
        "nav.home": "Home",
        "nav.font_library": "Font Library",
        "nav.glyphs": "Glyph Browser",
        "nav.typesetter": "Live Typesetter",
        "nav.ocr": "Image OCR",
        "home.title": "HoyoGraphae",
        "home.subtitle": "A constructed-script workbench for HoyoVerse games",
        "home.intro": (
            "Browse, type, and export fan-reconstructed scripts from the games. "
            "The first fonts are bundled; compositional writing systems and dedicated OCR will be added incrementally."
        ),
        "home.features_title": "Core features",
        "home.features": "Font library · Bidirectional glyph lookup · Live typesetting and image export · Image OCR",
        "home.settings_title": "Settings",
        "home.language_label": "Application language",
        "home.version": "Current version: {version}",
        "home.notice": "An unofficial fan project not affiliated with, sponsored by, or endorsed by HoyoVerse.",
        "font.title": "Font Library",
        "font.subtitle": "Read-only inventory and load status for bundled fonts; a game-organized catalog will replace this list in a later slice.",
        "font.empty": "No bundled font is available",
        "font.inventory": "{count} bundled fonts loaded for this application process; they are not installed into Windows automatically.",
        "font.load_failures": "Bundled fonts that failed to load: {count}",
        "font.qt_load_error": "Qt could not load this font for preview",
        "font.family_error": "The font has no usable family name",
        "glyph.title": "Glyph Browser",
        "glyph.subtitle": "Compare ordinary input characters with their glyphs in the selected constructed-script font.",
        "glyph.font": "Browse font",
        "glyph.search": "Filter by an input character, for example: A",
        "glyph.previous": "← Previous",
        "glyph.next": "Next →",
        "glyph.load_font": "No bundled font is available",
        "glyph.page": "Page {page} / {pages} · {count:,} items",
        "typesetter.title": "Live Typesetter",
        "typesetter.subtitle": "Type with the current font and export a PNG with a transparent or solid background.",
        "typesetter.size": "Size",
        "typesetter.foreground": "Text color",
        "typesetter.background": "Background color",
        "typesetter.transparent": "Transparent background",
        "typesetter.export": "Export PNG",
        "typesetter.default_font": "No bundled font is available; using the system default font",
        "typesetter.current_font": "Current font: {name}",
        "typesetter.foreground_dialog": "Choose text color",
        "typesetter.background_dialog": "Choose background color",
        "typesetter.no_text_title": "No text",
        "typesetter.no_text": "Enter some text before exporting.",
        "typesetter.export_dialog": "Export PNG",
        "typesetter.export_error_title": "Export failed",
        "typesetter.export_error": "Could not write: {path}",
        "typesetter.export_done_title": "Export complete",
        "typesetter.export_done": "PNG saved to:\n{path}",
        "ocr.title": "Image OCR",
        "ocr.subtitle": "Choose an image for the future recognition workflow; this version has no OCR inference model.",
        "ocr.choose": "Choose image",
        "ocr.no_image": "No image selected",
        "ocr.preview": "Image preview",
        "ocr.notice_title": "OCR model not connected",
        "ocr.notice": "This version does not generate, guess, or fabricate recognition results. A selected local model will be connected later.",
        "ocr.dialog_title": "Choose an image to recognize",
        "ocr.read_error": "Could not read image",
    },
}


class LanguageManager(QObject):
    """Translate UI strings and persist the selected language."""

    changed = Signal(str)

    def __init__(self, settings: QSettings | None = None) -> None:
        super().__init__()
        self.settings = settings if settings is not None else QSettings()
        stored = str(self.settings.value(SETTINGS_KEY, DEFAULT_LANGUAGE))
        self._language = stored if stored in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE

    @property
    def language(self) -> str:
        return self._language

    def set_language(self, language: str) -> None:
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")
        if language == self._language:
            return
        self._language = language
        self.settings.setValue(SETTINGS_KEY, language)
        self.settings.sync()
        self.changed.emit(language)

    def text(self, key: str, **values: object) -> str:
        text = TRANSLATIONS[self._language][key]
        return text.format(**values) if values else text
