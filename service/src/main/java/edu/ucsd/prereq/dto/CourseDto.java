package edu.ucsd.prereq.dto;

import java.util.List;

/**
 * Field-for-field equivalent of the frontend's {@code Course} type in {@code types.ts} and of one
 * entry in {@code graph.json}.
 *
 * @param prereqGroups disjunctive normal form: satisfying every member of any one group satisfies
 *     the prerequisite
 * @param prereqSlots AND-joined slots of OR-alternatives; null when the parser could not factor the
 *     expression into flat slots
 */
public record CourseDto(
        String code,
        String title,
        String department,
        String units,
        String description,
        String rawPrereqText,
        String notes,
        List<List<String>> prereqGroups,
        List<List<String>> prereqSlots,
        List<List<String>> coreqGroups,
        List<List<String>> recommendedGroups,
        String requiredStanding,
        List<String> restrictedToMajors) {}
