package edu.ucsd.prereq.dto;

import java.util.List;

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
