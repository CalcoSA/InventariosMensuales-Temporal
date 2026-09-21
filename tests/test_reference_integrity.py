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
    assert re.findall(r"\bfunction (\w+)\(",original)==re.findall(r"\bfunction (\w+)\(",script)
    assert "google.script.run" not in script


def test_all_legacy_functions_documented():
    parity=(ROOT/"MIGRATION_PARITY.md").read_text(encoding="utf-8")
    for filename in ("generador_inventario_mensual.gs","inventarios_mensuales_pdv.gs","index_original.html"):
        source=(ROOT/"legacy"/filename).read_text(encoding="utf-8")
        for name in re.findall(r"\bfunction (\w+)\(",source):
            assert f"\x60{name}\x60" in parity,name
