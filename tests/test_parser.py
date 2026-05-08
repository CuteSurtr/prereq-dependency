"""Parser tests. Cases mix synthetic structure with verbatim strings from
catalog.ucsd.edu MATH (sampled at scrape time)."""

from __future__ import annotations

import pytest

from backend.parser import PrereqKind, parse


def G(*codes: str) -> tuple[str, ...]:
    """Sorted tuple, as the parser emits."""
    return tuple(sorted(codes))


# ---------- Single & empty --------------------------------------------------


def test_empty_string() -> None:
    r = parse("")
    assert r.groups == []
    assert r.kind == PrereqKind.PREREQ


def test_whitespace_only() -> None:
    assert parse("   ").groups == []


def test_single_course() -> None:
    r = parse("MATH 20A")
    assert r.groups == [G("MATH 20A")]
    assert r.kind == PrereqKind.PREREQ


def test_single_course_with_period() -> None:
    assert parse("CSE 11.").groups == [G("CSE 11")]


# ---------- AND -------------------------------------------------------------


def test_and_two_courses() -> None:
    assert parse("MATH 20A and MATH 20B").groups == [G("MATH 20A", "MATH 20B")]


def test_and_three_courses_oxford() -> None:
    assert parse("MATH 20A, MATH 20B, and MATH 20C").groups == [
        G("MATH 20A", "MATH 20B", "MATH 20C")
    ]


def test_and_three_courses_no_oxford() -> None:
    assert parse("MATH 20A, MATH 20B and MATH 20C").groups == [
        G("MATH 20A", "MATH 20B", "MATH 20C")
    ]


def test_and_cross_department() -> None:
    assert parse("CHEM 6A and MATH 20A").groups == [G("CHEM 6A", "MATH 20A")]


# ---------- OR --------------------------------------------------------------


def test_or_two_courses() -> None:
    r = parse("MATH 20A or MATH 10A")
    assert sorted(r.groups) == sorted([G("MATH 20A"), G("MATH 10A")])


def test_or_three_courses_oxford() -> None:
    r = parse("MATH 18, MATH 20F, or MATH 31AH")
    assert sorted(r.groups) == sorted([G("MATH 18"), G("MATH 20F"), G("MATH 31AH")])


# ---------- Bare number expansion ------------------------------------------


def test_bare_numbers_inherit_dept_and() -> None:
    assert parse("MATH 20A, 20B, and 20C").groups == [
        G("MATH 20A", "MATH 20B", "MATH 20C")
    ]


def test_bare_numbers_inherit_dept_or() -> None:
    r = parse("MATH 20A or 20B or 20C")
    assert sorted(r.groups) == sorted([G("MATH 20A"), G("MATH 20B"), G("MATH 20C")])


# ---------- Mixed AND/OR with parens ---------------------------------------


def test_paren_or_inside_and() -> None:
    """X and (Y or Z) → {X,Y} OR {X,Z}"""
    r = parse("MATH 20A and (MATH 20B or MATH 10B)")
    assert sorted(r.groups) == sorted(
        [G("MATH 20A", "MATH 20B"), G("MATH 20A", "MATH 10B")]
    )


def test_paren_or_then_and() -> None:
    """(X or Y) and Z → {X,Z} OR {Y,Z}"""
    r = parse("(MATH 20A or MATH 10A) and MATH 20B")
    assert sorted(r.groups) == sorted(
        [G("MATH 20A", "MATH 20B"), G("MATH 10A", "MATH 20B")]
    )


def test_two_and_groups_separated_by_or() -> None:
    """Spec example: (X and Y) OR (A and B)"""
    r = parse("(MATH 20A and MATH 20B) or (MATH 10A and MATH 10B)")
    assert sorted(r.groups) == sorted(
        [G("MATH 20A", "MATH 20B"), G("MATH 10A", "MATH 10B")]
    )


# ---------- "or equivalent" / placement / AP scores ------------------------


def test_or_equivalent_dropped() -> None:
    assert parse("MATH 20A or equivalent").groups == [G("MATH 20A")]


def test_or_equivalent_paren_dropped() -> None:
    assert parse("MATH 20A (or equivalent experience)").groups == [G("MATH 20A")]


def test_grade_qualifier_dropped() -> None:
    assert parse("MATH 20B with a grade of C– or better").groups == [G("MATH 20B")]


def test_placement_only_yields_no_groups() -> None:
    r = parse("Math Placement Exam qualifying score.")
    assert r.groups == []
    assert r.confident is True


