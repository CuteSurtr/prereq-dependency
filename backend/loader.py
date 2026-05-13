from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models import Base, Course, Prereq, PrereqType
from backend.parser import PrereqKind, detect_standing, extract_description_notes, parse

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
DB_PATH = Path(__file__).parent / "data" / "courses.db"


_KIND_TO_PREREQ_TYPE: dict[PrereqKind, PrereqType] = {
    PrereqKind.PREREQ: PrereqType.AND,
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

    all_courses: list[dict] = []
    for f in raw_files:
        all_courses.extend(json.loads(f.read_text(encoding="utf-8")))

    known_codes: set[str] = {c["code"] for c in all_courses}

    with Session(engine) as session:
        for c in all_courses:
            stats["courses_total"] += 1
            desc_notes = extract_description_notes(c.get("description"))
            standing = detect_standing(
                c["code"], c.get("raw_prereq_text"), c.get("description")
            )
            session.add(
                Course(
                    code=c["code"],
                    title=c["title"],
                    department=c["department"],
                    units=c.get("units"),
                    description=c.get("description"),
                    raw_prereq_text=c.get("raw_prereq_text"),
                    notes="; ".join(desc_notes) if desc_notes else None,
                    required_standing=standing.value if standing else None,
                )
            )
            if desc_notes:
                stats["desc_notes_extracted"] += 1
            if standing:
                stats[f"standing_{standing.value}"] += 1
        session.commit()

        for c in all_courses:
            raw = c.get("raw_prereq_text")
            if not raw:
                continue
            stats["prereq_strings_total"] += 1
            result = parse(raw)
            course = session.get(Course, c["code"])
            assert course is not None
            if result.notes:
                course.notes = (
                    f"{course.notes}; {result.notes}" if course.notes else result.notes
                )

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
                    stats["groups_dropped_self_prereq"] += 1
                    continue
                if any(req not in known_codes for req in group):
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

            if (
                result.slots is not None
                and result.kind == PrereqKind.PREREQ
            ):
                cleaned: list[list[str]] = []
                for slot in result.slots:
                    alts = [
                        a for a in slot
                        if a != course.code and a in known_codes
                    ]
                    if alts:
                        cleaned.append(sorted(set(alts)))
                if cleaned:
                    course.prereq_slots_json = json.dumps(cleaned, separators=(",", ":"))
                    stats["slots_stored"] += 1
            elif (
                result.slots is None
                and result.kind == PrereqKind.PREREQ
                and result.groups
            ):
                stats["slots_unfactored"] += 1
        session.commit()

    return dict(stats)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(DB_PATH))
    args = ap.parse_args()

    stats = load_into(Path(args.db))
    print(f"Loaded into {args.db}:")
    for k, v in sorted(stats.items()):
        print(f"  {k:>32}: {v}")


if __name__ == "__main__":
    main()
