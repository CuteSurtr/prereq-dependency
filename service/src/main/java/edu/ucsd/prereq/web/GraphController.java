package edu.ucsd.prereq.web;

import edu.ucsd.prereq.dto.ChainDto;
import edu.ucsd.prereq.dto.EligibilityRequest;
import edu.ucsd.prereq.dto.EligibilityResponse;
import edu.ucsd.prereq.dto.GraphDto;
import edu.ucsd.prereq.service.CourseCodes;
import edu.ucsd.prereq.service.EligibilityService;
import edu.ucsd.prereq.service.GraphService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Positive;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Graph-wide work that is too expensive to redo in the browser on every interaction. */
@RestController
@RequestMapping("/api")
@Validated
@Tag(name = "Graph")
public class GraphController {

    private final GraphService graph;
    private final EligibilityService eligibility;

    public GraphController(GraphService graph, EligibilityService eligibility) {
        this.graph = graph;
        this.eligibility = eligibility;
    }

    @GetMapping("/courses/{code}/chain")
    @Operation(summary = "Recursive upstream prerequisite chain, laid out as nodes and edges")
    public ChainDto chain(
            @PathVariable String code,
            @RequestParam(defaultValue = "3") @Positive @Max(GraphService.MAX_DEPTH) int depth) {
        return graph.upstreamChain(CourseCodes.normalize(code), depth);
    }

    @PostMapping("/eligibility")
    @Operation(summary = "Courses unlocked by a set of completed courses")
    public EligibilityResponse eligibility(@Valid @RequestBody EligibilityRequest request) {
        return eligibility.evaluate(request);
    }

    @GetMapping("/graph")
    @Operation(summary = "Full graph export, identical in shape to frontend/public/graph.json")
    public GraphDto graph() {
        return graph.export();
    }
}
