from __future__ import annotations

import pytest

from backend.parser import PrereqKind, parse


def G(*codes: str) -> tuple[str, ...]:
    return tuple(sorted(codes))


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


def test_or_two_courses() -> None:
    r = parse("MATH 20A or MATH 10A")
    assert sorted(r.groups) == sorted([G("MATH 20A"), G("MATH 10A")])


def test_or_three_courses_oxford() -> None:
    r = parse("MATH 18, MATH 20F, or MATH 31AH")
    assert sorted(r.groups) == sorted([G("MATH 18"), G("MATH 20F"), G("MATH 31AH")])


def test_bare_numbers_inherit_dept_and() -> None:
    assert parse("MATH 20A, 20B, and 20C").groups == [
        G("MATH 20A", "MATH 20B", "MATH 20C")
    ]


def test_bare_numbers_inherit_dept_or() -> None:
    r = parse("MATH 20A or 20B or 20C")
    assert sorted(r.groups) == sorted([G("MATH 20A"), G("MATH 20B"), G("MATH 20C")])


def test_paren_or_inside_and() -> None:
    r = parse("MATH 20A and (MATH 20B or MATH 10B)")
    assert sorted(r.groups) == sorted(
        [G("MATH 20A", "MATH 20B"), G("MATH 20A", "MATH 10B")]
    )


def test_paren_or_then_and() -> None:
    r = parse("(MATH 20A or MATH 10A) and MATH 20B")
    assert sorted(r.groups) == sorted(
        [G("MATH 20A", "MATH 20B"), G("MATH 10A", "MATH 20B")]
    )


def test_two_and_groups_separated_by_or() -> None:
    r = parse("(MATH 20A and MATH 20B) or (MATH 10A and MATH 10B)")
    assert sorted(r.groups) == sorted(
        [G("MATH 20A", "MATH 20B"), G("MATH 10A", "MATH 10B")]
    )


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
    r = parse(
        "Math Placement Exam qualifying score, "
        "or AP Precalculus score of 5, "
        "or AP Calculus AB score of 3, "
        "or MATH 4C or MATH 10A."
    )
    assert sorted(r.groups) == sorted([G("MATH 4C"), G("MATH 10A")])


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


def test_real_math_109() -> None:
    r = parse(
        "MATH 18 or MATH 20F or MATH 31AH, and MATH 20C. "
        "Students who have not completed listed prerequisites may enroll with consent of instructor."
    )
    assert G("MATH 18", "MATH 20C") in r.groups
    assert G("MATH 20F", "MATH 20C") in r.groups
    assert G("MATH 31AH", "MATH 20C") in r.groups


def test_real_math_20c() -> None:
    r = parse("AP Calculus BC score of 4 or 5, or MATH 20B with a grade of C– or better.")
    assert r.groups == [G("MATH 20B")]


def test_real_math_2_placement_only() -> None:
    assert parse("Math Placement Exam qualifying score.").groups == []


def test_confident_on_clean_input() -> None:
    assert parse("MATH 20A and MATH 20B").confident is True


def test_groups_dedupe() -> None:
    r = parse("MATH 20A or MATH 20A")
    assert r.groups == [G("MATH 20A")]


def test_double_paren() -> None:
    r = parse("((MATH 20A))")
    assert r.groups == [G("MATH 20A")]


def test_multi_sentence_prereqs_treated_flat() -> None:
    r = parse("MATH 20A. MATH 20B.")
    assert "MATH 20A" in {c for g in r.groups for c in g} or r.groups == [G("MATH 20A")]


def test_bio_with_chem_prereq() -> None:
    r = parse("BILD 1 and CHEM 6A")
    assert r.groups == [G("BILD 1", "CHEM 6A")]


def test_bio_with_chem_or() -> None:
    r = parse("BILD 1 and (CHEM 6A or CHEM 6AH)")
    assert sorted(r.groups) == sorted(
        [G("BILD 1", "CHEM 6A"), G("BILD 1", "CHEM 6AH")]
    )


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
    r = parse("Math 20C or MATH 31BH")
    assert sorted(r.groups) == sorted([G("MATH 20C"), G("MATH 31BH")])


def test_either_keyword_dropped() -> None:
    r = parse("MATH 20D and either MATH 20F or MATH 31AH")
    assert sorted(r.groups) == sorted(
        [G("MATH 20D", "MATH 20F"), G("MATH 20D", "MATH 31AH")]
    )


def test_bare_numbers_inherit_dept_after_lowercase() -> None:
    r = parse("Math 20A, 20B, and 20C")
    assert r.groups == [G("MATH 20A", "MATH 20B", "MATH 20C")]


