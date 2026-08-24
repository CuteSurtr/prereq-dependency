package edu.ucsd.prereq.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Convert;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.util.List;
import java.util.Objects;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

@Entity
@Table(name = "courses")
public class CourseEntity {
    @Id
    @Column(name = "code", length = 20, nullable = false)
    private String code;

    @Column(name = "title", length = 255, nullable = false)
    private String title;

    @Column(name = "department", length = 10, nullable = false)
    private String department;

    @Column(name = "units", length = 64)
    private String units;

    @JdbcTypeCode(SqlTypes.LONGVARCHAR)
    @Column(name = "description")
    private String description;

    @JdbcTypeCode(SqlTypes.LONGVARCHAR)
    @Column(name = "raw_prereq_text")
    private String rawPrereqText;

    @JdbcTypeCode(SqlTypes.LONGVARCHAR)
    @Column(name = "notes")
    private String notes;

    @JdbcTypeCode(SqlTypes.LONGVARCHAR)
    @Column(name = "prereq_slots_json")
    @Convert(converter = JsonListConverter.NestedStringList.class)
    private List<List<String>> prereqSlots;

    @Column(name = "required_standing", length = 16)
    private String requiredStanding;

    @JdbcTypeCode(SqlTypes.LONGVARCHAR)
    @Column(name = "restricted_to_majors_json")
    @Convert(converter = JsonListConverter.StringList.class)
    private List<String> restrictedToMajors;

    protected CourseEntity() {}

    public CourseEntity(String code, String title, String department) {
        this.code = code;
        this.title = title;
        this.department = department;
    }

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getDepartment() {
        return department;
    }

    public void setDepartment(String department) {
        this.department = department;
    }

    public String getUnits() {
        return units;
    }

    public void setUnits(String units) {
        this.units = units;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public String getRawPrereqText() {
        return rawPrereqText;
    }

    public void setRawPrereqText(String rawPrereqText) {
        this.rawPrereqText = rawPrereqText;
    }

    public String getNotes() {
        return notes;
    }

    public void setNotes(String notes) {
        this.notes = notes;
    }

    public List<List<String>> getPrereqSlots() {
        return prereqSlots;
    }

    public void setPrereqSlots(List<List<String>> prereqSlots) {
        this.prereqSlots = prereqSlots;
    }

    public String getRequiredStanding() {
        return requiredStanding;
    }

    public void setRequiredStanding(String requiredStanding) {
        this.requiredStanding = requiredStanding;
    }

    public List<String> getRestrictedToMajors() {
        return restrictedToMajors;
    }

    public void setRestrictedToMajors(List<String> restrictedToMajors) {
        this.restrictedToMajors = restrictedToMajors;
    }

    @Override
    public boolean equals(Object o) {
        return o instanceof CourseEntity other && Objects.equals(code, other.code);
    }

    @Override
    public int hashCode() {
        return Objects.hashCode(code);
    }
}
