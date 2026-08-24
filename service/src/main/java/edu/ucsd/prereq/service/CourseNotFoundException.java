package edu.ucsd.prereq.service;

public class CourseNotFoundException extends RuntimeException {

    public CourseNotFoundException(String code) {
        super("Course " + code + " not found");
    }
}
