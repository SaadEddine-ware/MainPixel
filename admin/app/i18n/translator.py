import json
import os

_translations = {}
_current_lang = "fr"

_RTL_LANGS = {"ar"}


def load_language(lang):
    global _translations
    path = os.path.join(os.path.dirname(__file__), f"{lang}.json")
    if not os.path.exists(path):
        _translations = {}
        return
    with open(path, "r", encoding="utf-8") as f:
        _translations = json.load(f)


def set_language(lang):
    global _current_lang
    _current_lang = lang
    load_language(lang)


def _(key, **kwargs):
    text = _translations.get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text


def get_language():
    return _current_lang


def is_rtl():
    return _current_lang in _RTL_LANGS


def anchor(dir="w"):
    if is_rtl():
        return "e" if dir == "w" else "w" if dir == "e" else dir
    return dir


set_language("fr")
