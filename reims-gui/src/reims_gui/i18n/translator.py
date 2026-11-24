from __future__ import annotations
import json
import locale
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class Translator:
    """Manages translations and language switching."""

    _instance: Optional[Translator] = None

    def __init__(self, default_lang: Optional[str] = None):
        self.locales_dir = Path(__file__).parent / "locales"
        self._current_lang = default_lang or self._detect_system_language()
        self._translations: Dict[str, Dict[str, str]] = {}
        self._observers: List[Callable[[str], None]] = []
        self._load_all_languages()

    @classmethod
    def get_instance(cls) -> Translator:
        if cls._instance is None:
            cls._instance = Translator()
        return cls._instance

    def _detect_system_language(self) -> str:
        try:
            sys_lang = os.environ.get("LANG") or (locale.getlocale()[0] if hasattr(locale, "getlocale") else None)
            if sys_lang:
                if sys_lang.startswith("pt"):
                    return "pt_BR"
                elif sys_lang.startswith("es"):
                    return "es_ES"
        except Exception:
            pass
        return "pt_BR"  # Default to pt_BR on ReimsOS

    def _load_all_languages(self) -> None:
        for file in self.locales_dir.glob("*.json"):
            lang_code = file.stem
            try:
                with open(file, "r", encoding="utf-8") as f:
                    self._translations[lang_code] = json.load(f)
            except Exception as e:
                logger.error(f"Error loading locale {lang_code}: {e}")

    @property
    def current_language(self) -> str:
        return self._current_lang

    def set_language(self, lang_code: str) -> None:
        if lang_code in self._translations:
            self._current_lang = lang_code
            for observer in self._observers:
                observer(lang_code)

    def subscribe(self, callback: Callable[[str], None]) -> None:
        if callback not in self._observers:
            self._observers.append(callback)

    def translate(self, key: str, **kwargs) -> str:
        dict_data = self._translations.get(self._current_lang, {})
        val = dict_data.get(key)
        if val is None:
            # Fallback to pt_BR or en_US or return key
            fallback_dict = self._translations.get("en_US", {})
            val = fallback_dict.get(key, key)
        if kwargs:
            try:
                return val.format(**kwargs)
            except Exception:
                return val
        return val


def t(key: str, **kwargs) -> str:
    """Helper shortcut for translate."""
    return Translator.get_instance().translate(key, **kwargs)
