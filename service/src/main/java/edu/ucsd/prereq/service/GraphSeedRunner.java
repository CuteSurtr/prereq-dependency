package edu.ucsd.prereq.service;

import edu.ucsd.prereq.config.PrereqProperties;
import java.nio.file.Path;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.stereotype.Component;

@Component
public class GraphSeedRunner implements ApplicationRunner {
    private static final Logger log = LoggerFactory.getLogger(GraphSeedRunner.class);

    private final GraphImportService importer;
    private final PrereqProperties props;

    public GraphSeedRunner(GraphImportService importer, PrereqProperties props) {
        this.importer = importer;
        this.props = props;
    }

    @Override
    public void run(ApplicationArguments args) {
        PrereqProperties.Seed seed = props.seed();
        if (!seed.onStartup() || seed.graphJson() == null || seed.graphJson().isBlank()) {
            return;
        }
        Path path = Path.of(seed.graphJson());
        try {
            GraphImportService.ImportStats stats = importer.importFrom(path, seed.force());
            if (stats.skipped()) {
                log.info("Courses already present; skipping seed from {}", path);
            }
        } catch (Exception e) {
            log.warn("Could not seed from {}: {}", path.toAbsolutePath(), e.getMessage());
        }
    }
}
