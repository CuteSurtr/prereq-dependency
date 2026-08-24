package edu.ucsd.prereq;

import static org.assertj.core.api.Assertions.assertThat;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import edu.ucsd.prereq.dto.GraphDto;
import edu.ucsd.prereq.service.GraphImportService;
import edu.ucsd.prereq.service.GraphService;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.cache.CacheManager;
import org.springframework.test.context.ActiveProfiles;

/**
 * Loads the real 2,000-course export, pushes it through the relational model, and reads it back out
 * again. The result has to be indistinguishable from what {@code backend/export_static.py} wrote.
 *
 * <p>This is the guard that keeps the two backends interchangeable: any drift in how Java groups,
 * sorts, deduplicates or names a field shows up here rather than as a frontend that renders
 * differently depending on which backend served it.
 */
@SpringBootTest
@ActiveProfiles("test")
class GraphParityTest {

    private static final Path REAL_GRAPH = Path.of("../frontend/public/graph.json");

    @Autowired GraphImportService importer;
    @Autowired GraphService graph;
    @Autowired ObjectMapper mapper;
    @Autowired CacheManager cacheManager;

    @BeforeAll
    static void requireTheExport() {
        assertThat(Files.isReadable(REAL_GRAPH))
                .as("run `python -m backend.export_static` if %s is missing", REAL_GRAPH)
                .isTrue();
    }

    @Test
    void roundTripsTheRealCatalogWithoutChangingIt() throws IOException {
        GraphImportService.ImportStats stats = importer.importFrom(REAL_GRAPH, true);
        cacheManager.getCacheNames().forEach(name -> cacheManager.getCache(name).clear());

        GraphDto exported = graph.export();
        JsonNode fromJava = mapper.valueToTree(exported);
        JsonNode fromPython = mapper.readTree(REAL_GRAPH.toFile());

        assertThat(stats.courses()).isEqualTo(fromPython.get("courses").size());
        // Object field order is not significant to JsonNode equality; array order is, which is what
        // makes this a real check on the sorting rules in CourseMapper and GraphService.
        assertThat(fromJava.get("courses")).isEqualTo(fromPython.get("courses"));
        assertThat(fromJava.get("unlocks")).isEqualTo(fromPython.get("unlocks"));
    }
}
