"""Minimal i18n: same interface as admin app for compatibility."""
import json
import os

_current_lang = "fr"
_strings: dict = {}

DIR = os.path.dirname(os.path.abspath(__file__))


def _load_lang(lang: str):
    global _strings
    path = os.path.join(DIR, f"{lang}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            _strings = json.load(f)
    except Exception:
        _strings = {}


def set_language(lang: str):
    global _current_lang
    _current_lang = lang
    _load_lang(lang)


def get_language() -> str:
    return _current_lang


def _(key: str, **kwargs) -> str:
    val = _strings.get(key, key)
    if kwargs:
        try:
            val = val.format(**kwargs)
        except KeyError:
            pass
    return val


def anchor(dir="w"):
    return "e" if _current_lang == "ar" else "w"


# Load default
_load_lang(_current_lang)
