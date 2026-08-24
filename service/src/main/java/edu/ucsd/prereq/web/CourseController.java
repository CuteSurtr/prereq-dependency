package edu.ucsd.prereq.web;

import edu.ucsd.prereq.dto.CourseDto;
import edu.ucsd.prereq.dto.CourseSummaryDto;
import edu.ucsd.prereq.dto.PrereqTreeDto;
import edu.ucsd.prereq.service.CourseCodes;
import edu.ucsd.prereq.service.CourseService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Positive;
import java.util.List;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Route-compatible with the dev FastAPI app in {@code backend/api.py}. */
@RestController
@RequestMapping("/api")
@Validated
@Tag(name = "Courses")
public class CourseController {

    private final CourseService courses;

    public CourseController(CourseService courses) {
        this.courses = courses;
    }

    @GetMapping("/courses")
    @Operation(summary = "Search courses by department and/or code/title substring")
    public List<CourseSummaryDto> list(
            @RequestParam(required = false) String department,
            @RequestParam(required = false) String q,
            @RequestParam(defaultValue = "200") @Positive @Max(2000) int limit) {
        return courses.search(department, q, limit);
    }

    @GetMapping("/courses/{code}")
    @Operation(summary = "Full course record, including prerequisite groups and slots")
    public CourseDto get(@PathVariable String code) {
        return courses.get(CourseCodes.normalize(code));
    }

    @GetMapping("/courses/{code}/prereqs")
    @Operation(summary = "Prerequisite groups for one course")
    public PrereqTreeDto prereqs(@PathVariable String code) {
        return courses.prereqTree(CourseCodes.normalize(code));
    }

    @GetMapping("/courses/{code}/unlocks")
    @Operation(summary = "Courses that list this course as a hard prerequisite")
    public List<CourseSummaryDto> unlocks(@PathVariable String code) {
        return courses.unlocks(CourseCodes.normalize(code));
    }

    @GetMapping("/departments")
    @Operation(summary = "Distinct department codes present in the catalog")
    public List<String> departments() {
        return courses.departments();
    }
}
