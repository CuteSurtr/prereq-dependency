package edu.ucsd.prereq.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import java.util.List;

/**
 * @param completed course codes the student has already passed; case and inner whitespace are
 *     normalized server-side
 * @param department optional filter, applied to the results
 * @param limit maximum rows to return; defaults to 200
 */
public record EligibilityRequest(
        @NotNull List<String> completed, String department, @Positive Integer limit) {}
