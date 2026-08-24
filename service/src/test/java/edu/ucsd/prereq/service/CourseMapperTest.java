package edu.ucsd.prereq.service;

import static org.assertj.core.api.Assertions.assertThat;

import edu.ucsd.prereq.domain.PrereqEntity;
import edu.ucsd.prereq.domain.PrereqType;
import java.util.List;
import org.junit.jupiter.api.Test;

class CourseMapperTest {
    @Test
    void groupsByGroupIdAndSortsMembersLikeThePythonExporter() {
        List<PrereqEntity> edges =
                List.of(
                        new PrereqEntity("CSE 100", 1, "MATH 20C", PrereqType.AND),
                        new PrereqEntity("CSE 100", 0, "CSE 20", PrereqType.AND),
                        new PrereqEntity("CSE 100", 0, "CSE 12", PrereqType.AND),
                        new PrereqEntity("CSE 100", 1, "CSE 12", PrereqType.AND),
                        new PrereqEntity("CSE 100", 0, "CSE 12", PrereqType.AND));

        assertThat(CourseMapper.groupsOf(edges, PrereqType.AND))
                .containsExactly(List.of("CSE 12", "CSE 20"), List.of("CSE 12", "MATH 20C"));
    }

    @Test
    void keepsPrereqTypesInSeparateNamespaces() {
        List<PrereqEntity> edges =
                List.of(
                        new PrereqEntity("CSE 12", 0, "CSE 11", PrereqType.AND),
                        new PrereqEntity("CSE 12", 0, "MATH 20A", PrereqType.RECOMMENDED));

        assertThat(CourseMapper.groupsOf(edges, PrereqType.AND)).containsExactly(List.of("CSE 11"));
        assertThat(CourseMapper.groupsOf(edges, PrereqType.RECOMMENDED))
                .containsExactly(List.of("MATH 20A"));
        assertThat(CourseMapper.groupsOf(edges, PrereqType.COREQ)).isEmpty();
    }
}
