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

SCRAPED_CATALOGS: tuple[str, ...] = (
    "MATH",
    "PHYS",
    "CHEM",
    "BIOL",
    "CSE",
    "ECE",
    "MAE",
    "BENG",
    "NANO",
    "SE",
    "ECON",
    "DSC",
    "COGS",
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


_COURSE_HEADER_RE = re.compile(
    r"^\s*(?P<code>[A-Z]{2,5}\s+\d+[A-Z]{0,3})"
    r"[^.]*"
    r"\.\s+(?P<title>.+?)"
    r"\s*\((?P<units>\d[^()]*)\)"
)

_LEADING_ZERO_RE = re.compile(r"^([A-Z]{2,5})\s+0+(\d)")


def _normalize_course_code(code: str) -> str:
    return _LEADING_ZERO_RE.sub(r"\1 \2", code)


_PREREQ_MARKER_RE = re.compile(
    r"(?:<(?:strong|em|i|b)[^>]*>\s*)+\s*Prerequisites?[^<]*(?:</(?:strong|em|i|b)\s*>\s*)+",
    re.I,
)


def _strip_html(s: str) -> str:
    return HTMLParser(s).text(separator=" ").strip()


def _split_description_and_prereq(html_inner: str) -> tuple[str, str | None]:
    match = _PREREQ_MARKER_RE.search(html_inner)
    if not match:
        return _strip_html(html_inner), None
    desc = html_inner[: match.start()]
    prereq = html_inner[match.end() :]
    return _strip_html(desc), _strip_html(prereq) or None


def parse_department_html(_url_key: str, html: str) -> list[ScrapedCourse]:
    tree = HTMLParser(html)
    courses: list[ScrapedCourse] = []

    pairs: list[tuple] = []
    pending_name = None
    for p in tree.css("p"):
        cls = (p.attributes.get("class") or "").strip()
        if cls == "course-name":
            if pending_name is not None:
                pairs.append((pending_name, None))
            pending_name = p
        elif cls == "course-descriptions":
            if pending_name is not None:
                pairs.append((pending_name, p))
                pending_name = None
    if pending_name is not None:
        pairs.append((pending_name, None))

    for name_node, desc_node in pairs:
        header = re.sub(r"\s+", " ", name_node.text(separator=" ")).strip()
        m = _COURSE_HEADER_RE.match(header)
        if not m:
            continue
        code = _normalize_course_code(re.sub(r"\s+", " ", m.group("code")).strip().upper())
        subject = code.split()[0]
        title = m.group("title").strip().rstrip(".")
        units = m.group("units").strip()

        if desc_node is not None:
            desc, prereq_text = _split_description_and_prereq(desc_node.html or "")
        else:
            desc, prereq_text = "", None

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
    ap = argparse.ArgumentParser()
    ap.add_argument("departments", nargs="*")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    depts = [d.upper() for d in args.departments] or list(SCRAPED_CATALOGS)
    print(f"Scraping {len(depts)} department(s): {', '.join(depts)}")
    total = scrape_many(depts, force=args.force)
    print(f"Done. {total} courses across {len(depts)} departments.")


if __name__ == "__main__":
    main()
