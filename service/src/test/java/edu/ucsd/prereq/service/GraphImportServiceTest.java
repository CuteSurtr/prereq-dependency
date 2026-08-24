package edu.ucsd.prereq.service;

import static org.assertj.core.api.Assertions.assertThat;

import edu.ucsd.prereq.FixtureTest;
import edu.ucsd.prereq.domain.PrereqType;
import edu.ucsd.prereq.repo.CourseRepository;
import edu.ucsd.prereq.repo.PrereqRepository;
import java.io.IOException;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

class GraphImportServiceTest extends FixtureTest {

    @Autowired CourseRepository courses;
    @Autowired PrereqRepository prereqs;

    @Test
    void loadsEveryCourseAndFlattensGroupsIntoEdges() {
        assertThat(courses.count()).isEqualTo(7);
        // 1 + 1 + 1 + 2 + 4 prereq edges, plus CSE 12's single RECOMMENDED edge.
        assertThat(prereqs.count()).isEqualTo(10);
    }

    @Test
    void preservesJsonColumnsThroughTheConverters() {
        var cse100 = courses.findById("CSE 100").orElseThrow();
        assertThat(cse100.getRequiredStanding()).isEqualTo("junior");
        assertThat(cse100.getRestrictedToMajors()).containsExactly("CS25", "CS26");
        assertThat(cse100.getPrereqSlots())
                .containsExactly(List.of("CSE 12"), List.of("CSE 20", "MATH 20C"));
        assertThat(courses.findById("MATH 20A").orElseThrow().getRestrictedToMajors()).isNull();
    }

    @Test
    void numbersGroupsByPositionSoTheyRoundTrip() {
        assertThat(CourseMapper.groupsOf(
                        prereqs.findByCourseCodeOrderByGroupIdAscIdAsc("CSE 100"), PrereqType.AND))
                .containsExactly(List.of("CSE 12", "CSE 20"), List.of("CSE 12", "MATH 20C"));
    }

    @Test
    void skipsWhenAlreadyPopulatedUnlessForced() throws IOException {
        var skipped = importer.importFrom(FIXTURE, false);
        assertThat(skipped.skipped()).isTrue();
        assertThat(courses.count()).isEqualTo(7);

        var forced = importer.importFrom(FIXTURE, true);
        assertThat(forced.skipped()).isFalse();
        assertThat(forced.courses()).isEqualTo(7);
        assertThat(courses.count()).isEqualTo(7);
    }

    @Test
    void reportsAnUnreadablePath() {
        org.assertj.core.api.Assertions.assertThatThrownBy(
                        () -> importer.importFrom(java.nio.file.Path.of("does/not/exist.json"), true))
                .isInstanceOf(IOException.class)
                .hasMessageContaining("not readable");
    }
}
