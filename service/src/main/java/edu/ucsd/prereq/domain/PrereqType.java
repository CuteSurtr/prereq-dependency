package edu.ucsd.prereq.domain;

/** Mirrors {@code backend/models.py::PrereqType} so both stacks read the same rows. */
public enum PrereqType {
    AND,
    OR,
    COREQ,
    RECOMMENDED
}
