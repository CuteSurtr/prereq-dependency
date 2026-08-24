package edu.ucsd.prereq.dto;

/** Lightweight row for list endpoints; serialized as {@code {code, title, department}}. */
public record CourseSummaryDto(String code, String title, String department) {}