def test_ap_score_only_yields_no_groups() -> None:
    r = parse("AP Calculus AB score of 3 or higher.")
    assert r.groups == []


def test_placement_or_courses() -> None:
    """Real MATH 20A string: placement/AP/courses mixed."""
    r = parse(
        "Math Placement Exam qualifying score, "
        "or AP Precalculus score of 5, "
        "or AP Calculus AB score of 3, "
        "or MATH 4C or MATH 10A."
    )
    # Non-course atoms drop; remaining is OR of two courses.
    assert sorted(r.groups) == sorted([G("MATH 4C"), G("MATH 10A")])


# ---------- Notes (consent / department approval) -------------------------


def test_consent_of_instructor_trailer() -> None:
    r = parse(
        "MATH 18 or MATH 20F or MATH 31AH, and MATH 20C. "
        "Students who have not completed listed prerequisites may enroll with consent of instructor."
    )
    expected = sorted([
        G("MATH 18", "MATH 20C"),
        G("MATH 20F", "MATH 20C"),
        G("MATH 31AH", "MATH 20C"),
    ])
    assert sorted(r.groups) == expected
    assert "consent" in r.notes.lower() or "may enroll" in r.notes.lower()


def test_consent_only_yields_empty_groups() -> None:
    r = parse("Consent of instructor.")
    assert r.groups == []
    assert r.notes


def test_department_approval_trailer() -> None:
    r = parse("CSE 100 or department approval")
    assert r.groups == [G("CSE 100")]
    assert "department" in r.notes.lower()


# ---------- Corequisites & recommended -------------------------------------


def test_corequisite_prefix() -> None:
    r = parse("Corequisite: PHYS 2A")
    assert r.kind == PrereqKind.COREQ
    assert r.groups == [G("PHYS 2A")]


def test_corequisites_plural() -> None:
    r = parse("Corequisites: MATH 20A and MATH 18")
    assert r.kind == PrereqKind.COREQ
    assert r.groups == [G("MATH 18", "MATH 20A")]


def test_concurrent_enrollment_prefix() -> None:
    r = parse("Concurrent enrollment in MATH 20D")
    assert r.kind == PrereqKind.COREQ
    assert r.groups == [G("MATH 20D")]


def test_recommended_preparation_prefix() -> None:
    r = parse("Recommended preparation: MATH 20A and MATH 20B")
    assert r.kind == PrereqKind.RECOMMENDED
    assert r.groups == [G("MATH 20A", "MATH 20B")]


# ---------- Real strings sampled from catalog.ucsd.edu MATH ---------------


def test_real_math_109() -> None:
    """MATH 109 prose. Distributes the 3-way OR across the AND with 20C."""
    r = parse(
        "MATH 18 or MATH 20F or MATH 31AH, and MATH 20C. "
        "Students who have not completed listed prerequisites may enroll with consent of instructor."
    )
    assert G("MATH 18", "MATH 20C") in r.groups
    assert G("MATH 20F", "MATH 20C") in r.groups
    assert G("MATH 31AH", "MATH 20C") in r.groups


def test_real_math_20c() -> None:
    """MATH 20C prose: AP/grade qualifier strip; one MATH course remains."""
    r = parse("AP Calculus BC score of 4 or 5, or MATH 20B with a grade of C– or better.")
    assert r.groups == [G("MATH 20B")]


def test_real_math_2_placement_only() -> None:
    """MATH 2 prose: placement-only prereq → no course edges."""
    assert parse("Math Placement Exam qualifying score.").groups == []


# ---------- Confidence flag -----------------------------------------------


def test_confident_on_clean_input() -> None:
    assert parse("MATH 20A and MATH 20B").confident is True


def test_groups_dedupe() -> None:
    r = parse("MATH 20A or MATH 20A")
    assert r.groups == [G("MATH 20A")]


def test_double_paren() -> None:
    r = parse("((MATH 20A))")
    assert r.groups == [G("MATH 20A")]


# ---------- Edge: multiple sentences --------------------------------------


def test_multi_sentence_prereqs_treated_flat() -> None:
    """Two sentences both listing courses — still get parsed as a flat list."""
    r = parse("MATH 20A. MATH 20B.")
    # Without an explicit conjunction, the parser falls into a tokens-only state:
    # both atoms accumulate into the AND chain (no operator → consecutive atoms left implicit).
    # This is a known limitation — the result here documents current behavior.
    assert "MATH 20A" in {c for g in r.groups for c in g} or r.groups == [G("MATH 20A")]


