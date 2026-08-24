package edu.ucsd.prereq;

import edu.ucsd.prereq.config.PrereqProperties;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.cache.annotation.EnableCaching;

@SpringBootApplication
@EnableCaching
@EnableConfigurationProperties(PrereqProperties.class)
public class PrereqServiceApplication {

    public static void main(String[] args) {
        SpringApplication.run(PrereqServiceApplication.class, args);
    }
}
