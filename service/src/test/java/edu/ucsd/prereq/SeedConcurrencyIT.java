package edu.ucsd.prereq;

import static org.assertj.core.api.Assertions.assertThat;

import edu.ucsd.prereq.repo.CourseRepository;
import edu.ucsd.prereq.repo.PrereqRepository;
import edu.ucsd.prereq.service.SeedCoordinator;
import edu.ucsd.prereq.service.SeedCoordinator.Outcome;
import edu.ucsd.prereq.service.SeedLock;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.Callable;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.stream.IntStream;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.test.context.ActiveProfiles;

/**
 * The importer decides whether to seed by reading the row count and then writing. Two instances
 * starting together both read an empty table, so both write, and every loser dies on the primary
 * key. Measured on this fixture with eight threads over ten trials: 70 of 80 calls failed that way.
 * Through {@link SeedCoordinator} the same 80 calls all succeed, because seven of every eight find
 * the lock taken and return without writing.
 *
 * <p>The failures were noisy rather than corrupting — each import runs in its own transaction, so
 * the losers rolled back cleanly and the table was correct after every trial. What the lock buys is
 * that seven instances no longer log a startup warning for a problem nobody has, and no longer
 * re-read and re-insert the whole graph to discover they were not needed.
 */
@SpringBootTest
@ActiveProfiles("mysqlit")
class SeedConcurrencyIT {
    private static final Path FIXTURE = Path.of("src/test/resources/fixtures/graph-mini.json");
    private static final int THREADS = 8;

    @Autowired SeedCoordinator coordinator;
    @Autowired SeedLock lock;
    @Autowired CourseRepository courses;
    @Autowired PrereqRepository prereqs;
    @Autowired StringRedisTemplate redis;

    @BeforeEach
    void emptyEverything() {
        prereqs.deleteAllInBatch();
        courses.deleteAllInBatch();
        redis.delete("prereq:seed:lock");
    }

    @Test
    void concurrentStartupsSeedExactlyOnce() throws Exception {
        List<SeedCoordinator.Result> results = allAtOnce(() -> coordinator.seedOnce(FIXTURE, false));

        assertThat(results).hasSize(THREADS);
        assertThat(results).noneMatch(r -> r.outcome() == Outcome.RAN_UNLOCKED);
        assertThat(results.stream().filter(r -> r.outcome() == Outcome.IMPORTED))
                .as("exactly one caller may perform the import")
                .hasSize(1);

        // Everyone else either found the lock taken or, if the winner had already finished and
        // released, found the table populated. Both are correct; neither writes.
        assertThat(results.stream().filter(r -> r.outcome() != Outcome.IMPORTED))
                .allMatch(r -> r.outcome() == Outcome.SKIPPED_LOCK_HELD
                        || r.outcome() == Outcome.ALREADY_POPULATED);

        assertThat(courses.count()).isEqualTo(7);
    }

    @Test
    void aForcedReseedRunsOnceRatherThanOncePerInstance() throws Exception {
        coordinator.seedOnce(FIXTURE, true);
        long edgesAfterOneImport = prereqs.count();

        List<SeedCoordinator.Result> results = allAtOnce(() -> coordinator.seedOnce(FIXTURE, true));

        // force makes every caller eligible to delete and rewrite, so without the lock all eight
        // would do the whole job. Row-level locking would keep the result correct; it would just
        // cost eight full re-imports to arrive at what one produces.
        assertThat(results.stream().filter(r -> r.outcome() == Outcome.IMPORTED)).hasSize(1);
        assertThat(courses.count()).isEqualTo(7);
        assertThat(prereqs.count()).isEqualTo(edgesAfterOneImport);
    }

    @Test
    void theLockIsReleasedOnlyByWhoeverHoldsIt() {
        String key = "prereq:test:lock";
        redis.delete(key);

        Optional<String> mine = lock.tryAcquire(key, Duration.ofSeconds(30));
        assertThat(mine).isPresent();
        assertThat(lock.tryAcquire(key, Duration.ofSeconds(30))).isEmpty();

        assertThat(lock.release(key, "some-other-token"))
                .as("a stale holder must not release a lock someone else now owns")
                .isFalse();
        assertThat(lock.release(key, mine.get())).isTrue();
        assertThat(lock.tryAcquire(key, Duration.ofSeconds(30))).isPresent();

        redis.delete(key);
    }

    /** Runs the same call on {@value #THREADS} threads released together, to widen the window. */
    private <T> List<T> allAtOnce(Callable<T> body) throws Exception {
        ExecutorService pool = Executors.newFixedThreadPool(THREADS);
        CyclicBarrier start = new CyclicBarrier(THREADS);
        try {
            List<Future<T>> futures =
                    IntStream.range(0, THREADS)
                            .mapToObj(
                                    i ->
                                            pool.submit(
                                                    () -> {
                                                        start.await(20, TimeUnit.SECONDS);
                                                        return body.call();
                                                    }))
                            .toList();
            List<T> out = new java.util.ArrayList<>(THREADS);
            for (Future<T> f : futures) {
                out.add(f.get(90, TimeUnit.SECONDS));
            }
            return out;
        } finally {
            pool.shutdownNow();
        }
    }
}
