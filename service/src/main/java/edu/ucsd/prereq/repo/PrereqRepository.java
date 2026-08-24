package edu.ucsd.prereq.repo;

import edu.ucsd.prereq.domain.PrereqEntity;
import edu.ucsd.prereq.domain.PrereqType;
import java.util.Collection;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PrereqRepository extends JpaRepository<PrereqEntity, Long> {

    List<PrereqEntity> findByCourseCodeOrderByGroupIdAscIdAsc(String courseCode);

    List<PrereqEntity> findByRequiredCourseCodeAndPrereqTypeOrderByCourseCodeAsc(
            String requiredCourseCode, PrereqType prereqType);

    /** Batched by level so a chain traversal costs one query per depth, not one per course. */
    List<PrereqEntity> findByCourseCodeInAndPrereqType(
            Collection<String> courseCodes, PrereqType prereqType);

    List<PrereqEntity> findByRequiredCourseCodeInAndPrereqType(
            Collection<String> requiredCourseCodes, PrereqType prereqType);

    List<PrereqEntity> findAllByOrderByCourseCodeAscGroupIdAscIdAsc();
}
