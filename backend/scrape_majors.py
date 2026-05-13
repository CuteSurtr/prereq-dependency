"""Scrape UCSD's undergraduate major plan codes from Blink.

The page at https://blink.ucsd.edu/instructors/academic-info/majors/major-codes.html
is the registrar-maintained source of truth for the 4-character codes that
appear in catalog restrictions like "Restricted to CS25, CS26, CS27, and CS29
majors only." Each row gives a code, the full major name, and the home
department.

Output is written to frontend/public/majors.json so the frontend can render
a dropdown without needing to know any major codes ahead of time.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import httpx
from selectolax.parser import HTMLParser

URL = "https://blink.ucsd.edu/instructors/academic-info/majors/major-codes.html"
USER_AGENT = "prereq-dependency-scraper/1.0 (github.com/CuteSurtr/prereq-dependency)"
OUT_PATH = Path(__file__).parent.parent / "frontend" / "public" / "majors.json"

_CODE_RE = re.compile(r"^[A-Z]{2}\d{2}$|^[A-Z]{4}$")


def fetch(url: str = URL) -> str:
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        r = client.get(url, headers={"User-Agent": USER_AGENT})
        r.raise_for_status()
        return r.text


def parse_table(html: str) -> list[dict[str, str]]:
    """Walk every <tr> on the page and keep rows that look like
    (code, major name, department).

    The Blink table groups majors by department with a rowspan'd first cell.
    A "header" row carries 5 cells: dept | degreed-flag | ISIS code | TSS
    code | name. Subsequent rows in the same dept group carry only 4 cells
    (the dept cell is the rowspan'd one above). We latch the most-recent
    department text and apply it to the rows that follow.
    """
    tree = HTMLParser(html)
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    current_dept = ""

    for tr in tree.css("tr"):
        cells = [c.text(strip=True).replace("\xa0", " ").strip() for c in tr.css("td")]
        if len(cells) == 5:
            current_dept = cells[0] or current_dept
            code, name = cells[2], cells[4]
        elif len(cells) == 4:
            code, name = cells[1], cells[3]
        else:
            continue

        code = code.upper().replace(" ", "")
        if not _CODE_RE.match(code) or not name or not current_dept:
            continue
        key = (code, name, current_dept)
        if key in seen:
            continue
        seen.add(key)
        out.append({"code": code, "name": name, "department": current_dept})

    return out


def main() -> int:
    html = fetch()
    rows = parse_table(html)
    if not rows:
        print("warning: no rows parsed; the Blink page layout may have changed.")
        return 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(rows, indent=2), encoding="utf-8")

    by_dept: dict[str, int] = {}
    for r in rows:
        by_dept[r["department"]] = by_dept.get(r["department"], 0) + 1

    print(f"wrote {len(rows)} majors across {len(by_dept)} departments to {OUT_PATH}")
    print(f"bytes: {OUT_PATH.stat().st_size}")
    top = sorted(by_dept.items(), key=lambda kv: -kv[1])[:6]
    print("top departments:")
    for dept, n in top:
        print(f"  {n:>3}  {dept}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
