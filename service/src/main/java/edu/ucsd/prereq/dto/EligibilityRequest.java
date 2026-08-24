package edu.ucsd.prereq.dto;

import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Positive;
import java.util.List;

public record EligibilityRequest(
        @NotNull List<String> completed, String department, @Positive Integer limit) {}
