package edu.ucsd.prereq.config;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

/** Application-specific settings, bound from the {@code prereq.*} block of application.yml. */
@ConfigurationProperties(prefix = "prereq")
public record PrereqProperties(
        @DefaultValue Cors cors,
        @DefaultValue CacheSettings cache,
        @DefaultValue Seed seed) {

    public record Cors(@DefaultValue("http://localhost:5173") List<String> allowedOrigins) {}

    /**
     * @param ttls per-cache overrides keyed by cache name; anything absent falls back to
     *     {@code defaultTtl}.
     */
    public record CacheSettings(
            @DefaultValue("prereq") String keyPrefix,
            @DefaultValue("PT1H") Duration defaultTtl,
            @DefaultValue Map<String, Duration> ttls) {}

    /**
     * @param graphJson path to the static export the frontend already ships; used to seed MySQL
     * @param onStartup seed automatically when the courses table is empty
     * @param force reload even when the courses table already has rows
     */
    public record Seed(
            String graphJson,
            @DefaultValue("true") boolean onStartup,
            @DefaultValue("false") boolean force) {}
}