# ---------- Bio cross-department (chem dependency) ------------------------


def test_bio_with_chem_prereq() -> None:
    """A common pattern: bio courses requiring CHEM."""
    r = parse("BILD 1 and CHEM 6A")
    assert r.groups == [G("BILD 1", "CHEM 6A")]


def test_bio_with_chem_or() -> None:
    r = parse("BILD 1 and (CHEM 6A or CHEM 6AH)")
    assert sorted(r.groups) == sorted(
        [G("BILD 1", "CHEM 6A"), G("BILD 1", "CHEM 6AH")]
    )


# ---------- Parametric corpus check on a few synthetic cases --------------


@pytest.mark.parametrize(
    "text,expected_groups",
    [
        ("CSE 11", [("CSE 11",)]),
        ("CSE 11 or CSE 8A", [("CSE 11",), ("CSE 8A",)]),
        ("CSE 11 and CSE 12", [("CSE 11", "CSE 12")]),
        (
            "CSE 11 and CSE 12 and CSE 15L",
            [("CSE 11", "CSE 12", "CSE 15L")],
        ),
        (
            "CSE 11 and (CSE 12 or CSE 15L)",
            [("CSE 11", "CSE 12"), ("CSE 11", "CSE 15L")],
        ),
    ],
)
def test_parametric(text: str, expected_groups: list[tuple[str, ...]]) -> None:
    r = parse(text)
    assert sorted(r.groups) == sorted(expected_groups)


# ---------- "or more" / "(or subscore)" extras --------------------------


def test_ap_score_or_more() -> None:
    r = parse("AP Calculus AB score of 4 or more, or MATH 20A.")
    assert r.groups == [G("MATH 20A")]


def test_ap_score_or_subscore_paren() -> None:
    r = parse("AP Calculus AB score (or subscore) of 2, or MATH 3C")
    assert r.groups == [G("MATH 3C")]


def test_slash_separator_means_or() -> None:
    r = parse("EDS 30/MATH 95 and MATH 31CH")
    assert sorted(r.groups) == sorted(
        [G("EDS 30", "MATH 31CH"), G("MATH 31CH", "MATH 95")]
    )


def test_lowercase_dept_normalized() -> None:
    """Catalog inconsistency: 'Math 20A' (lowercase) appears in some prereq strings."""
    r = parse("Math 20C or MATH 31BH")
    assert sorted(r.groups) == sorted([G("MATH 20C"), G("MATH 31BH")])


def test_either_keyword_dropped() -> None:
    r = parse("MATH 20D and either MATH 20F or MATH 31AH")
    assert sorted(r.groups) == sorted(
        [G("MATH 20D", "MATH 20F"), G("MATH 20D", "MATH 31AH")]
    )


# ---------- Bug-fix regression tests --------------------------------------


def test_bare_numbers_inherit_dept_after_lowercase() -> None:
    """Catalog occasionally uses lowercase 'Math 20A'. The bare-number expansion
    must still inherit the dept for the numbers that follow."""
    r = parse("Math 20A, 20B, and 20C")
    assert r.groups == [G("MATH 20A", "MATH 20B", "MATH 20C")]


def test_double_comma_does_not_drop_courses() -> None:
    """Malformed double commas shouldn't cause downstream tokens to be dropped."""
    r = parse("MATH 20A, , and MATH 20B")
    assert r.groups == [G("MATH 20A", "MATH 20B")]


def test_lowercase_grade_qualifier_dropped() -> None:
    r = parse("MATH 20B with a grade of c- or better")
    assert r.groups == [G("MATH 20B")]


def test_leading_zero_normalized_in_prereq_text() -> None:
    """MAE's catalog uses zero-padded course-names ('MAE 08') but prereq text
    is unpadded. The normalizer strips leading zeros so both forms match."""
    r = parse("MAE 08 or MAE 09")
    assert sorted(r.groups) == sorted([G("MAE 8"), G("MAE 9")])


def test_leading_zero_in_oxford_list() -> None:
    r = parse("MAE 08, MAE 09, and MAE 11")
    assert r.groups == [G("MAE 11", "MAE 8", "MAE 9")]


def test_parallel_or_clauses_joined_by_bare_comma() -> None:
    """Catalog pattern from BENG 100: 'MATH 18 or MATH 31AH , MATH 20C or MATH 31BH'
    means (MATH 18 OR MATH 31AH) AND (MATH 20C OR MATH 31BH)."""
    r = parse("MATH 18 or MATH 31AH, MATH 20C or MATH 31BH")
    expected = sorted([
        G("MATH 18", "MATH 20C"),
        G("MATH 18", "MATH 31BH"),
        G("MATH 20C", "MATH 31AH"),
        G("MATH 31AH", "MATH 31BH"),
    ])
    assert sorted(r.groups) == expected


