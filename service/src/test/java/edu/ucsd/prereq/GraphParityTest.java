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

        assertThat(fromJava.get("courses")).isEqualTo(fromPython.get("courses"));
        assertThat(fromJava.get("unlocks")).isEqualTo(fromPython.get("unlocks"));
    }
}
