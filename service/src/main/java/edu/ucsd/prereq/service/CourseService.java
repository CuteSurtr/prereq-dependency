package edu.ucsd.prereq.service;

import edu.ucsd.prereq.config.CacheNames;
import edu.ucsd.prereq.domain.CourseEntity;
import edu.ucsd.prereq.domain.PrereqEntity;
import edu.ucsd.prereq.domain.PrereqType;
import edu.ucsd.prereq.dto.CourseDto;
import edu.ucsd.prereq.dto.CourseSummaryDto;
import edu.ucsd.prereq.dto.PrereqGroupDto;
import edu.ucsd.prereq.dto.PrereqGroupDto.PrereqMemberDto;
import edu.ucsd.prereq.dto.PrereqTreeDto;
import edu.ucsd.prereq.repo.CourseRepository;
import edu.ucsd.prereq.repo.CourseSummary;
import edu.ucsd.prereq.repo.PrereqRepository;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class CourseService {
    private final CourseRepository courses;
    private final PrereqRepository prereqs;

    public CourseService(CourseRepository courses, PrereqRepository prereqs) {
        this.courses = courses;
        this.prereqs = prereqs;
    }

    @Cacheable(
            cacheNames = CacheNames.COURSES,
            key = "'search:' + (#department ?: '*') + ':' + (#q ?: '*') + ':' + #limit")
    public List<CourseSummaryDto> search(String department, String q, int limit) {
        String dept = department == null || department.isBlank() ? null : department.trim().toUpperCase(Locale.ROOT);
        String like = q == null || q.isBlank() ? null : "%" + q.trim().toUpperCase(Locale.ROOT) + "%";
        return courses.search(dept, like, PageRequest.ofSize(limit)).stream()
                .map(CourseService::toSummary)
                .toList();
    }

    @Cacheable(cacheNames = CacheNames.COURSE, key = "#code")
    public CourseDto get(String code) {
        CourseEntity course = courses.findById(code).orElseThrow(() -> new CourseNotFoundException(code));
        return CourseMapper.toDto(course, prereqs.findByCourseCodeOrderByGroupIdAscIdAsc(code));
    }

    @Cacheable(cacheNames = CacheNames.PREREQS, key = "#code")
    public PrereqTreeDto prereqTree(String code) {
        CourseEntity course = courses.findById(code).orElseThrow(() -> new CourseNotFoundException(code));
        Map<Integer, List<PrereqMemberDto>> byGroup = new LinkedHashMap<>();
        for (PrereqEntity e : prereqs.findByCourseCodeOrderByGroupIdAscIdAsc(code)) {
            byGroup.computeIfAbsent(e.getGroupId(), k -> new ArrayList<>())
                    .add(new PrereqMemberDto(e.getRequiredCourseCode(), e.getPrereqType().name()));
        }
        List<PrereqGroupDto> groups =
                byGroup.entrySet().stream()
                        .map(e -> new PrereqGroupDto(e.getKey(), List.copyOf(e.getValue())))
                        .toList();
        return new PrereqTreeDto(
                course.getCode(), course.getTitle(), course.getRawPrereqText(), course.getNotes(), groups);
    }

    @Cacheable(cacheNames = CacheNames.UNLOCKS, key = "#code")
    public List<CourseSummaryDto> unlocks(String code) {
        if (!courses.existsById(code)) {
            throw new CourseNotFoundException(code);
        }
        List<String> dependents =
                prereqs
                        .findByRequiredCourseCodeAndPrereqTypeOrderByCourseCodeAsc(code, PrereqType.AND)
                        .stream()
                        .map(PrereqEntity::getCourseCode)
                        .distinct()
                        .toList();
        if (dependents.isEmpty()) {
            return List.of();
        }
        return courses.findByCodeInOrderByCode(dependents).stream().map(CourseMapper::toSummary).toList();
    }

    @Cacheable(cacheNames = CacheNames.DEPARTMENTS)
    public List<String> departments() {
        return courses.findDistinctDepartments();
    }

    private static CourseSummaryDto toSummary(CourseSummary row) {
        return new CourseSummaryDto(row.getCode(), row.getTitle(), row.getDepartment());
    }
}
