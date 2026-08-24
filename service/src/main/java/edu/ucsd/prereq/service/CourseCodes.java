package edu.ucsd.prereq.service;

import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Catalog codes are stored as {@code "CSE 100"}. Users type {@code cse100}, {@code CSE  100} and
 * everything in between, so every code entering the API gets folded to one canonical form.
 */
public final class CourseCodes {

    private static final Pattern SPLIT = Pattern.compile("^([A-Z]{2,5})(\\d+[A-Z]*)$");
    private static final Pattern WHITESPACE = Pattern.compile("\\s+");

    private CourseCodes() {}

    public static String normalize(String raw) {
        if (raw == null) {
            return null;
        }
        String upper = WHITESPACE.matcher(raw.trim()).replaceAll(" ").toUpperCase(Locale.ROOT);
        if (upper.isEmpty()) {
            return upper;
        }
        Matcher m = SPLIT.matcher(upper.replace(" ", ""));
        return m.matches() ? m.group(1) + " " + m.group(2) : upper;
    }
}
