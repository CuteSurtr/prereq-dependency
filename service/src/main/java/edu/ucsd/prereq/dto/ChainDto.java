package edu.ucsd.prereq.dto;

import java.util.List;

public record ChainDto(
        String root, int depth, boolean truncated, List<ChainNodeDto> nodes, List<ChainEdgeDto> edges) {
    public record ChainNodeDto(String code, String title, String department, int level, boolean known) {}

    public record ChainEdgeDto(String source, String target, String kind) {}
}
