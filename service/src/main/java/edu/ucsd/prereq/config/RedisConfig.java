package edu.ucsd.prereq.config;

import com.fasterxml.jackson.annotation.JsonTypeInfo;
import com.fasterxml.jackson.databind.JavaType;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.jsontype.BasicPolymorphicTypeValidator;
import com.fasterxml.jackson.databind.type.TypeFactory;
import edu.ucsd.prereq.dto.ChainDto;
import edu.ucsd.prereq.dto.CourseDto;
import edu.ucsd.prereq.dto.CourseSummaryDto;
import edu.ucsd.prereq.dto.GraphDto;
import edu.ucsd.prereq.dto.PrereqTreeDto;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.springframework.boot.autoconfigure.cache.RedisCacheManagerBuilderCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.Jackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext.SerializationPair;
import org.springframework.data.redis.serializer.RedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

/**
 * Cache entries are stored as plain JSON so they can be read with {@code redis-cli} and so a DTO
 * change that only adds a field does not invalidate the whole cache.
 *
 * <p>Each cache declares the exact type its values deserialize back into. The obvious alternative —
 * one generic serializer with Jackson's default typing — does not work here: every DTO is a record,
 * records are {@code final}, and {@code NON_FINAL} typing therefore never writes the {@code @class}
 * tag needed to read them back. Declaring the type also keeps the payloads small, which matters for
 * the {@code graph} cache in particular.
 *
 * <p>Spring Boot only consults the customizer when Redis is the active cache provider, so the test
 * profile ({@code spring.cache.type=simple}) ignores all of this and needs no Redis server.
 */
@Configuration(proxyBeanMethods = false)
public class RedisConfig {

    private static Map<String, JavaType> cacheValueTypes(TypeFactory types) {
        JavaType summaryList = types.constructCollectionType(List.class, CourseSummaryDto.class);
        return Map.of(
                CacheNames.COURSE, types.constructType(CourseDto.class),
                CacheNames.COURSES, summaryList,
                CacheNames.UNLOCKS, summaryList,
                CacheNames.PREREQS, types.constructType(PrereqTreeDto.class),
                CacheNames.CHAIN, types.constructType(ChainDto.class),
                CacheNames.GRAPH, types.constructType(GraphDto.class),
                CacheNames.DEPARTMENTS, types.constructCollectionType(List.class, String.class));
    }

    /**
     * Catch-all for any cache not listed above. It has to carry type information for every value,
     * final types included, or records coming back out would be unreadable.
     */
    @Bean
    public RedisSerializer<Object> fallbackCacheSerializer() {
        ObjectMapper mapper = new ObjectMapper();
        mapper.activateDefaultTyping(
                BasicPolymorphicTypeValidator.builder().allowIfBaseType(Object.class).build(),
                ObjectMapper.DefaultTyping.EVERYTHING,
                JsonTypeInfo.As.PROPERTY);
        return new GenericJackson2JsonRedisSerializer(mapper);
    }

    @Bean
    public RedisCacheManagerBuilderCustomizer cacheTtlCustomizer(
            PrereqProperties props, ObjectMapper objectMapper, RedisSerializer<Object> fallbackCacheSerializer) {

        RedisCacheConfiguration base =
                RedisCacheConfiguration.defaultCacheConfig()
                        .prefixCacheNameWith(props.cache().keyPrefix() + ":")
                        .disableCachingNullValues()
                        .serializeKeysWith(SerializationPair.fromSerializer(RedisSerializer.string()));

        Map<String, JavaType> valueTypes = cacheValueTypes(objectMapper.getTypeFactory());

        return builder -> {
            builder.cacheDefaults(
                    base.entryTtl(props.cache().defaultTtl())
                            .serializeValuesWith(SerializationPair.fromSerializer(fallbackCacheSerializer)));

            valueTypes.forEach(
                    (cacheName, javaType) ->
                            builder.withCacheConfiguration(
                                    cacheName,
                                    base.entryTtl(ttlFor(props, cacheName))
                                            .serializeValuesWith(
                                                    SerializationPair.fromSerializer(
                                                            new Jackson2JsonRedisSerializer<>(objectMapper, javaType)))));
        };
    }

    private static Duration ttlFor(PrereqProperties props, String cacheName) {
        return props.cache().ttls().getOrDefault(cacheName, props.cache().defaultTtl());
    }

    /** For the ad-hoc reads and cache sweeps that operating the service occasionally needs. */
    @Bean
    public RedisTemplate<String, Object> redisTemplate(
            RedisConnectionFactory connectionFactory, RedisSerializer<Object> fallbackCacheSerializer) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(connectionFactory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(fallbackCacheSerializer);
        template.setHashValueSerializer(fallbackCacheSerializer);
        template.afterPropertiesSet();
        return template;
    }
}
