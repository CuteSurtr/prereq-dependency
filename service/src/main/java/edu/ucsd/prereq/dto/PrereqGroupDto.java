package edu.ucsd.prereq.dto;

import java.util.List;

public record PrereqGroupDto(int groupId, List<PrereqMemberDto> members) {
    public record PrereqMemberDto(String required, String type) {}
}
