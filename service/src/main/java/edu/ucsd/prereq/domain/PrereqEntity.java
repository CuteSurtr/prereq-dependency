package edu.ucsd.prereq.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import java.util.Objects;

@Entity
@Table(
        name = "prereqs",
        indexes = {
            @Index(name = "ix_prereqs_course_code", columnList = "course_code"),
            @Index(name = "ix_prereqs_required_course_code", columnList = "required_course_code")
        })
public class PrereqEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @Column(name = "course_code", length = 20, nullable = false)
    private String courseCode;

    @Column(name = "group_id", nullable = false)
    private int groupId;

    @Column(name = "required_course_code", length = 20, nullable = false)
    private String requiredCourseCode;

    @Enumerated(EnumType.STRING)
    @Column(name = "prereq_type", length = 16, nullable = false)
    private PrereqType prereqType;

    protected PrereqEntity() {}

    public PrereqEntity(String courseCode, int groupId, String requiredCourseCode, PrereqType prereqType) {
        this.courseCode = courseCode;
        this.groupId = groupId;
        this.requiredCourseCode = requiredCourseCode;
        this.prereqType = prereqType;
    }

    public Long getId() {
        return id;
    }

    public String getCourseCode() {
        return courseCode;
    }

    public int getGroupId() {
        return groupId;
    }

    public String getRequiredCourseCode() {
        return requiredCourseCode;
    }

    public PrereqType getPrereqType() {
        return prereqType;
    }

    @Override
    public boolean equals(Object o) {
        return o instanceof PrereqEntity other && id != null && Objects.equals(id, other.id);
    }

    @Override
    public int hashCode() {
        return Objects.hashCode(id);
    }
}
