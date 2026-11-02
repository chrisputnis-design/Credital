"""Build web/index.html: inlines poker.js + data (preflop table, tuned params) into the template.

    python -m pokerbot.web.build
"""
import json
import pathlib

from ..basic_bot import DEFAULT_PARAMS, ORIGINAL_PARAMS
from ..preflop_table import PREFLOP_EQUITY

HERE = pathlib.Path(__file__).parent


def data_json():
    return json.dumps({"preflop": PREFLOP_EQUITY, "params": DEFAULT_PARAMS, "original": ORIGINAL_PARAMS})


def main():
    html = (HERE / "template.html").read_text()
    html = html.replace("/*POKER_JS*/", (HERE / "poker.js").read_text())
    html = html.replace("/*POKER_DATA*/null", data_json())
    (HERE / "index.html").write_text(html)
    (HERE / "data.json").write_text(data_json())
    print("wrote", HERE / "index.html", f"({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
