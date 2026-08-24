package edu.ucsd.prereq.web;

import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Actuator already exposes {@code /actuator/health}; this keeps the {@code /api/health} path the
 * FastAPI app answers on so existing probes do not have to change.
 */
@RestController
@RequestMapping("/api")
@Tag(name = "Health")
public class HealthController {

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "ok");
    }
}
