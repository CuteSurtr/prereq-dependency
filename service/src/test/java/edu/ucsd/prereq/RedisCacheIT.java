package edu.ucsd.prereq;

import static org.assertj.core.api.Assertions.assertThat;

import edu.ucsd.prereq.config.CacheNames;
import edu.ucsd.prereq.dto.ChainDto;
import edu.ucsd.prereq.dto.CourseDto;
import edu.ucsd.prereq.service.CourseService;
import edu.ucsd.prereq.service.GraphService;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.test.context.ActiveProfiles;

/**
 * Requires a Redis on localhost:6379 (see {@code service/docker-compose.yml}). Records survive a
 * round trip through Redis only if the cache serializer keeps enough type information, which is the
 * failure mode this test exists to catch.
 */
@ActiveProfiles({"test", "redisit"})
class RedisCacheIT extends FixtureTest {

    @Autowired CourseService courses;
    @Autowired GraphService graph;
    @Autowired RedisTemplate<String, Object> redis;

    @Test
    void courseRecordsRoundTripThroughRedis() {
        CourseDto first = courses.get("CSE 100");
        CourseDto cached = courses.get("CSE 100");

        assertThat(cached).isEqualTo(first);
        assertThat(cached.prereqGroups())
                .containsExactly(List.of("CSE 12", "CSE 20"), List.of("CSE 12", "MATH 20C"));
        assertThat(cached.restrictedToMajors()).containsExactly("CS25", "CS26");
        assertThat(cached.prereqSlots()).containsExactly(List.of("CSE 12"), List.of("CSE 20", "MATH 20C"));
    }

    @Test
    void nestedRecordsInsideCollectionsRoundTrip() {
        ChainDto first = graph.upstreamChain("CSE 100", 3);
        ChainDto cached = graph.upstreamChain("CSE 100", 3);

        assertThat(cached).isEqualTo(first);
        assertThat(cached.nodes()).hasSize(7);
        assertThat(cached.nodes().getFirst().code()).isEqualTo("CSE 100");
        assertThat(cached.edges()).isNotEmpty();
    }

    @Test
    void keysArePrefixedSoTheyCanShareARedisWithOtherApps() {
        courses.get("MATH 20A");
        assertThat(redis.keys("prereq:" + CacheNames.COURSE + "::MATH 20A")).isNotEmpty();
    }

    @Test
    void listAndMapReturningMethodsAreCacheableToo() {
        assertThat(courses.departments()).isEqualTo(courses.departments()).containsExactly("CSE", "MATH");
        assertThat(courses.unlocks("CSE 11")).isEqualTo(courses.unlocks("CSE 11"));
        assertThat(graph.export().courses()).hasSameSizeAs(graph.export().courses());
    }
}
