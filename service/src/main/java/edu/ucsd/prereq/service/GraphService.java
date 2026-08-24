package edu.ucsd.prereq.service;

import edu.ucsd.prereq.config.CacheNames;
import edu.ucsd.prereq.domain.CourseEntity;
import edu.ucsd.prereq.domain.PrereqEntity;
import edu.ucsd.prereq.domain.PrereqType;
import edu.ucsd.prereq.dto.ChainDto;
import edu.ucsd.prereq.dto.ChainDto.ChainEdgeDto;
import edu.ucsd.prereq.dto.ChainDto.ChainNodeDto;
import edu.ucsd.prereq.dto.CourseDto;
import edu.ucsd.prereq.dto.GraphDto;
import edu.ucsd.prereq.repo.CourseRepository;
import edu.ucsd.prereq.repo.PrereqRepository;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.stream.Collectors;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class GraphService {
    public static final int CHAIN_NODE_CAP = 160;

    public static final int MAX_DEPTH = 12;

    private final CourseRepository courses;
    private final PrereqRepository prereqs;

    public GraphService(CourseRepository courses, PrereqRepository prereqs) {
        this.courses = courses;
        this.prereqs = prereqs;
    }

    @Cacheable(cacheNames = CacheNames.CHAIN, key = "#code + ':' + #depth")
    public ChainDto upstreamChain(String code, int depth) {
        if (!courses.existsById(code)) {
            throw new CourseNotFoundException(code);
        }
        int maxDepth = Math.clamp(depth, 1, MAX_DEPTH);

        Map<String, Integer> levels = new HashMap<>();
        levels.put(code, 0);
        Set<String> visited = new LinkedHashSet<>();
        visited.add(code);
        Set<String> edgeKeys = new LinkedHashSet<>();
        List<ChainEdgeDto> edges = new ArrayList<>();
        Set<String> frontier = Set.of(code);
        boolean truncated = false;

        for (int d = 0; d < maxDepth && !frontier.isEmpty() && !truncated; d++) {
            Map<String, List<PrereqEntity>> byCourse =
                    prereqs.findByCourseCodeInAndPrereqType(frontier, PrereqType.AND).stream()
                            .collect(Collectors.groupingBy(PrereqEntity::getCourseCode));

            Set<String> next = new LinkedHashSet<>();
            for (Map.Entry<String, List<PrereqEntity>> entry : byCourse.entrySet()) {
                String target = entry.getKey();
                List<List<String>> groups = CourseMapper.groupsOf(entry.getValue(), PrereqType.AND);
                String kind = groups.size() > 1 ? "or" : "and";
                for (List<String> group : groups) {
                    for (String source : group) {
                        if (edgeKeys.add(source + "->" + target)) {
                            edges.add(new ChainEdgeDto(source, target, kind));
                        }
                        if (visited.contains(source)) {
                            continue;
                        }
                        if (visited.size() >= CHAIN_NODE_CAP) {
                            truncated = true;
                            break;
                        }
                        visited.add(source);
                        levels.put(source, d + 1);
                        next.add(source);
                    }
                    if (truncated) {
                        break;
                    }
                }
                if (truncated) {
                    break;
                }
            }
            frontier = next;
        }

        return new ChainDto(code, maxDepth, truncated, buildNodes(visited, levels), List.copyOf(edges));
    }

    @Cacheable(cacheNames = CacheNames.GRAPH)
    public GraphDto export() {
        Map<String, List<PrereqEntity>> edgesByCourse =
                prereqs.findAllByOrderByCourseCodeAscGroupIdAscIdAsc().stream()
                        .collect(Collectors.groupingBy(PrereqEntity::getCourseCode));

        Map<String, CourseDto> out = new TreeMap<>();
        for (CourseEntity c : courses.findAll()) {
            out.put(c.getCode(), CourseMapper.toDto(c, edgesByCourse.getOrDefault(c.getCode(), List.of())));
        }

        Map<String, TreeSet<String>> unlocks = new TreeMap<>();
        for (List<PrereqEntity> rows : edgesByCourse.values()) {
            for (PrereqEntity e : rows) {
                if (e.getPrereqType() == PrereqType.AND) {
                    unlocks.computeIfAbsent(e.getRequiredCourseCode(), k -> new TreeSet<>())
                            .add(e.getCourseCode());
                }
            }
        }
        Map<String, List<String>> unlocksOut = new TreeMap<>();
        unlocks.forEach((k, v) -> unlocksOut.put(k, List.copyOf(v)));

        return new GraphDto(out, unlocksOut);
    }

    private List<ChainNodeDto> buildNodes(Set<String> visited, Map<String, Integer> levels) {
        Map<String, CourseEntity> known =
                courses.findByCodeInOrderByCode(visited).stream()
                        .collect(Collectors.toMap(CourseEntity::getCode, c -> c));

        List<ChainNodeDto> nodes = new ArrayList<>(visited.size());
        for (String c : visited) {
            CourseEntity e = known.get(c);
            nodes.add(
                    new ChainNodeDto(
                            c,
                            e != null ? e.getTitle() : null,
                            e != null ? e.getDepartment() : departmentOf(c),
                            levels.getOrDefault(c, 0),
                            e != null));
        }
        nodes.sort(Comparator.comparingInt(ChainNodeDto::level).thenComparing(ChainNodeDto::code));
        return List.copyOf(nodes);
    }

    private static String departmentOf(String code) {
        int space = code.indexOf(' ');
        return space > 0 ? code.substring(0, space) : code;
    }
}
