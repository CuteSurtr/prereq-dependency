"""Dump the SQLite DB to a single JSON file the frontend reads at runtime.

Vercel deploys the frontend as static; this avoids the complexity of a Python
serverless function while keeping the FastAPI backend alive for local dev.

Output schema:
    {
      "courses": {
        "MATH 20A": {"code": "MATH 20A", "title": "...", "department": "MATH", "units": "4",
                     "description": "...", "raw_prereq_text": "...", "notes": null,
                     "prereq_groups": [["MATH 4C"], ["MATH 10A"]],   // OR across, AND within
                     "coreq_groups": [...],
                     "recommended_groups": [...]},
        ...
      },
      "unlocks": {"MATH 20A": ["MATH 20B", "PHYS 2A", ...], ...}
    }
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.models import Course, Prereq, PrereqType

DB_PATH = Path(__file__).parent / "data" / "courses.db"
OUT_PATH = Path(__file__).parent.parent / "frontend" / "public" / "graph.json"


def export(db_path: Path = DB_PATH, out_path: Path = OUT_PATH) -> dict[str, int]:
    engine = create_engine(f"sqlite:///{db_path}")
    courses_out: dict[str, dict] = {}
    unlocks: dict[str, list[str]] = defaultdict(list)

    with Session(engine) as session:
        courses = session.query(Course).all()
        edges = session.query(Prereq).all()

        # Build groups per course, partitioned by edge type.
        groups: dict[
            tuple[str, PrereqType], dict[int, list[str]]
        ] = defaultdict(lambda: defaultdict(list))
        for e in edges:
            groups[(e.course_code, e.prereq_type)][e.group_id].append(e.required_course_code)

        for c in courses:
            prereq_groups = [
                sorted(set(members))
                for _, members in sorted(groups[(c.code, PrereqType.AND)].items())
            ]
            coreq_groups = [
                sorted(set(members))
                for _, members in sorted(groups[(c.code, PrereqType.COREQ)].items())
            ]
            recommended_groups = [
                sorted(set(members))
                for _, members in sorted(groups[(c.code, PrereqType.RECOMMENDED)].items())
            ]
            courses_out[c.code] = {
                "code": c.code,
                "title": c.title,
                "department": c.department,
                "units": c.units,
                "description": c.description,
                "raw_prereq_text": c.raw_prereq_text,
                "notes": c.notes,
                "prereq_groups": prereq_groups,
                "coreq_groups": coreq_groups,
                "recommended_groups": recommended_groups,
            }

        # Unlocks: who lists each course as a (blocking) prereq?
        for e in edges:
            if e.prereq_type == PrereqType.AND:
                unlocks[e.required_course_code].append(e.course_code)

    out = {
        "courses": courses_out,
        "unlocks": {k: sorted(set(v)) for k, v in unlocks.items()},
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    return {
        "courses": len(courses_out),
        "courses_with_prereqs": sum(1 for c in courses_out.values() if c["prereq_groups"]),
        "unlock_keys": len(unlocks),
        "bytes": out_path.stat().st_size,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Export DB to a single JSON for the static frontend.")
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--out", default=str(OUT_PATH))
    args = ap.parse_args()
    stats = export(Path(args.db), Path(args.out))
    print(f"Exported {args.out}:")
    for k, v in stats.items():
        print(f"  {k:>22}: {v}")


if __name__ == "__main__":
    main()
