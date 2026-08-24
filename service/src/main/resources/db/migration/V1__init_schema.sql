CREATE TABLE courses (
    code                      VARCHAR(20)  NOT NULL,
    title                     VARCHAR(255) NOT NULL,
    department                VARCHAR(10)  NOT NULL,
    units                     VARCHAR(64)  NULL,
    description               TEXT         NULL,
    raw_prereq_text           TEXT         NULL,
    notes                     TEXT         NULL,
    prereq_slots_json         TEXT         NULL,
    required_standing         VARCHAR(16)  NULL,
    restricted_to_majors_json TEXT         NULL,
    PRIMARY KEY (code),
    KEY ix_courses_department (department)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;

CREATE TABLE prereqs (
    id                   BIGINT      NOT NULL AUTO_INCREMENT,
    course_code          VARCHAR(20) NOT NULL,
    group_id             INT         NOT NULL,
    required_course_code VARCHAR(20) NOT NULL,
    prereq_type          VARCHAR(16) NOT NULL,
    PRIMARY KEY (id),
    KEY ix_prereqs_course_code (course_code),
    KEY ix_prereqs_required_course_code (required_course_code),
    KEY ix_prereqs_course_type_group (course_code, prereq_type, group_id),
    KEY ix_prereqs_required_type (required_course_code, prereq_type),
    CONSTRAINT fk_prereqs_course FOREIGN KEY (course_code) REFERENCES courses (code) ON DELETE CASCADE
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci;
