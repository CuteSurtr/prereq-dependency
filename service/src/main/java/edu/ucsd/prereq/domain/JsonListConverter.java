package edu.ucsd.prereq.domain;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.persistence.AttributeConverter;
import jakarta.persistence.Converter;
import java.io.IOException;
import java.io.UncheckedIOException;
import java.util.List;

/**
 * The Python loader stores {@code restricted_to_majors} as a JSON array in a text column; these
 * converters keep that on-disk shape byte-compatible while exposing real lists to Java.
 */
public final class JsonListConverter {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private JsonListConverter() {}

    private static <T> String write(T value) {
        if (value == null) {
            return null;
        }
        try {
            return MAPPER.writeValueAsString(value);
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to serialize JSON column", e);
        }
    }

    private static <T> T read(String json, TypeReference<T> type) {
        if (json == null || json.isBlank()) {
            return null;
        }
        try {
            return MAPPER.readValue(json, type);
        } catch (IOException e) {
            throw new UncheckedIOException("Failed to deserialize JSON column: " + json, e);
        }
    }

    @Converter
    public static class StringList implements AttributeConverter<List<String>, String> {
        private static final TypeReference<List<String>> TYPE = new TypeReference<>() {};

        @Override
        public String convertToDatabaseColumn(List<String> attribute) {
            return write(attribute);
        }

        @Override
        public List<String> convertToEntityAttribute(String dbData) {
            return read(dbData, TYPE);
        }
    }

    @Converter
    public static class NestedStringList implements AttributeConverter<List<List<String>>, String> {
        private static final TypeReference<List<List<String>>> TYPE = new TypeReference<>() {};

        @Override
        public String convertToDatabaseColumn(List<List<String>> attribute) {
            return write(attribute);
        }

        @Override
        public List<List<String>> convertToEntityAttribute(String dbData) {
            return read(dbData, TYPE);
        }
    }
}
