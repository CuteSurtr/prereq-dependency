package edu.ucsd.prereq.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import edu.ucsd.prereq.FixtureTest;
import edu.ucsd.prereq.dto.ChainDto;
import edu.ucsd.prereq.dto.ChainDto.ChainNodeDto;
import edu.ucsd.prereq.dto.GraphDto;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

class GraphServiceTest extends FixtureTest {
    @Autowired GraphService graph;

    @Test
    void depthOneReturnsOnlyDirectPrerequisites() {
        ChainDto chain = graph.upstreamChain("CSE 100", 1);
        assertThat(chain.nodes()).extracting(ChainNodeDto::code)
                .containsExactlyInAnyOrder("CSE 100", "CSE 12", "CSE 20", "MATH 20C");
        assertThat(chain.truncated()).isFalse();
    }

    @Test
    void deeperTraversalWalksTheWholeUpstreamTree() {
        ChainDto chain = graph.upstreamChain("CSE 100", 5);
        assertThat(chain.nodes()).extracting(ChainNodeDto::code)
                .containsExactlyInAnyOrder(
                        "CSE 100", "CSE 12", "CSE 20", "MATH 20C", "CSE 11", "MATH 20A", "MATH 20B");
    }

    @Test
    void levelsCountHopsFromTheRoot() {
        ChainDto chain = graph.upstreamChain("CSE 100", 5);
        assertThat(levelOf(chain, "CSE 100")).isZero();
        assertThat(levelOf(chain, "CSE 12")).isEqualTo(1);
        assertThat(levelOf(chain, "CSE 11")).isEqualTo(2);
        assertThat(levelOf(chain, "MATH 20A")).isEqualTo(2);
    }

    @Test
    void marksMultiGroupCoursesAsOrEdges() {
        ChainDto chain = graph.upstreamChain("CSE 20", 1);
        assertThat(chain.edges()).allMatch(e -> e.kind().equals("or"));
        assertThat(chain.edges()).extracting(ChainDto.ChainEdgeDto::source)
                .containsExactlyInAnyOrder("CSE 11", "MATH 20A");

        assertThat(graph.upstreamChain("CSE 12", 1).edges()).allMatch(e -> e.kind().equals("and"));
    }

    @Test
    void deduplicatesEdgesThatAppearInMoreThanOneGroup() {
        ChainDto chain = graph.upstreamChain("CSE 100", 1);
        assertThat(chain.edges())
                .filteredOn(e -> e.source().equals("CSE 12") && e.target().equals("CSE 100"))
                .hasSize(1);
    }

    @Test
    void depthIsClampedRatherThanTrusted() {
        assertThat(graph.upstreamChain("CSE 100", 999).depth()).isEqualTo(GraphService.MAX_DEPTH);
        assertThat(graph.upstreamChain("CSE 100", 0).depth()).isEqualTo(1);
    }

    @Test
    void rejectsAnUnknownRoot() {
        assertThatThrownBy(() -> graph.upstreamChain("CSE 999", 2))
                .isInstanceOf(CourseNotFoundException.class);
    }

    @Test
    void leafCourseHasAChainOfItselfAlone() {
        ChainDto chain = graph.upstreamChain("MATH 20A", 3);
        assertThat(chain.nodes()).extracting(ChainNodeDto::code).containsExactly("MATH 20A");
        assertThat(chain.edges()).isEmpty();
    }

    @Test
    void exportMatchesTheStaticGraphJsonShape() {
        GraphDto export = graph.export();
        assertThat(export.courses()).hasSize(7).containsKey("CSE 100");

        var cse100 = export.courses().get("CSE 100");
        assertThat(cse100.prereqGroups())
                .containsExactly(List.of("CSE 12", "CSE 20"), List.of("CSE 12", "MATH 20C"));
        assertThat(cse100.requiredStanding()).isEqualTo("junior");
        assertThat(cse100.restrictedToMajors()).containsExactly("CS25", "CS26");
        assertThat(export.courses().get("CSE 12").recommendedGroups())
                .containsExactly(List.of("MATH 20A"));
    }

    @Test
    void exportDerivesUnlocksFromHardPrerequisitesOnly() {
        GraphDto export = graph.export();
        assertThat(export.unlocks().get("CSE 11")).containsExactly("CSE 12", "CSE 20");
        assertThat(export.unlocks().get("CSE 12")).containsExactly("CSE 100");

        assertThat(export.unlocks().get("MATH 20A")).containsExactly("CSE 20", "MATH 20B");
        assertThat(export.unlocks()).doesNotContainKey("CSE 100");
    }

    private static int levelOf(ChainDto chain, String code) {
        return chain.nodes().stream()
                .filter(n -> n.code().equals(code))
                .findFirst()
                .orElseThrow()
                .level();
    }
}
