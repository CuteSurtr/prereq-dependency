package edu.ucsd.prereq.config;

/** Cache names shared between {@code @Cacheable} annotations and the TTL configuration. */
public final class CacheNames {

    public static final String COURSES = "courses";
    public static final String COURSE = "course";
    public static final String PREREQS = "prereqs";
    public static final String UNLOCKS = "unlocks";
    public static final String CHAIN = "chain";
    public static final String GRAPH = "graph";
    public static final String DEPARTMENTS = "departments";

    private CacheNames() {}
}
