package edu.ucsd.prereq.service;

import edu.ucsd.prereq.domain.PrereqEntity;
import edu.ucsd.prereq.domain.PrereqType;
import edu.ucsd.prereq.dto.CourseSummaryDto;
import edu.ucsd.prereq.dto.EligibilityRequest;
import edu.ucsd.prereq.dto.EligibilityResponse;
import edu.ucsd.prereq.repo.CourseRepository;
import edu.ucsd.prereq.repo.PrereqRepository;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Server-side counterpart of {@code isEligible} in {@code frontend/src/data.ts}: a course is
 * eligible when every member of at least one of its DNF prerequisite groups has been completed.
 *
 * <p>Only courses that name a completed course as a prerequisite are considered — those are the ones
 * a new completion can unlock. Courses with no prerequisites at all are always takeable and would
 * otherwise swamp the response, so they are deliberately left out.
 *
 * <p>Not cached: the request body is effectively unbounded, so cache keys would never be reused.
 */
@Service
@Transactional(readOnly = true)
public class EligibilityService {

    public static final int DEFAULT_LIMIT = 200;

    private final CourseRepository courses;
    private final PrereqRepository prereqs;

    public EligibilityService(CourseRepository courses, PrereqRepository prereqs) {
        this.courses = courses;
        this.prereqs = prereqs;
    }

    public EligibilityResponse evaluate(EligibilityRequest request) {
        Set<String> completed =
                request.completed().stream()
                        .map(CourseCodes::normalize)
                        .filter(c -> c != null && !c.isEmpty())
                        .collect(Collectors.toCollection(LinkedHashSet::new));
        int limit = request.limit() == null ? DEFAULT_LIMIT : request.limit();
        if (completed.isEmpty()) {
            return new EligibilityResponse(0, 0, false, List.of());
        }

        Set<String> candidates =
                prereqs.findByRequiredCourseCodeInAndPrereqType(completed, PrereqType.AND).stream()
                        .map(PrereqEntity::getCourseCode)
                        .filter(code -> !completed.contains(code))
                        .collect(Collectors.toCollection(LinkedHashSet::new));
        if (candidates.isEmpty()) {
            return new EligibilityResponse(completed.size(), 0, false, List.of());
        }

        Map<String, List<PrereqEntity>> byCourse =
                prereqs.findByCourseCodeInAndPrereqType(candidates, PrereqType.AND).stream()
                        .collect(Collectors.groupingBy(PrereqEntity::getCourseCode));

        List<String> satisfied = new ArrayList<>();
        for (String candidate : candidates) {
            List<List<String>> groups =
                    CourseMapper.groupsOf(byCourse.getOrDefault(candidate, List.of()), PrereqType.AND);
            if (groups.isEmpty() || groups.stream().anyMatch(completed::containsAll)) {
                satisfied.add(candidate);
            }
        }
        if (satisfied.isEmpty()) {
            return new EligibilityResponse(completed.size(), 0, false, List.of());
        }

        String department =
                request.department() == null || request.department().isBlank()
                        ? null
                        : request.department().trim().toUpperCase(Locale.ROOT);

        List<CourseSummaryDto> rows =
                courses.findByCodeInOrderByCode(satisfied).stream()
                        .filter(c -> department == null || department.equals(c.getDepartment()))
                        .map(CourseMapper::toSummary)
                        .toList();

        boolean truncated = rows.size() > limit;
        return new EligibilityResponse(
                completed.size(), rows.size(), truncated, truncated ? rows.subList(0, limit) : rows);
    }
}
