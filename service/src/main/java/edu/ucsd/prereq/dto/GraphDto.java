package edu.ucsd.prereq.dto;

import java.util.List;
import java.util.Map;

public record GraphDto(Map<String, CourseDto> courses, Map<String, List<String>> unlocks) {}
