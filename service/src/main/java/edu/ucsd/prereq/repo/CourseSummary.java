package edu.ucsd.prereq.repo;

/** Projection that skips the TEXT columns; list endpoints never need them. */
public interface CourseSummary {

    String getCode();

    String getTitle();

    String getDepartment();
}
