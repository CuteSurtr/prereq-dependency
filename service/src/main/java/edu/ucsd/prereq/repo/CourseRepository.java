package edu.ucsd.prereq.repo;

import edu.ucsd.prereq.domain.CourseEntity;
import java.util.Collection;
import java.util.List;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CourseRepository extends JpaRepository<CourseEntity, String> {
    List<CourseEntity> findByCodeInOrderByCode(Collection<String> codes);

    @Query(
            """
            select c from CourseEntity c
            where (:department is null or c.department = :department)
              and (:q is null or upper(c.code) like :q or upper(c.title) like :q)
            order by c.code
            """)
    List<CourseSummary> search(
            @Param("department") String department, @Param("q") String q, Pageable pageable);

    @Query("select distinct c.department from CourseEntity c order by c.department")
    List<String> findDistinctDepartments();
}