def test_double_comma_does_not_drop_courses() -> None:
    r = parse("MATH 20A, , and MATH 20B")
    assert r.groups == [G("MATH 20A", "MATH 20B")]


def test_lowercase_grade_qualifier_dropped() -> None:
    r = parse("MATH 20B with a grade of c- or better")
    assert r.groups == [G("MATH 20B")]


def test_leading_zero_normalized_in_prereq_text() -> None:
    r = parse("MAE 08 or MAE 09")
    assert sorted(r.groups) == sorted([G("MAE 8"), G("MAE 9")])


def test_leading_zero_in_oxford_list() -> None:
    r = parse("MAE 08, MAE 09, and MAE 11")
    assert r.groups == [G("MAE 11", "MAE 8", "MAE 9")]


def test_parallel_or_clauses_joined_by_bare_comma() -> None:
    r = parse("MATH 18 or MATH 31AH, MATH 20C or MATH 31BH")
    expected = sorted([
        G("MATH 18", "MATH 20C"),
        G("MATH 18", "MATH 31BH"),
        G("MATH 20C", "MATH 31AH"),
        G("MATH 31AH", "MATH 31BH"),
    ])
    assert sorted(r.groups) == expected


def test_hyphen_series_two_letters() -> None:
    r = parse("PHYS 4A-B")
    assert r.groups == [G("PHYS 4A", "PHYS 4B")]


def test_hyphen_series_three_letters() -> None:
    r = parse("MATH 20A-B-C")
    assert r.groups == [G("MATH 20A", "MATH 20B", "MATH 20C")]


def test_duplicate_credit_notice_dropped() -> None:
    r = parse("CSE 21. Students may not receive credit for both CSE 100R and CSE 100.")
    assert r.groups == [G("CSE 21")]


def test_renumbered_notice_dropped() -> None:
    r = parse("PHYS 2C and CHEM 6A. Renumbered from MAE 110A.")
    assert r.groups == [G("CHEM 6A", "PHYS 2C")]


def test_and_or_chain_wraps_correctly() -> None:
    r = parse("PHYS 2A and MATH 31BH or MATH 20C.")
    assert sorted(r.groups) == sorted(
        [G("MATH 31BH", "PHYS 2A"), G("MATH 20C", "PHYS 2A")]
    )


def test_and_or_chain_three_alternatives() -> None:
    r = parse("ECON 1 and MATH 10C or 20C or 31BH.")
    assert sorted(r.groups) == sorted(
        [
            G("ECON 1", "MATH 10C"),
            G("ECON 1", "MATH 20C"),
            G("ECON 1", "MATH 31BH"),
        ]
    )


def test_and_or_chain_doesnt_apply_when_followed_by_and() -> None:
    r = parse("MATH 20A and MATH 20B or MATH 10A and MATH 10B")
    assert sorted(r.groups) == sorted(
        [G("MATH 20A", "MATH 20B"), G("MATH 10A", "MATH 10B")]
    )


def test_leading_or_chain_wraps_when_followed_by_and() -> None:
    r = parse(
        "CSE 21 or MATH 154 or MATH 158 or MATH 184 or MATH 188 and CSE 12 and CSE 15L or CSE 29 or ECE 15"
    )
    assert len(r.groups) == 15
    for g in r.groups:
        assert "CSE 12" in g
        assert any(c in g for c in ("CSE 21", "MATH 154", "MATH 158", "MATH 184", "MATH 188"))
        assert any(c in g for c in ("CSE 15L", "CSE 29", "ECE 15"))


def test_extract_description_notes_concurrent() -> None:
    from backend.parser import extract_description_notes
    desc = (
        "Basic concepts in graph theory. Credit not offered for MATH 154 if MATH 158 is "
        "previously taken. If MATH 154 and MATH 158 are concurrently taken, credit is only "
        "offered for MATH 158."
    )
    notes = extract_description_notes(desc)
    assert any("Credit not offered" in n for n in notes)
    assert any("concurrently taken" in n for n in notes)


def test_extract_description_notes_credit_not_allowed() -> None:
    from backend.parser import extract_description_notes
    desc = "Probability and statistics. Credit not allowed for ECON 120A after ECE 109, MAE 108, MATH 180A, MATH 183, or MATH 186."
    notes = extract_description_notes(desc)
    assert any("ECE 109" in n and "credit" in n.lower() for n in notes)


