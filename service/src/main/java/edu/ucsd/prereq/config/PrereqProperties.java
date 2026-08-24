package edu.ucsd.prereq.config;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

@ConfigurationProperties(prefix = "prereq")
public record PrereqProperties(
        @DefaultValue Cors cors,
        @DefaultValue CacheSettings cache,
        @DefaultValue Seed seed) {
    public record Cors(@DefaultValue("http://localhost:5173") List<String> allowedOrigins) {}

    public record CacheSettings(
            @DefaultValue("prereq") String keyPrefix,
            @DefaultValue("PT1H") Duration defaultTtl,
            @DefaultValue Map<String, Duration> ttls) {}

    public record Seed(
            String graphJson,
            @DefaultValue("true") boolean onStartup,
            @DefaultValue("false") boolean force) {}
}
