package edu.ucsd.prereq.dto;

import java.util.List;

/**
 * A breadth-first upstream prerequisite chain, the server-side counterpart of
 * {@code buildUpstreamChain} in the frontend.
 *
 * @param truncated true when the node cap stopped the traversal before it ran out of prerequisites
 */
public record ChainDto(
        String root, int depth, boolean truncated, List<ChainNodeDto> nodes, List<ChainEdgeDto> edges) {

    /**
     * @param level hops upstream from the root; the root itself is level 0
     * @param known false for a code that is referenced as a prerequisite but has no course row of
     *     its own, which a renderer should draw as a stub
     */
    public record ChainNodeDto(String code, String title, String department, int level, boolean known) {}

    /**
     * @param kind {@code "or"} when the target course has multiple alternative groups, else
     *     {@code "and"}
     */
    public record ChainEdgeDto(String source, String target, String kind) {}
}
