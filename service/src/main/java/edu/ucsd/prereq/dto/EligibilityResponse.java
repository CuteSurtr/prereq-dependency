package edu.ucsd.prereq.dto;

import java.util.List;

public record EligibilityResponse(
        int completedCount, int eligibleCount, boolean truncated, List<CourseSummaryDto> eligible) {}
