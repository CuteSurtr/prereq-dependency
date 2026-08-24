package edu.ucsd.prereq.service;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.api.Test;

class CourseCodesTest {
    @ParameterizedTest
    @CsvSource({
        "cse100,      CSE 100",
        "CSE 100,     CSE 100",
        "'  cse  100  ', CSE 100",
        "math20a,     MATH 20A",
        "MATH   20A,  MATH 20A",
        "bild1,       BILD 1",
    })
    void normalizesToCatalogForm(String raw, String expected) {
        assertThat(CourseCodes.normalize(raw)).isEqualTo(expected);
    }

    @Test
    void leavesUnrecognizedInputUppercasedRatherThanMangled() {
        assertThat(CourseCodes.normalize("consent of instructor"))
                .isEqualTo("CONSENT OF INSTRUCTOR");
    }

    @Test
    void handlesNullAndBlank() {
        assertThat(CourseCodes.normalize(null)).isNull();
        assertThat(CourseCodes.normalize("   ")).isEmpty();
    }
}
