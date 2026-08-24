package edu.ucsd.prereq.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import edu.ucsd.prereq.config.CacheNames;
import edu.ucsd.prereq.domain.CourseEntity;
import edu.ucsd.prereq.domain.PrereqEntity;
import edu.ucsd.prereq.domain.PrereqType;
import edu.ucsd.prereq.dto.CourseDto;
import edu.ucsd.prereq.dto.GraphDto;
import edu.ucsd.prereq.repo.CourseRepository;
import edu.ucsd.prereq.repo.PrereqRepository;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Seeds MySQL from {@code frontend/public/graph.json}, the export the Python pipeline already
 * produces. That keeps the scraper and parser as the single source of truth: this service never
 * re-parses catalog text, it only reshapes an existing export into relational rows.
 */
@Service
public class GraphImportService {

    private static final Logger log = LoggerFactory.getLogger(GraphImportService.class);

    private final CourseRepository courses;
    private final PrereqRepository prereqs;
    private final ObjectMapper objectMapper;

    public GraphImportService(
            CourseRepository courses, PrereqRepository prereqs, ObjectMapper objectMapper) {
        this.courses = courses;
        this.prereqs = prereqs;
        this.objectMapper = objectMapper;
    }

    /**
     * Every cache is dropped on the way out: the cached graph, chains and course records all describe
     * the catalog that was just replaced, and a reseed that left them in place would keep serving the
     * old one until the TTLs happened to expire.
     *
     * @param replaceExisting drop existing rows first; otherwise the import is skipped when the
     *     courses table already has data
     */
    @Transactional
    @CacheEvict(
            cacheNames = {
                CacheNames.COURSES,
                CacheNames.COURSE,
                CacheNames.PREREQS,
                CacheNames.UNLOCKS,
                CacheNames.CHAIN,
                CacheNames.GRAPH,
                CacheNames.DEPARTMENTS
            },
            allEntries = true)
    public ImportStats importFrom(Path graphJson, boolean replaceExisting) throws IOException {
        if (!Files.isReadable(graphJson)) {
            throw new IOException("graph.json not readable at " + graphJson.toAbsolutePath());
        }
        if (courses.count() > 0) {
            if (!replaceExisting) {
                return ImportStats.alreadyPopulated();
            }
            prereqs.deleteAllInBatch();
            courses.deleteAllInBatch();
        }

        GraphDto graph = objectMapper.readValue(graphJson.toFile(), GraphDto.class);
        if (graph.courses() == null || graph.courses().isEmpty()) {
            throw new IOException("No courses in " + graphJson.toAbsolutePath());
        }

        List<CourseEntity> courseRows = new ArrayList<>(graph.courses().size());
        for (CourseDto dto : graph.courses().values()) {
            courseRows.add(toEntity(dto));
        }
        courses.saveAll(courseRows);
        // Prereq rows carry a foreign key to courses, so the parent rows have to land first.
        courses.flush();

        Set<String> known = graph.courses().keySet();
        List<PrereqEntity> edgeRows = new ArrayList<>();
        for (CourseDto dto : graph.courses().values()) {
            addEdges(edgeRows, dto.code(), dto.prereqGroups(), PrereqType.AND, known);
            addEdges(edgeRows, dto.code(), dto.coreqGroups(), PrereqType.COREQ, known);
            addEdges(edgeRows, dto.code(), dto.recommendedGroups(), PrereqType.RECOMMENDED, known);
        }
        prereqs.saveAll(edgeRows);
        prereqs.flush();

        log.info("Imported {} courses and {} prereq edges from {}", courseRows.size(), edgeRows.size(), graphJson);
        return new ImportStats(courseRows.size(), edgeRows.size(), false);
    }

    /**
     * Group position in the exported list becomes {@code group_id}, matching how
     * {@code backend/loader.py} numbers them.
     */
    private static void addEdges(
            List<PrereqEntity> out,
            String courseCode,
            List<List<String>> groups,
            PrereqType type,
            Set<String> known) {
        if (groups == null) {
            return;
        }
        for (int groupId = 0; groupId < groups.size(); groupId++) {
            for (String required : groups.get(groupId)) {
                if (required == null || required.isBlank() || !known.contains(required)) {
                    continue;
                }
                out.add(new PrereqEntity(courseCode, groupId, required, type));
            }
        }
    }

    private static CourseEntity toEntity(CourseDto dto) {
        CourseEntity e = new CourseEntity(dto.code(), dto.title(), dto.department());
        e.setUnits(dto.units());
        e.setDescription(dto.description());
        e.setRawPrereqText(dto.rawPrereqText());
        e.setNotes(dto.notes());
        e.setPrereqSlots(dto.prereqSlots());
        e.setRequiredStanding(dto.requiredStanding());
        e.setRestrictedToMajors(dto.restrictedToMajors());
        return e;
    }

    public record ImportStats(int courses, int edges, boolean skipped) {

        static ImportStats alreadyPopulated() {
            return new ImportStats(0, 0, true);
        }
    }
}
