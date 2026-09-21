"""Extract the supplied frontend without redesign; only transport/event wiring changes."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def render():
    source = (ROOT / "legacy/index_original.html").read_text(encoding="utf-8")
    css = re.search(r"<style>([\s\S]*?)</style>", source).group(1)
    js = re.search(r"<script>([\s\S]*?)</script>", source).group(1)
    # Data attributes preserve the exact event arguments, without inline execution/eval.
    def events(value):
        return re.sub(r"\bon(click|input|change)=", r"data-on\1=", value)
    html = re.sub(r"<style>[\s\S]*?</style>", '<link rel="stylesheet" href="/static/css/monthly.css">', source)
    html = re.sub(r"<script>[\s\S]*?</script>",
                  '<script src="/static/js/api.js"></script>\n  <script src="/static/js/monthly.js"></script>\n  <script src="/static/js/events.js"></script>', html)
    html = html.replace("<head>", "<head>\n  <title>Inventarios Mensuales PDV</title>")
    js = events(js.replace("google.script.run", "monthlyApi"))
    # Ignore stale category responses after the user changes PDV/date quickly.
    js = js.replace("estadosCategorias = estados || [];",
                    "if (document.getElementById('puntoVenta').value !== puntoVenta ||\n"
                    "              document.getElementById('fechaInventario').value !== fecha) return;\n"
                    "          estadosCategorias = estados || [];")
    for path, content in (("app/templates/index.html", events(html)),
                          ("app/static/css/monthly.css", css), ("app/static/js/monthly.js", js)):
        target = ROOT / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    render()
