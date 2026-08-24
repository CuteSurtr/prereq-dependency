package edu.ucsd.prereq.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/** The frontend is served from GitHub Pages, so the API has to opt those origins in explicitly. */
@Configuration(proxyBeanMethods = false)
public class WebConfig implements WebMvcConfigurer {

    private final PrereqProperties props;

    public WebConfig(PrereqProperties props) {
        this.props = props;
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOrigins(props.cors().allowedOrigins().toArray(String[]::new))
                .allowedMethods("GET", "POST", "OPTIONS")
                .allowedHeaders("*")
                .maxAge(3600);
    }
}
