package edu.ucsd.prereq.dto;

import java.util.List;
import java.util.Map;

/** Byte-for-byte equivalent of {@code frontend/public/graph.json}. */
public record GraphDto(Map<String, CourseDto> courses, Map<String, List<String>> unlocks) {}
