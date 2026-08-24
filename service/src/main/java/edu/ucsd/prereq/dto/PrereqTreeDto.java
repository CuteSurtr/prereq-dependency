package edu.ucsd.prereq.dto;

import java.util.List;

/** Response shape of {@code GET /api/courses/{code}/prereqs}. */
public record PrereqTreeDto(
        String code, String title, String rawPrereqText, String notes, List<PrereqGroupDto> groups) {}
