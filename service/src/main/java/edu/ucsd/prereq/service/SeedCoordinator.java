package edu.ucsd.prereq.service;

import edu.ucsd.prereq.config.PrereqProperties;
import java.io.IOException;
import java.nio.file.Path;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DataAccessException;
import org.springframework.stereotype.Component;

/**
 * Runs the graph import at most once across every instance sharing this Redis.
 *
 * <p>{@link GraphImportService#importFrom} decides whether to seed by reading the row count and
 * then writing, which is safe in one process and wasteful in two: both read an empty table and both
 * insert, so every loser dies on the primary key. Measured with eight concurrent callers over ten
 * trials, 70 of 80 calls failed that way. The import is transactional, so those losers rolled back
 * and the table stayed correct — the cost is a startup warning per instance and a full pointless
 * read-and-insert of the graph behind it, not corruption. With the lock, all 80 calls succeed and
 * one of them does the work.
 *
 * <p>A caller that cannot take the lock skips rather than waits. Seeding is "make the table
 * populated", not "run exactly here": if another instance is already doing it, this one has nothing
 * to contribute, and blocking startup to watch would only make the slowest instance slower.
 *
 * <p>The lock lives outside the importer's transaction on purpose. Releasing inside it would hand
 * the lock to the next instance before this one's rows were committed, which is the same race in a
 * smaller window.
 */
@Component
public class SeedCoordinator {
    private static final Logger log = LoggerFactory.getLogger(SeedCoordinator.class);
    static final String LOCK_KEY = "prereq:seed:lock";

    private final GraphImportService importer;
    private final SeedLock lock;
    private final PrereqProperties props;

    public SeedCoordinator(GraphImportService importer, SeedLock lock, PrereqProperties props) {
        this.importer = importer;
        this.lock = lock;
        this.props = props;
    }

    public Result seedOnce(Path graphJson, boolean force) throws IOException {
        Optional<String> token;
        try {
            token = lock.tryAcquire(LOCK_KEY, props.seed().lockTtl());
        } catch (DataAccessException e) {
            // Redis is how instances agree, not how the import works. Losing it should not stop a
            // single-instance deployment from starting; the primary key is still the backstop.
            log.warn("Seed lock unavailable ({}); importing without coordination", e.getMessage());
            return new Result(Outcome.RAN_UNLOCKED, importer.importFrom(graphJson, force));
        }

        if (token.isEmpty()) {
            log.info("Another instance holds {}; skipping seed", LOCK_KEY);
            return new Result(Outcome.SKIPPED_LOCK_HELD, null);
        }

        try {
            GraphImportService.ImportStats stats = importer.importFrom(graphJson, force);
            return new Result(stats.skipped() ? Outcome.ALREADY_POPULATED : Outcome.IMPORTED, stats);
        } finally {
            if (!lock.release(LOCK_KEY, token.get())) {
                log.warn("Seed lock expired before the import finished; it took longer than {}",
                        props.seed().lockTtl());
            }
        }
    }

    public enum Outcome {
        IMPORTED,
        ALREADY_POPULATED,
        SKIPPED_LOCK_HELD,
        RAN_UNLOCKED
    }

    public record Result(Outcome outcome, GraphImportService.ImportStats stats) {}
}
