package edu.ucsd.prereq;

import edu.ucsd.prereq.service.GraphImportService;
import java.io.IOException;
import java.nio.file.Path;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.cache.CacheManager;
import org.springframework.test.context.ActiveProfiles;

/** Reloads the miniature catalog before each test so cases cannot leak state into each other. */
@SpringBootTest
@ActiveProfiles("test")
public abstract class FixtureTest {

    protected static final Path FIXTURE = Path.of("src/test/resources/fixtures/graph-mini.json");

    @Autowired protected GraphImportService importer;

    @Autowired protected CacheManager cacheManager;

    @BeforeEach
    void reloadFixture() throws IOException {
        importer.importFrom(FIXTURE, true);
        cacheManager.getCacheNames().forEach(name -> cacheManager.getCache(name).clear());
    }
}
