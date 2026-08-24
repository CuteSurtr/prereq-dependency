package edu.ucsd.prereq.dto;

import java.util.List;

/**
 * @param eligible courses whose prerequisites are now fully satisfied and that are not themselves
 *     in the completed set
 * @param truncated true when {@code limit} cut the list short
 */
public record EligibilityResponse(
        int completedCount, int eligibleCount, boolean truncated, List<CourseSummaryDto> eligible) {}
