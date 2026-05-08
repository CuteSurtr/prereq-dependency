"""Scrape course pages from catalog.ucsd.edu.

One page per department (e.g. https://catalog.ucsd.edu/courses/MATH.html).
Polite: 1 request/second, on-disk HTML cache so reruns hit the cache.

Outputs a list of `ScrapedCourse` dicts to a JSON file under data/raw/.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import httpx
from selectolax.parser import HTMLParser

DATA_ROOT = Path(__file__).parent.parent / "data"
CACHE_DIR = DATA_ROOT / "cache"
RAW_DIR = DATA_ROOT / "raw"

USER_AGENT = (
    "ucsd-prereq-graph-scraper/0.1 "
    "(educational; contact 133225877+CuteSurtr@users.noreply.github.com)"
)

# Catalog URL keys we scrape. UCSD lumps all bio subject codes (BILD, BIBC,
# BICD, BIEB, BIMM, BIPN) onto BIOL.html — the per-course subject is recovered
# from each course code (e.g. "BICD 100" -> department="BICD").
SCRAPED_CATALOGS: tuple[str, ...] = (
    "MATH",
    "PHYS",
    "CHEM",
    "BIOL",  # contains BILD/BIBC/BICD/BIEB/BIMM/BIPN
    "CSE",
    "ECE",
    "MAE",
    "BENG",  # Bioengineering
    "NANO",  # NanoEngineering
    "SE",    # Structural Engineering
    "ECON",  # Economics
    "DSC",   # Data Science
    "COGS",  # Cognitive Science
)


@dataclass
class ScrapedCourse:
    code: str
    department: str
    title: str
    units: str | None
    description: str
    raw_prereq_text: str | None


def _cache_path(department: str) -> Path:
    return CACHE_DIR / f"{department}.html"


def _raw_path(department: str) -> Path:
    return RAW_DIR / f"{department}.json"


def fetch(department: str, *, force: bool = False, client: httpx.Client | None = None) -> str:
    """Fetch a department's catalog HTML, caching to disk. Polite ~1 req/sec."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = _cache_path(department)
    if cache.exists() and not force:
        return cache.read_text(encoding="utf-8")

    url = f"https://catalog.ucsd.edu/courses/{department}.html"
    own = False
    if client is None:
        client = httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=30.0,
            follow_redirects=True,
        )
        own = True
    try:
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text
        cache.write_text(html, encoding="utf-8")
        return html
    finally:
        if own:
            client.close()


# Course-name pattern, e.g. "MATH 20A. Calculus for Science and Engineering (4)"
# Code is dept + space + number that may end in a letter (and optional trailing letter for honors).
_COURSE_HEADER_RE = re.compile(
    r"""^\s*
        (?P<code>[A-Z]{2,5}\s+\d+[A-Z]{0,3})  # MATH 20A, CSE 11, BIEB 121, BENG 100D
        \.?\s+
        (?P<title>.+?)
        \s*\((?P<units>[^)]+)\)
        \s*$
    """,
    re.X,
)

_PREREQ_MARKER_RE = re.compile(
    r"<strong[^>]*>\s*<em[^>]*>\s*Prerequisites?\s*:?\s*</em>\s*</strong>", re.I
)


def _strip_html(s: str) -> str:
    return HTMLParser(s).text(separator=" ").strip()


def _split_description_and_prereq(html_inner: str) -> tuple[str, str | None]:
    """Description and prereq text live in the same `course-descriptions` <p>,
    separated by a `<strong><em>Prerequisites:</em></strong>` marker.

    Returns (description_text, prereq_text_or_None).
    """
    match = _PREREQ_MARKER_RE.search(html_inner)
    if not match:
        return _strip_html(html_inner), None
    desc = html_inner[: match.start()]
    prereq = html_inner[match.end() :]
    return _strip_html(desc), _strip_html(prereq) or None


def parse_department_html(_url_key: str, html: str) -> list[ScrapedCourse]:
    tree = HTMLParser(html)
    courses: list[ScrapedCourse] = []

    name_nodes = tree.css("p.course-name")
    desc_nodes = tree.css("p.course-descriptions")

    for name_node, desc_node in zip(name_nodes, desc_nodes, strict=False):
        header = name_node.text(strip=True)
        m = _COURSE_HEADER_RE.match(header)
        if not m:
            continue
        code = re.sub(r"\s+", " ", m.group("code")).strip().upper()
        # Subject code lives at the front of the course code, not the URL key
        # (the BIOL.html page contains BILD/BIBC/BICD/BIEB/BIMM/BIPN courses).
        subject = code.split()[0]
        title = m.group("title").strip().rstrip(".")
        units = m.group("units").strip()

        desc, prereq_text = _split_description_and_prereq(desc_node.html or "")

        courses.append(
            ScrapedCourse(
                code=code,
                department=subject,
                title=title,
                units=units,
                description=desc,
                raw_prereq_text=prereq_text,
            )
        )

    return courses


def scrape(department: str, *, force: bool = False) -> list[ScrapedCourse]:
    html = fetch(department, force=force)
    courses = parse_department_html(department, html)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    _raw_path(department).write_text(
        json.dumps([asdict(c) for c in courses], indent=2),
        encoding="utf-8",
    )
    return courses


def scrape_many(departments: list[str], *, force: bool = False, sleep: float = 1.0) -> int:
    total = 0
    with httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        for i, dept in enumerate(departments):
            cache_hit = _cache_path(dept).exists() and not force
            try:
                html = fetch(dept, force=force, client=client)
            except httpx.HTTPStatusError as e:
                print(f"  {dept:>5}: SKIP ({e.response.status_code})")
                if not cache_hit and i < len(departments) - 1:
                    time.sleep(sleep)
                continue
            courses = parse_department_html(dept, html)
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            _raw_path(dept).write_text(
                json.dumps([asdict(c) for c in courses], indent=2),
                encoding="utf-8",
            )
            total += len(courses)
            print(f"  {dept:>5}: {len(courses):>4} courses ({'cached' if cache_hit else 'fetched'})")
            if not cache_hit and i < len(departments) - 1:
                time.sleep(sleep)
    return total


def main() -> None:
    ap = argparse.ArgumentParser(description="Scrape UCSD catalog department pages.")
    ap.add_argument(
        "departments",
        nargs="*",
        help="Department codes (e.g. MATH CSE). Default: all configured catalogs.",
    )
    ap.add_argument("--force", action="store_true", help="Bypass disk cache.")
    args = ap.parse_args()

    depts = [d.upper() for d in args.departments] or list(SCRAPED_CATALOGS)
    print(f"Scraping {len(depts)} department(s): {', '.join(depts)}")
    total = scrape_many(depts, force=args.force)
    print(f"Done. {total} courses across {len(depts)} departments.")


if __name__ == "__main__":
    main()
