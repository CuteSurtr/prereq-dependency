package edu.ucsd.prereq.dto;

import java.util.List;

public record PrereqTreeDto(
        String code, String title, String rawPrereqText, String notes, List<PrereqGroupDto> groups) {}
