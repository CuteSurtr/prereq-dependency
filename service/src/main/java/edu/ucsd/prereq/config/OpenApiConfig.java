package edu.ucsd.prereq.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration(proxyBeanMethods = false)
public class OpenApiConfig {
    @Bean
    public OpenAPI prereqOpenApi() {
        return new OpenAPI()
                .info(
                        new Info()
                                .title("UCSD Prereq Graph API")
                                .version("0.1.0")
                                .description(
                                        "Course prerequisite graph: lookups, recursive chains, "
                                                + "unlocks and eligibility. Backed by MySQL, cached in Redis.")
                                .license(new License().name("MIT")));
    }
}
