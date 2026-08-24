package edu.ucsd.prereq.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import edu.ucsd.prereq.FixtureTest;
import edu.ucsd.prereq.config.CacheNames;
import edu.ucsd.prereq.repo.CourseRepository;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.annotation.Transactional;

/**
 * Proves the {@code @Cacheable} annotations are wired up, independently of which cache provider is
 * active: the second read is served without touching the repository, so deleting the row underneath
 * does not change the answer until the cache is cleared.
 */
class CachingBehaviourTest extends FixtureTest {

    @Autowired CourseService courseService;
    @Autowired GraphService graphService;
    @Autowired CourseRepository courses;

    @Test
    void courseLookupsAreCachedByCode() {
        assertThat(courseService.get("CSE 100").title()).isEqualTo("Advanced Data Structures");
        assertThat(cacheManager.getCache(CacheNames.COURSE).get("CSE 100")).isNotNull();
    }

    @Test
    @Transactional
    void aCachedCourseSurvivesTheRowDisappearing() {
        courseService.get("MATH 20A");

        courses.deleteById("MATH 20A");
        courses.flush();

        assertThat(courseService.get("MATH 20A").code()).isEqualTo("MATH 20A");

        cacheManager.getCache(CacheNames.COURSE).clear();
        assertThatThrownBy(() -> courseService.get("MATH 20A"))
                .isInstanceOf(CourseNotFoundException.class);
    }

    @Test
    void searchesAreCachedPerFilterCombination() {
        courseService.search("CSE", null, 200);
        assertThat(cacheManager.getCache(CacheNames.COURSES).get("search:CSE:*:200")).isNotNull();
        assertThat(cacheManager.getCache(CacheNames.COURSES).get("search:*:*:200")).isNull();
    }

    @Test
    void chainsAreCachedPerDepth() {
        graphService.upstreamChain("CSE 100", 2);
        assertThat(cacheManager.getCache(CacheNames.CHAIN).get("CSE 100:2")).isNotNull();
        assertThat(cacheManager.getCache(CacheNames.CHAIN).get("CSE 100:3")).isNull();
    }

    @Test
    void reseedingDropsEveryCache() throws java.io.IOException {
        courseService.get("CSE 100");
        graphService.export();
        graphService.upstreamChain("CSE 100", 2);
        assertThat(cacheManager.getCache(CacheNames.COURSE).get("CSE 100")).isNotNull();

        importer.importFrom(FIXTURE, true);

        // Stale entries would otherwise describe the catalog that was just replaced.
        assertThat(cacheManager.getCache(CacheNames.COURSE).get("CSE 100")).isNull();
        assertThat(cacheManager.getCache(CacheNames.CHAIN).get("CSE 100:2")).isNull();
    }

    @Test
    void exportsAndDepartmentListsAreCached() {
        graphService.export();
        courseService.departments();
        assertThat(cacheManager.getCache(CacheNames.GRAPH).getNativeCache()).isNotNull();
        assertThat(cacheManager.getCache(CacheNames.DEPARTMENTS).get(
                        org.springframework.cache.interceptor.SimpleKey.EMPTY))
                .isNotNull();
    }
}
