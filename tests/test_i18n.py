from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from hoyographae.i18n import LanguageManager, TRANSLATIONS


def _settings(path: Path) -> QSettings:
    return QSettings(str(path), QSettings.Format.IniFormat)


def test_language_defaults_to_simplified_chinese(tmp_path: Path) -> None:
    manager = LanguageManager(_settings(tmp_path / "settings.ini"))

    assert manager.language == "zh_CN"
    assert manager.text("nav.home") == "首页"


def test_language_change_is_emitted_and_persisted(tmp_path: Path) -> None:
    path = tmp_path / "settings.ini"
    manager = LanguageManager(_settings(path))
    changes: list[str] = []
    manager.changed.connect(changes.append)

    manager.set_language("en_US")

    assert changes == ["en_US"]
    assert manager.text("nav.home") == "Home"
    assert LanguageManager(_settings(path)).language == "en_US"


def test_unknown_language_is_rejected(tmp_path: Path) -> None:
    manager = LanguageManager(_settings(tmp_path / "settings.ini"))

    with pytest.raises(ValueError, match="Unsupported language"):
        manager.set_language("ja_JP")


def test_translation_catalogs_have_the_same_keys() -> None:
    assert set(TRANSLATIONS["zh_CN"]) == set(TRANSLATIONS["en_US"])
