package edu.ucsd.prereq.service;

import static org.assertj.core.api.Assertions.assertThat;

import edu.ucsd.prereq.FixtureTest;
import edu.ucsd.prereq.dto.CourseSummaryDto;
import edu.ucsd.prereq.dto.EligibilityRequest;
import edu.ucsd.prereq.dto.EligibilityResponse;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;

class EligibilityServiceTest extends FixtureTest {

    @Autowired EligibilityService eligibility;

    @Test
    void unlocksEverythingWhoseGroupIsFullySatisfied() {
        EligibilityResponse res = evaluate(List.of("MATH 20A", "CSE 11"));
        assertThat(res.eligible()).extracting(CourseSummaryDto::code)
                .containsExactlyInAnyOrder("MATH 20B", "CSE 12", "CSE 20");
        assertThat(res.completedCount()).isEqualTo(2);
    }

    @Test
    void anySatisfiedGroupIsEnough() {
        // CSE 20 lists CSE 11 and MATH 20A as separate groups, so either alone unlocks it.
        assertThat(evaluate(List.of("MATH 20A")).eligible()).extracting(CourseSummaryDto::code)
                .contains("CSE 20");
    }

    @Test
    void aPartiallySatisfiedGroupDoesNotUnlock() {
        // CSE 100 needs CSE 12 *and* one of CSE 20 / MATH 20C.
        assertThat(evaluate(List.of("CSE 11", "CSE 12")).eligible())
                .extracting(CourseSummaryDto::code)
                .doesNotContain("CSE 100");

        assertThat(evaluate(List.of("CSE 11", "CSE 12", "CSE 20")).eligible())
                .extracting(CourseSummaryDto::code)
                .contains("CSE 100");
    }

    @Test
    void normalizesWhateverTheUserTyped() {
        assertThat(evaluate(List.of("  cse11 ", "math 20a")).eligible())
                .extracting(CourseSummaryDto::code)
                .containsExactlyInAnyOrder("MATH 20B", "CSE 12", "CSE 20");
    }

    @Test
    void neverSuggestsACourseAlreadyCompleted() {
        assertThat(evaluate(List.of("CSE 11", "CSE 12")).eligible())
                .extracting(CourseSummaryDto::code)
                .doesNotContain("CSE 12");
    }

    @Test
    void appliesTheDepartmentFilter() {
        EligibilityResponse res =
                eligibility.evaluate(new EligibilityRequest(List.of("MATH 20A", "CSE 11"), "math", null));
        assertThat(res.eligible()).extracting(CourseSummaryDto::code).containsExactly("MATH 20B");
    }

    @Test
    void reportsTruncationWhenTheLimitBites() {
        EligibilityResponse res =
                eligibility.evaluate(new EligibilityRequest(List.of("MATH 20A", "CSE 11"), null, 1));
        assertThat(res.eligible()).hasSize(1);
        assertThat(res.eligibleCount()).isEqualTo(3);
        assertThat(res.truncated()).isTrue();
    }

    @Test
    void emptyInputYieldsEmptyOutput() {
        assertThat(evaluate(List.of()).eligible()).isEmpty();
        assertThat(evaluate(List.of("NOT A COURSE")).eligible()).isEmpty();
    }

    private EligibilityResponse evaluate(List<String> completed) {
        return eligibility.evaluate(new EligibilityRequest(completed, null, null));
    }
}