def test_extract_description_notes_partial_credit() -> None:
    from backend.parser import extract_description_notes
    desc = (
        "Probability spaces. (Two units of credit offered for MATH 180A if ECON 120A previously, "
        "no credit offered if ECON 120A concurrently. Two units of credit offered for MATH 180A "
        "if MATH 183 or 186 taken previously or concurrently.)"
    )
    notes = extract_description_notes(desc)
    assert any("ECON 120A" in n and "credit" in n.lower() for n in notes)


def test_extract_description_notes_one_of_following() -> None:
    from backend.parser import extract_description_notes
    desc = "Course content. Students may only receive credit for one of the following: CHEM 40C, 40CH, 140C, or 140CH."
    notes = extract_description_notes(desc)
    assert any("CHEM 40C" in n and "credit" in n.lower() for n in notes)


def test_extract_description_notes_renumbered() -> None:
    from backend.parser import extract_description_notes
    notes = extract_description_notes("Course content. Renumbered from BIMM 171A.")
    assert any("Renumbered from" in n for n in notes)


def test_extract_description_notes_cross_listed() -> None:
    from backend.parser import extract_description_notes
    notes = extract_description_notes("Course content. Cross-listed with SIO 134.")
    assert any("Cross-listed" in n for n in notes)


def test_extract_description_notes_empty() -> None:
    from backend.parser import extract_description_notes
    assert extract_description_notes(None) == []
    assert extract_description_notes("") == []
    assert extract_description_notes("Just a normal description, nothing notable.") == []


def test_major_code_restrictions_not_treated_as_courses() -> None:
    r = parse(
        "MAE 11 and MAE 30A. Enrollment restricted to BE 25, MC 25, MC 27, MC 29 majors only."
    )
    assert r.groups == [G("MAE 11", "MAE 30A")]


def test_gpa_clause_not_treated_as_course() -> None:
    r = parse("MATH 20A and a UC San Diego GPA of 3.0 or higher.")
    assert r.groups == [G("MATH 20A")]


def test_known_limit_mixed_top_level_left_associative() -> None:
    r = parse("MATH 20A, and MATH 20B, or MATH 20C, and MATH 20D")
    assert sorted(r.groups) == sorted(
        [G("MATH 20A", "MATH 20B", "MATH 20D"), G("MATH 20C", "MATH 20D")]
    )


def test_slots_single_course() -> None:
    assert parse("MATH 20A").slots == [("MATH 20A",)]


def test_slots_pure_and() -> None:
    assert parse("MATH 20A and MATH 20B").slots == [("MATH 20A",), ("MATH 20B",)]


def test_slots_pure_or_collapses_to_one_slot() -> None:
    r = parse("MATH 20A or MATH 10A")
    assert r.slots == [("MATH 10A", "MATH 20A")]


def test_slots_factored_and_of_or() -> None:
    r = parse("MATH 20A and (MATH 20B or MATH 10B)")
    assert r.slots == [("MATH 20A",), ("MATH 10B", "MATH 20B")]


def test_slots_cse100_factored_into_three_slots() -> None:
    # The motivating case: 15 DNF groups collapse to 3 factored slots.
    r = parse(
        "CSE 21 or MATH 154 or MATH 158 or MATH 184 or MATH 188 "
        "and CSE 12 and CSE 15L or CSE 29 or ECE 15"
    )
    assert r.slots is not None
    assert len(r.slots) == 3
    assert ("CSE 12",) in r.slots
    assert ("CSE 21", "MATH 154", "MATH 158", "MATH 184", "MATH 188") in r.slots
    assert ("CSE 15L", "CSE 29", "ECE 15") in r.slots


def test_slots_or_of_ands_is_not_factorable() -> None:
    r = parse("(MATH 20A and MATH 20B) or (MATH 10A and MATH 10B)")
    assert r.slots is None
    assert sorted(r.groups) == sorted(
        [G("MATH 20A", "MATH 20B"), G("MATH 10A", "MATH 10B")]
    )


def test_slots_dropped_consent_clause_does_not_break_factoring() -> None:
    # The trailing "or consent of department" gets stripped to a note; the
    # remaining AST is a pure AND and should factor into per-course slots.
    r = parse("MATH 20D and BENG 103B and BENG 160 or consent of department.")
    assert r.slots == [("MATH 20D",), ("BENG 103B",), ("BENG 160",)]


def test_slots_empty_when_no_prereqs() -> None:
    assert parse("").slots is None or parse("").slots == []


def test_slots_dedupe_repeated_course() -> None:
    r = parse("MATH 20A or MATH 20A")
    assert r.slots == [("MATH 20A",)]
