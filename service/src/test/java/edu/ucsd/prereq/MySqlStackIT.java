package edu.ucsd.prereq;

import static org.assertj.core.api.Assertions.assertThat;

import edu.ucsd.prereq.domain.PrereqType;
import edu.ucsd.prereq.dto.EligibilityRequest;
import edu.ucsd.prereq.repo.CourseRepository;
import edu.ucsd.prereq.repo.PrereqRepository;
import edu.ucsd.prereq.service.CourseService;
import edu.ucsd.prereq.service.EligibilityService;
import edu.ucsd.prereq.service.GraphImportService;
import edu.ucsd.prereq.service.GraphService;
import java.io.IOException;
import java.nio.file.Path;
import java.util.List;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.cache.CacheManager;
import org.springframework.test.context.ActiveProfiles;

/**
 * The production stack end to end: Flyway-managed MySQL plus Redis. Requires both to be running —
 * {@code docker compose up -d} in this directory, or the service containers CI starts.
 *
 * <p>Because the profile sets {@code ddl-auto: validate}, the application context only starts if the
 * hand-written migration in {@code db/migration} and the JPA entities still agree; a column added to
 * one but not the other fails every test here rather than surfacing at runtime.
 */
@SpringBootTest
@ActiveProfiles("mysqlit")
class MySqlStackIT {

    private static final Path FIXTURE = Path.of("src/test/resources/fixtures/graph-mini.json");

    @Autowired GraphImportService importer;
    @Autowired CourseService courses;
    @Autowired GraphService graph;
    @Autowired EligibilityService eligibility;
    @Autowired CourseRepository courseRepo;
    @Autowired PrereqRepository prereqRepo;
    @Autowired CacheManager cacheManager;
    @Autowired Flyway flyway;

    @BeforeEach
    void reload() throws IOException {
        importer.importFrom(FIXTURE, true);
        cacheManager.getCacheNames().forEach(name -> cacheManager.getCache(name).clear());
    }

    @Test
    void flywayHasAppliedTheSchema() {
        assertThat(flyway.info().applied()).isNotEmpty();
        assertThat(flyway.info().current().getVersion().getVersion()).isEqualTo("1");
    }

    @Test
    void writesAndReadsEveryColumnTypeMysqlUses() {
        var cse100 = courseRepo.findById("CSE 100").orElseThrow();
        assertThat(cse100.getTitle()).isEqualTo("Advanced Data Structures");
        // TEXT columns
        assertThat(cse100.getRawPrereqText()).contains("CSE 12 and (CSE 20 or MATH 20C)");
        assertThat(cse100.getNotes()).isEqualTo("or consent of instructor");
        // JSON-in-TEXT columns, via the attribute converters
        assertThat(cse100.getRestrictedToMajors()).containsExactly("CS25", "CS26");
        assertThat(cse100.getPrereqSlots())
                .containsExactly(List.of("CSE 12"), List.of("CSE 20", "MATH 20C"));
        assertThat(cse100.getRequiredStanding()).isEqualTo("junior");
    }

    @Test
    void storesPrereqTypesAsReadableStrings() {
        assertThat(prereqRepo.findByCourseCodeOrderByGroupIdAscIdAsc("CSE 12"))
                .extracting(e -> e.getPrereqType())
                .containsExactlyInAnyOrder(PrereqType.AND, PrereqType.RECOMMENDED);
    }

    @Test
    void theForeignKeyCascadeRemovesOrphanEdges() throws IOException {
        long before = prereqRepo.count();
        assertThat(before).isPositive();
        importer.importFrom(FIXTURE, true);
        assertThat(prereqRepo.count()).isEqualTo(before);
    }

    @Test
    void servesTheApiSurfaceOffMysqlThroughRedis() {
        assertThat(courses.get("CSE 100").prereqGroups())
                .containsExactly(List.of("CSE 12", "CSE 20"), List.of("CSE 12", "MATH 20C"));
        assertThat(courses.search("CSE", null, 200)).hasSize(4);
        assertThat(courses.departments()).containsExactly("CSE", "MATH");
        assertThat(courses.unlocks("CSE 11")).hasSize(2);
        assertThat(courses.prereqTree("CSE 100").groups()).hasSize(2);

        assertThat(graph.upstreamChain("CSE 100", 5).nodes()).hasSize(7);
        assertThat(graph.export().courses()).hasSize(7);

        assertThat(eligibility.evaluate(new EligibilityRequest(List.of("CSE 11", "MATH 20A"), null, null))
                        .eligible())
                .hasSize(3);
    }

    @Test
    void secondReadsComeBackIdenticalFromRedis() {
        assertThat(courses.get("CSE 100")).isEqualTo(courses.get("CSE 100"));
        assertThat(graph.upstreamChain("CSE 100", 3)).isEqualTo(graph.upstreamChain("CSE 100", 3));
        assertThat(graph.export()).isEqualTo(graph.export());
    }
}
