package edu.ucsd.prereq.service;

import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

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
