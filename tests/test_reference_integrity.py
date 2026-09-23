import hashlib
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent


def test_legacy_hashes():
    for name,digest in json.loads((ROOT/"legacy/SHA256.json").read_text()).items():
        assert hashlib.sha256((ROOT/"legacy"/name).read_bytes()).hexdigest()==digest


def test_css_and_all_frontend_functions_preserved():
    original=(ROOT/"legacy/index_original.html").read_text(encoding="utf-8")
    css=re.search(r"<style>([\s\S]*?)</style>",original).group(1)
    assert (ROOT/"app/static/css/monthly.css").read_text(encoding="utf-8")==css
    script=(ROOT/"app/static/js/monthly.js").read_text(encoding="utf-8")
    legacy_functions = re.findall(r"\bfunction (\w+)\(",original)
    current_functions = re.findall(r"\bfunction (\w+)\(",script)
    assert legacy_functions == [name for name in current_functions if name in legacy_functions]
    assert set(current_functions) - set(legacy_functions) == {"clavesBorradorPara", "leerBorradorPara"}
    assert "google.script.run" not in script
