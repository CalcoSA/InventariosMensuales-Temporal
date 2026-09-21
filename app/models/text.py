"""JavaScript-compatible primitives used by the legacy (not generic normalization)."""
import ctypes
import ctypes.util
import math
import re
import sys
import unicodedata
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP, localcontext
from functools import lru_cache
from threading import RLock
from app.models.errors import ConfigurationError, DomainError


def js_string(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        if value == int(value):
            return str(int(value))
    return str(value)


def clean(value):
    return js_string(value).strip()


def accents(value):
    return re.sub("[\u0300-\u036f]", "", unicodedata.normalize("NFD", js_string(value)))


def normalize(value):
    return re.sub(r"\s+", " ", accents(value or "")).strip().lower()


def generator_normalize(value):
    return re.sub(r"[^A-Z0-9]+", " ", accents(value).upper()).strip()


def product_key(product):
    return "\x1f".join(normalize(product.get(k)) for k in ("item", "producto", "udm"))


def date_key(value):
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    text = clean(value or "")
    match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text, re.ASCII)
    if match:
        day, month, year = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return text


def valid_date(value):
    key = date_key(value)
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", key, re.ASCII):
            raise ValueError
        date.fromisoformat(key)
    except (ValueError, TypeError):
        raise DomainError("Seleccione una fecha de inventario válida.") from None
    return key


def safe_filename(value):
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", accents(value or "")).strip("_")


def js_number(value):
    if isinstance(value, (int, float)):
        return float(value)
    text = clean(value)
    if not text:
        return 0.0
    try:
        if re.fullmatch(r"0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+", text):
            return float(int(text, 0))
        if not re.fullmatch(r"[+-]?(?:(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?|Infinity)", text, re.ASCII):
            return math.nan
        return float(text)
    except (ValueError, OverflowError):
        return math.nan


def parse_number(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    text = re.sub(r"\s", "", clean(value))
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".", 1) if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".", 1)
    return js_number(text)


def js_fixed(value, digits=15):
    # Number.toFixed rounds the exact binary64 value, ties away from zero.
    if value == 0:
        value = 0.0
    with localcontext() as context:
        context.prec = 400
        return format(Decimal.from_float(float(value)).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP), f".{digits}f")


def rounded_count(value):
    return math.floor((float(value) + sys.float_info.epsilon) * 1000000 + 0.5) / 1000000


class SpanishCollation:
    """ICU es locale, the same collation family as JS Intl; never process-global locale."""
    def __init__(self, numeric=False):
        library = "icu.dll" if sys.platform == "win32" else ctypes.util.find_library("icui18n")
        try:
            self.lib = ctypes.CDLL(library or "libicui18n.so")
            def symbol(name):
                for suffix in [""] + [f"_{n}" for n in range(100, 49, -1)]:
                    try:
                        return getattr(self.lib, name + suffix)
                    except AttributeError:
                        pass
                raise OSError("ICU symbol missing")
            opener = symbol("ucol_open")
            opener.argtypes = [ctypes.c_char_p, ctypes.POINTER(ctypes.c_int)]
            opener.restype = ctypes.c_void_p
            status = ctypes.c_int(0)
            self.collator = opener(b"es", ctypes.byref(status))
            if status.value > 0 or not self.collator:
                raise OSError("ICU locale unavailable")
            setter = symbol("ucol_setAttribute")
            setter.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
            if numeric:
                setter(self.collator, 7, 17, ctypes.byref(status))
            self.sorter = symbol("ucol_getSortKey")
            self.sorter.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
            self.sorter.restype = ctypes.c_int
            self.lock = RLock()
        except (OSError, AttributeError):
            raise ConfigurationError("No está disponible ICU para ordenar en español. Instale la biblioteca ICU del sistema.") from None

    def key(self, value):
        data = js_string(value).encode("utf-16-le")
        source = ctypes.create_string_buffer(data)
        with self.lock:
            size = self.sorter(self.collator, source, len(data) // 2, None, 0)
            dest = ctypes.create_string_buffer(size)
            self.sorter(self.collator, source, len(data) // 2, dest, size)
            return dest.raw


@lru_cache(maxsize=2)
def collator(numeric=False):
    return SpanishCollation(numeric)


def spanish_key(value, numeric=False):
    return collator(numeric).key(value)
