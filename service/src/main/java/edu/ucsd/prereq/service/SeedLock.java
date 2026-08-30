package edu.ucsd.prereq.service;

import java.time.Duration;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.data.redis.core.script.RedisScript;
import org.springframework.stereotype.Component;

/**
 * A mutex held in Redis, used to keep two instances from seeding the database at the same time.
 *
 * <p>Acquisition is a single {@code SET key token NX PX ttl}: the check and the write are one
 * command, which is the point — the bug this exists to fix is a check-then-act in the importer.
 *
 * <p>Release is a compare-and-delete rather than a plain {@code DEL}. If a holder stalls past the
 * TTL, Redis drops the key and another instance can take the lock; a plain delete from the stalled
 * holder would then release a lock it no longer owns.
 */
@Component
public class SeedLock {
    private static final RedisScript<Long> RELEASE_IF_OWNED =
            new DefaultRedisScript<>(
                    """
                    if redis.call('get', KEYS[1]) == ARGV[1] then
                      return redis.call('del', KEYS[1])
                    else
                      return 0
                    end
                    """,
                    Long.class);

    private final StringRedisTemplate redis;

    public SeedLock(StringRedisTemplate redis) {
        this.redis = redis;
    }

    /** Returns the ownership token when the lock was taken, or empty when someone else holds it. */
    public Optional<String> tryAcquire(String key, Duration ttl) {
        String token = UUID.randomUUID().toString();
        Boolean acquired = redis.opsForValue().setIfAbsent(key, token, ttl);
        return Boolean.TRUE.equals(acquired) ? Optional.of(token) : Optional.empty();
    }

    /** Returns true when this caller still owned the lock and it was released. */
    public boolean release(String key, String token) {
        Long deleted = redis.execute(RELEASE_IF_OWNED, List.of(key), token);
        return deleted != null && deleted > 0;
    }
}