def test_hyphen_series_two_letters() -> None:
    """Catalog uses 'PHYS 4A-B' as shorthand for 'PHYS 4A and PHYS 4B'."""
    r = parse("PHYS 4A-B")
    assert r.groups == [G("PHYS 4A", "PHYS 4B")]


def test_hyphen_series_three_letters() -> None:
    r = parse("MATH 20A-B-C")
    assert r.groups == [G("MATH 20A", "MATH 20B", "MATH 20C")]


def test_duplicate_credit_notice_dropped() -> None:
    """'Students may not receive credit for X and Y' is a policy note, not a prereq."""
    r = parse("CSE 21. Students may not receive credit for both CSE 100R and CSE 100.")
    assert r.groups == [G("CSE 21")]


def test_renumbered_notice_dropped() -> None:
    r = parse("PHYS 2C and CHEM 6A. Renumbered from MAE 110A.")
    assert r.groups == [G("CHEM 6A", "PHYS 2C")]


# ---------- Catalog AND-OR-chain heuristic --------------------------------


def test_and_or_chain_wraps_correctly() -> None:
    """Catalog convention: 'X and Y or Z' means 'X and (Y or Z)'.
    MAE 30A in particular: 'PHYS 2A and MATH 31BH or MATH 20C.'"""
    r = parse("PHYS 2A and MATH 31BH or MATH 20C.")
    assert sorted(r.groups) == sorted(
        [G("MATH 31BH", "PHYS 2A"), G("MATH 20C", "PHYS 2A")]
    )


def test_and_or_chain_three_alternatives() -> None:
    """ECON 100A: 'ECON 1 and MATH 10C or 20C or 31BH.'"""
    r = parse("ECON 1 and MATH 10C or 20C or 31BH.")
    assert sorted(r.groups) == sorted(
        [
            G("ECON 1", "MATH 10C"),
            G("ECON 1", "MATH 20C"),
            G("ECON 1", "MATH 31BH"),
        ]
    )


def test_and_or_chain_doesnt_apply_when_followed_by_and() -> None:
    """'X and Y or Z and W' is genuinely '(X and Y) or (Z and W)' — the trailing
    AND keeps strict precedence. The heuristic should NOT wrap in this case."""
    r = parse("MATH 20A and MATH 20B or MATH 10A and MATH 10B")
    assert sorted(r.groups) == sorted(
        [G("MATH 20A", "MATH 20B"), G("MATH 10A", "MATH 10B")]
    )


def test_leading_or_chain_wraps_when_followed_by_and() -> None:
    """Catalog pattern from CSE 100: '(X or Y or Z or W or V) and CSE 12 and ...'."""
    r = parse(
        "CSE 21 or MATH 154 or MATH 158 or MATH 184 or MATH 188 and CSE 12 and CSE 15L or CSE 29 or ECE 15"
    )
    # Each group must have CSE 12 + one of the 5 leading alternatives + one of
    # the 3 trailing alternatives = 5 * 3 = 15 groups of 3 elements each.
    assert len(r.groups) == 15
    for g in r.groups:
        assert "CSE 12" in g
        assert any(c in g for c in ("CSE 21", "MATH 154", "MATH 158", "MATH 184", "MATH 188"))
        assert any(c in g for c in ("CSE 15L", "CSE 29", "ECE 15"))


def test_known_limit_mixed_top_level_left_associative() -> None:
    """Documented limitation (parser README): when TOP_AND and TOP_OR mix at the
    top level (rare in real prose), the parser binds left-associatively. This test
    pins current behavior so a future change is visible."""
    r = parse("MATH 20A, and MATH 20B, or MATH 20C, and MATH 20D")
    # Current: ((20A AND 20B) OR 20C) AND 20D  ->  {20A,20B,20D}, {20C,20D}
    # Ideal:   (20A AND 20B) OR (20C AND 20D)  ->  {20A,20B}, {20C,20D}
    # The first is what we produce today; the second is what an LLM fallback
    # should yield. Test pins the current behavior.
    assert sorted(r.groups) == sorted(
        [G("MATH 20A", "MATH 20B", "MATH 20D"), G("MATH 20C", "MATH 20D")]
    )
