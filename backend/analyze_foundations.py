"""Heuristically identify "foundation" courses: lower-division courses that
many departments require as prereqs. These should stay visible even when the
user enables a strict "hide out-of-department" filter.

Heuristic: for each lower-division course (number < 100), count how many
DISTINCT departments have at least one course that requires it as a direct
prereq. Anything used by 3+ departments is a strong foundation candidate.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

GRAPH_PATH = Path(__file__).parent.parent / "frontend" / "public" / "graph.json"

# Strip trailing letters and pull the numeric part: "MATH 20A" -> 20.
_NUM_RE = re.compile(r"\d+")


def course_number(code: str) -> int | None:
    m = _NUM_RE.search(code)
    return int(m.group()) if m else None


def main() -> None:
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    courses = graph["courses"]

    # For each course (as a prereq), record which departments use it.
    used_by_depts: dict[str, set[str]] = defaultdict(set)
    used_by_courses: dict[str, set[str]] = defaultdict(set)

    for code, course in courses.items():
        dept = course["department"]
        seen_for_this_course: set[str] = set()
        # Pull from slots if available, fall back to DNF.
        slots = course.get("prereq_slots")
        if slots is not None:
            for slot in slots:
                seen_for_this_course.update(slot)
        else:
            for group in course.get("prereq_groups") or []:
                seen_for_this_course.update(group)
        for p in seen_for_this_course:
            used_by_depts[p].add(dept)
            used_by_courses[p].add(code)

    # Score foundation candidates.
    rows: list[tuple[str, int, int, str]] = []
    for code, depts in used_by_depts.items():
        c = courses.get(code)
        if not c:
            continue
        num = course_number(code)
        if num is None or num >= 100:
            continue  # only consider lower-division
        rows.append((code, len(depts), len(used_by_courses[code]), c["title"][:50]))

    rows.sort(key=lambda r: (-r[1], -r[2], r[0]))

    print(f"{'Course':<12} {'#Dpt':>4} {'#Uses':>5}  Title")
    print("-" * 80)
    for code, n_depts, n_uses, title in rows:
        if n_depts < 2:
            continue
        print(f"{code:<12} {n_depts:>4} {n_uses:>5}  {title}")

    # Summary stats
    multi = [r for r in rows if r[1] >= 3]
    print()
    print(f"Courses used as a prereq by 3+ departments: {len(multi)}")
    print(f"Courses used by 4+ departments: {sum(1 for r in rows if r[1] >= 4)}")
    print(f"Courses used by 5+ departments: {sum(1 for r in rows if r[1] >= 5)}")


if __name__ == "__main__":
    main()
