package edu.ucsd.prereq.service;

import edu.ucsd.prereq.domain.CourseEntity;
import edu.ucsd.prereq.domain.PrereqEntity;
import edu.ucsd.prereq.domain.PrereqType;
import edu.ucsd.prereq.dto.CourseDto;
import edu.ucsd.prereq.dto.CourseSummaryDto;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.TreeSet;

public final class CourseMapper {
    private CourseMapper() {}

    public static CourseDto toDto(CourseEntity c, Collection<PrereqEntity> edges) {
        return new CourseDto(
                c.getCode(),
                c.getTitle(),
                c.getDepartment(),
                c.getUnits(),
                c.getDescription(),
                c.getRawPrereqText(),
                c.getNotes(),
                groupsOf(edges, PrereqType.AND),
                c.getPrereqSlots(),
                groupsOf(edges, PrereqType.COREQ),
                groupsOf(edges, PrereqType.RECOMMENDED),
                c.getRequiredStanding(),
                c.getRestrictedToMajors());
    }

    public static CourseSummaryDto toSummary(CourseEntity c) {
        return new CourseSummaryDto(c.getCode(), c.getTitle(), c.getDepartment());
    }

    public static List<List<String>> groupsOf(Collection<PrereqEntity> edges, PrereqType type) {
        Map<Integer, TreeSet<String>> byGroup = new TreeMap<>();
        for (PrereqEntity e : edges) {
            if (e.getPrereqType() == type) {
                byGroup.computeIfAbsent(e.getGroupId(), k -> new TreeSet<>())
                        .add(e.getRequiredCourseCode());
            }
        }
        List<List<String>> out = new ArrayList<>(byGroup.size());
        for (TreeSet<String> members : byGroup.values()) {
            out.add(List.copyOf(members));
        }
        return out;
    }
}
