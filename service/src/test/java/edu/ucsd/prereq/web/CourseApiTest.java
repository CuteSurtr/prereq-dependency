package edu.ucsd.prereq.web;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import edu.ucsd.prereq.FixtureTest;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@AutoConfigureMockMvc
class CourseApiTest extends FixtureTest {

    @Autowired MockMvc mvc;

    @Test
    void healthMatchesTheFastApiResponse() throws Exception {
        mvc.perform(get("/api/health"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("ok"));
    }

    @Test
    void listsCoursesFilteredByDepartment() throws Exception {
        mvc.perform(get("/api/courses").param("department", "cse"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(4))
                .andExpect(jsonPath("$[0].code").value("CSE 100"));
    }

    @Test
    void searchesCodeAndTitle() throws Exception {
        mvc.perform(get("/api/courses").param("q", "calculus"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(3));

        mvc.perform(get("/api/courses").param("q", "cse 1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(3));
    }

    @Test
    void honoursTheLimit() throws Exception {
        mvc.perform(get("/api/courses").param("limit", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2));
    }

    @Test
    void serializesACourseInTheSameSnakeCaseShapeAsGraphJson() throws Exception {
        mvc.perform(get("/api/courses/{code}", "cse100"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value("CSE 100"))
                .andExpect(jsonPath("$.department").value("CSE"))
                .andExpect(jsonPath("$.raw_prereq_text").exists())
                .andExpect(jsonPath("$.required_standing").value("junior"))
                .andExpect(jsonPath("$.restricted_to_majors[0]").value("CS25"))
                .andExpect(jsonPath("$.prereq_groups[0][0]").value("CSE 12"))
                .andExpect(jsonPath("$.prereq_groups[1][1]").value("MATH 20C"))
                .andExpect(jsonPath("$.prereq_slots[1][0]").value("CSE 20"))
                .andExpect(jsonPath("$.coreq_groups").isEmpty());
    }

    @Test
    void unknownCourseUsesTheFastApiErrorEnvelope() throws Exception {
        mvc.perform(get("/api/courses/{code}", "CSE 999"))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.detail").value("Course CSE 999 not found"));
    }

    @Test
    void exposesPrereqGroups() throws Exception {
        mvc.perform(get("/api/courses/{code}/prereqs", "CSE 100"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value("CSE 100"))
                .andExpect(jsonPath("$.groups.length()").value(2))
                .andExpect(jsonPath("$.groups[0].group_id").value(0))
                // Members keep insertion order within a group, as the FastAPI route does.
                .andExpect(jsonPath("$.groups[0].members[0].required").value("CSE 12"))
                .andExpect(jsonPath("$.groups[0].members[1].required").value("CSE 20"))
                .andExpect(jsonPath("$.groups[0].members[0].type").value("AND"))
                .andExpect(jsonPath("$.groups[1].members[1].required").value("MATH 20C"));
    }

    @Test
    void exposesUnlocks() throws Exception {
        mvc.perform(get("/api/courses/{code}/unlocks", "CSE 11"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.length()").value(2))
                .andExpect(jsonPath("$[0].code").value("CSE 12"))
                .andExpect(jsonPath("$[1].code").value("CSE 20"));
    }

    @Test
    void listsDepartments() throws Exception {
        mvc.perform(get("/api/departments"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0]").value("CSE"))
                .andExpect(jsonPath("$[1]").value("MATH"));
    }

    @Test
    void returnsAChainAsNodesAndEdges() throws Exception {
        mvc.perform(get("/api/courses/{code}/chain", "CSE 100").param("depth", "2"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.root").value("CSE 100"))
                .andExpect(jsonPath("$.depth").value(2))
                .andExpect(jsonPath("$.truncated").value(false))
                .andExpect(jsonPath("$.nodes.length()").value(7))
                .andExpect(jsonPath("$.nodes[0].code").value("CSE 100"))
                .andExpect(jsonPath("$.nodes[0].level").value(0))
                .andExpect(jsonPath("$.nodes[0].known").value(true));
    }

    @Test
    void rejectsAnOutOfRangeDepth() throws Exception {
        mvc.perform(get("/api/courses/{code}/chain", "CSE 100").param("depth", "99"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.detail").exists());
    }

    @Test
    void computesEligibilityFromCompletedCourses() throws Exception {
        mvc.perform(
                        post("/api/eligibility")
                                .contentType(MediaType.APPLICATION_JSON)
                                .content("{\"completed\":[\"cse11\",\"MATH 20A\"]}"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.completed_count").value(2))
                .andExpect(jsonPath("$.eligible_count").value(3))
                .andExpect(jsonPath("$.truncated").value(false))
                .andExpect(jsonPath("$.eligible.length()").value(3));
    }

    @Test
    void rejectsAnEligibilityRequestWithoutCompletedCourses() throws Exception {
        mvc.perform(post("/api/eligibility").contentType(MediaType.APPLICATION_JSON).content("{}"))
                .andExpect(status().isBadRequest());
    }

    @Test
    void exportsTheWholeGraph() throws Exception {
        mvc.perform(get("/api/graph"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.courses.length()").value(7))
                .andExpect(jsonPath("$.courses['CSE 100'].prereq_groups.length()").value(2))
                .andExpect(jsonPath("$.unlocks['CSE 11'][0]").value("CSE 12"));
    }
}
