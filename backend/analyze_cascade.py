"""Find redundant ("cascading") direct prereqs across the catalog.

A direct prereq P of course C is redundant if some OTHER direct prereq Q of C
already requires P transitively — i.e., taking Q implies you've also taken P,
so listing P alongside Q is noise.

This is a conservative analysis: P is only flagged as redundant when EVERY
viable path through Q's prereqs forces P (no OR alternative lets a student
skip P). That way the cascade toggle never hides something a student could
legitimately have skipped.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

GRAPH_PATH = Path(__file__).parent.parent / "frontend" / "public" / "graph.json"


def load_graph() -> dict:
    return json.loads(GRAPH_PATH.read_text(encoding="utf-8"))


def compute_mandatory_ancestors(graph: dict) -> dict[str, frozenset[str]]:
    """For each course, return the set of courses you are GUARANTEED to take on
    the way to satisfying its prereqs, regardless of which OR alternatives you
    pick. Uses slots when available, falls back to DNF groups when not.
    """
    courses = graph["courses"]
    memo: dict[str, frozenset[str]] = {}
    visiting: set[str] = set()

    def ancestors(code: str) -> frozenset[str]:
        if code in memo:
            return memo[code]
        if code in visiting:
            # Cycle: contribute nothing, let the outer call reconcile.
            return frozenset()
        visiting.add(code)
        course = courses.get(code)
        if not course:
            visiting.discard(code)
            memo[code] = frozenset()
            return memo[code]

        slots = course.get("prereq_slots")
        if slots is None:
            # Unfactored: treat each DNF group as an alternative satisfying-set.
            # Mandatory = intersection over groups of (group ∪ ancestors of group).
            groups = course.get("prereq_groups") or []
            if not groups:
                result: frozenset[str] = frozenset()
            else:
                group_sets: list[set[str]] = []
                for group in groups:
                    g_set: set[str] = set(group)
                    for c in group:
                        g_set |= ancestors(c)
                    group_sets.append(g_set)
                result = frozenset(set.intersection(*group_sets)) if group_sets else frozenset()
        else:
            # Slots are AND-joined. Each slot is an OR over alternatives.
            # For a slot, mandatory contribution = intersection over alts of
            # ({alt} ∪ ancestors(alt)).
            course_mandatory: set[str] = set()
            for slot in slots:
                if not slot:
                    continue
                alt_sets: list[set[str]] = []
                for alt in slot:
                    alt_set: set[str] = {alt}
                    alt_set |= ancestors(alt)
                    alt_sets.append(alt_set)
                if alt_sets:
                    course_mandatory |= set.intersection(*alt_sets)
            result = frozenset(course_mandatory)

        visiting.discard(code)
        memo[code] = result
        return result

    return {code: ancestors(code) for code in courses}


def find_redundant_directs(graph: dict) -> dict[str, list[tuple[str, list[str]]]]:
    """For each course, return a list of (redundant_prereq, [implying_courses])."""
    courses = graph["courses"]
    mandatory = compute_mandatory_ancestors(graph)
    out: dict[str, list[tuple[str, list[str]]]] = {}

    for code, course in courses.items():
        slots = course.get("prereq_slots")
        directs: set[str] = set()
        if slots is not None:
            for slot in slots:
                directs |= set(slot)
        else:
            # Unfactored fallback: use the union of all DNF groups as directs.
            for group in course.get("prereq_groups") or []:
                directs |= set(group)
        if len(directs) < 2:
            continue

        # For each direct prereq P, check whether P is mandatory for some
        # OTHER direct prereq Q (Q != P). If yes, P is redundant — listing Q
        # already forces P.
        flagged: list[tuple[str, list[str]]] = []
        for p in sorted(directs):
            implyers: list[str] = []
            for q in directs:
                if q == p:
                    continue
                if p in mandatory.get(q, frozenset()):
                    implyers.append(q)
            if implyers:
                flagged.append((p, sorted(implyers)))
        if flagged:
            out[code] = flagged

    return out


def main() -> None:
    graph = load_graph()
    redundant = find_redundant_directs(graph)

    print(f"courses analyzed: {len(graph['courses'])}")
    print(f"courses with at least one redundant direct prereq: {len(redundant)}")

    n_redundant_pairs = sum(len(v) for v in redundant.values())
    print(f"total (course, redundant_prereq) pairs: {n_redundant_pairs}")

    dist = Counter(len(v) for v in redundant.values())
    print(f"distribution of redundancy count per course: {dict(sorted(dist.items()))}")

    # Show top examples (most redundant prereqs)
    top = sorted(redundant.items(), key=lambda kv: -len(kv[1]))[:15]
    print("\nTop 15 courses with the most redundant directs:")
    for code, flagged in top:
        title = graph["courses"][code]["title"]
        print(f"\n  {code} ({title[:60]})")
        for p, implyers in flagged:
            print(f"    - {p:<10} already implied by: {', '.join(implyers)}")

    # The motivating example
    print("\nUser's example, CSE 120:")
    if "CSE 120" in redundant:
        for p, implyers in redundant["CSE 120"]:
            print(f"  - {p} implied by: {', '.join(implyers)}")
    else:
        print("  (no redundant directs found — check the slot data)")


if __name__ == "__main__":
    main()
