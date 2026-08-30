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

    private final SeedCoordinator coordinator;
    private final PrereqProperties props;

    public GraphSeedRunner(SeedCoordinator coordinator, PrereqProperties props) {
        this.coordinator = coordinator;
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
            SeedCoordinator.Result result = coordinator.seedOnce(path, seed.force());
            switch (result.outcome()) {
                case ALREADY_POPULATED -> log.info("Courses already present; skipping seed from {}", path);
                case SKIPPED_LOCK_HELD -> log.info("Seed skipped; another instance is importing");
                case IMPORTED, RAN_UNLOCKED -> {
                    // importFrom already logged the row counts.
                }
            }
        } catch (Exception e) {
            log.warn("Could not seed from {}: {}", path.toAbsolutePath(), e.getMessage());
        }
    }
}
