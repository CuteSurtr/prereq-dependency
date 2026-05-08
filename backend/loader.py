"""Load scraped JSON files into the SQLite DB used by the API.

Reads every `data/raw/*.json` produced by `backend.scraper`, parses each course's
prereq prose, and writes courses + prereq edges to `backend/data/courses.db`.

Idempotent: drops + recreates tables on each run.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models import Base, Course, Prereq, PrereqType
from backend.parser import PrereqKind, parse

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
DB_PATH = Path(__file__).parent / "data" / "courses.db"


_KIND_TO_PREREQ_TYPE: dict[PrereqKind, PrereqType] = {
    PrereqKind.PREREQ: PrereqType.AND,  # individual edge type within a group
    PrereqKind.COREQ: PrereqType.COREQ,
    PrereqKind.RECOMMENDED: PrereqType.RECOMMENDED,
}


def load_into(db_path: Path = DB_PATH) -> dict[str, int]:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    stats: Counter[str] = Counter()
    raw_files = sorted(RAW_DIR.glob("*.json"))
    if not raw_files:
        raise SystemExit(f"No raw scrape files at {RAW_DIR}; run `python -m backend.scraper` first.")

    # First pass: insert all courses (prereq edges may reference cross-dept courses,
    # so we want every course in the DB before we add edges).
    all_courses: list[dict] = []
    for f in raw_files:
        all_courses.extend(json.loads(f.read_text(encoding="utf-8")))

    # Index by code so we can drop edges that reference unknown courses.
    known_codes: set[str] = {c["code"] for c in all_courses}

    with Session(engine) as session:
        for c in all_courses:
            stats["courses_total"] += 1
            session.add(
                Course(
                    code=c["code"],
                    title=c["title"],
                    department=c["department"],
                    units=c.get("units"),
                    description=c.get("description"),
                    raw_prereq_text=c.get("raw_prereq_text"),
                    notes=None,
                )
            )
        session.commit()

        # Second pass: parse and insert prereq edges.
        for c in all_courses:
            raw = c.get("raw_prereq_text")
            if not raw:
                continue
            stats["prereq_strings_total"] += 1
            result = parse(raw)
            course = session.get(Course, c["code"])
            assert course is not None
            if result.notes:
                course.notes = result.notes

            if not result.groups:
                if result.confident:
                    stats["confident_no_groups"] += 1
                else:
                    stats["unconfident_no_groups"] += 1
                continue

            stats["confident" if result.confident else "unconfident"] += 1
            edge_type = _KIND_TO_PREREQ_TYPE[result.kind]

            for gid, group in enumerate(result.groups):
                if course.code in group:
                    # A group that includes the course itself is unsatisfiable. Drop
                    # the WHOLE group, not just the self-edge: keeping the rest as a
                    # smaller AND would silently weaken the requirement (e.g.
                    # {MAE 101A, MAE 11} -> {MAE 11} would imply MAE 11 alone is
                    # enough, which contradicts the original intent).
                    stats["groups_dropped_self_prereq"] += 1
                    continue
                if any(req not in known_codes for req in group):
                    # Same reasoning: if any AND member is unknown (deprecated /
                    # cross-listed elsewhere / typo), the surviving subset is a
                    # weakened version of the constraint. Drop the whole group.
                    stats["groups_dropped_unknown_course"] += 1
                    continue
                for required in group:
                    session.add(
                        Prereq(
                            course_code=course.code,
                            group_id=gid,
                            required_course_code=required,
                            prereq_type=edge_type,
                        )
                    )
                    stats["edges_inserted"] += 1
        session.commit()

    return dict(stats)


def main() -> None:
    ap = argparse.ArgumentParser(description="Load scraped JSON into the API SQLite DB.")
    ap.add_argument("--db", default=str(DB_PATH), help=f"Output DB path (default: {DB_PATH})")
    args = ap.parse_args()

    stats = load_into(Path(args.db))
    print(f"Loaded into {args.db}:")
    for k, v in sorted(stats.items()):
        print(f"  {k:>32}: {v}")


if __name__ == "__main__":
    main()
