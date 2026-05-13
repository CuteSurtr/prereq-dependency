import { useCallback, useEffect, useMemo, useState } from "react";
import { Graph } from "./Graph";
import { loadGraph } from "./data";
import { useProfile } from "./ProfileContext";
import { totalPicks } from "./profile";
import type { GraphData } from "./types";

const COURSE_CODE_RE = /\b[A-Z]{2,5}\s+\d+[A-Z]{0,3}\b/g;

function normalize(code: string): string {
  return code.replace(/\s+/g, " ").trim().toUpperCase();
}

function parseCompletedList(text: string): string[] {
  const found = text.toUpperCase().match(COURSE_CODE_RE) ?? [];
  return Array.from(new Set(found.map(normalize)));
}

const styles = {
  brand: {
    fontSize: 22,
    fontWeight: 300,
    letterSpacing: "-0.22px",
    margin: 0,
    color: "var(--color-navy)",
  } as const,
  brandPurple: { color: "var(--color-purple)", fontWeight: 400 } as const,
  intro: {
    fontSize: 12,
    lineHeight: 1.5,
    color: "var(--color-body)",
    margin: "4px 0 18px",
  } as const,
  field: { display: "flex", flexDirection: "column", gap: 4, marginBottom: 14 } as const,
  searchResults: {
    listStyle: "none",
    padding: 0,
    margin: "6px 0 0",
    maxHeight: 240,
    overflowY: "auto",
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    boxShadow: "var(--shadow-elevated)",
  } as const,
  searchResultButton: {
    display: "block",
    width: "100%",
    textAlign: "left",
    padding: "8px 12px",
    border: "none",
    background: "transparent",
    fontSize: 12,
    color: "var(--color-label)",
    transition: "background 100ms ease",
  } as const,
  recognizedRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    margin: "4px 0 18px",
  } as const,
  recognizedCount: {
    fontSize: 11,
    color: "var(--color-body)",
    fontVariantNumeric: "tabular-nums",
  } as const,
  legend: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
    padding: "10px 12px",
    background: "var(--color-bg-subtle)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    margin: "8px 0 18px",
  } as const,
  legendRow: { display: "flex", alignItems: "center", gap: 8, fontSize: 11 } as const,
  legendSwatch: {
    width: 22,
    height: 0,
    borderTopWidth: 2,
    borderTopStyle: "solid",
    flexShrink: 0,
  } as const,
  focusCard: {
    background: "var(--color-bg)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-md)",
    padding: 14,
    boxShadow: "var(--shadow-elevated)",
  } as const,
  focusCode: {
    fontSize: 16,
    fontWeight: 400,
    color: "var(--color-navy)",
    letterSpacing: "-0.16px",
    fontVariantNumeric: "tabular-nums",
  } as const,
  focusTitle: {
    fontSize: 13,
    fontWeight: 300,
    color: "var(--color-label)",
    margin: "2px 0 10px",
    lineHeight: 1.35,
  } as const,
  metaPill: {
    display: "inline-flex",
    alignItems: "center",
    padding: "2px 8px",
    background: "var(--color-purple-tint)",
    color: "var(--color-purple)",
    borderRadius: "var(--radius-sm)",
    fontSize: 11,
    fontVariantNumeric: "tabular-nums",
    fontWeight: 500,
  } as const,
  details: { marginTop: 10, fontSize: 12, color: "var(--color-body)" } as const,
  rawText: {
    margin: "6px 0 0",
    padding: "8px 10px",
    background: "var(--color-bg-subtle)",
    border: "1px solid var(--color-border)",
    borderRadius: "var(--radius-sm)",
    fontSize: 11.5,
    fontFamily: "var(--font-mono)",
    color: "var(--color-label)",
    whiteSpace: "pre-wrap",
    lineHeight: 1.5,
  } as const,
  notesBadge: {
    marginTop: 10,
    display: "inline-block",
    fontSize: 10,
    fontWeight: 400,
    padding: "1px 8px",
    background: "var(--color-magenta-bg)",
    color: "var(--color-ruby)",
    borderRadius: "var(--radius-sm)",
    border: "1px solid rgba(234, 34, 97, 0.25)",
  } as const,
};

const labelStyle: React.CSSProperties = {
  fontSize: 11,
  fontWeight: 500,
  color: "var(--color-label)",
  letterSpacing: "0.04em",
  textTransform: "uppercase",
};

const DEFAULT_FOCUS = "CSE 110";

const DEPTH_OPTIONS: { value: number; label: string }[] = [
  { value: 1, label: "Direct prereqs only" },
  { value: 2, label: "2 levels up" },
  { value: 3, label: "3 levels up" },
  { value: 5, label: "5 levels up" },
  { value: 99, label: "Full upstream chain" },
];

export default function App() {
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [focus, setFocus] = useState<string>(DEFAULT_FOCUS);
  const [completedRaw, setCompletedRaw] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [expandDepth, setExpandDepth] = useState<number>(1);
  const {
    profile,
    clearAllPicks,
    muteCourse,
    unmuteCourse,
    clearAllMutes,
    setMyDepartments,
  } = useProfile();
  // Seed the departments input synchronously from the persisted profile so
  // the input never flickers empty on first paint.
  const [deptsRaw, setDeptsRaw] = useState<string>(() =>
    profile.myDepartments.join(", "),
  );
  const pickCount = totalPicks(profile);
  const mutedSet = useMemo(() => new Set(profile.muted), [profile.muted]);

  const commitDepartments = useCallback(
    (text: string) => {
      const parsed = text
        .toUpperCase()
        .split(/[,\s]+/)
        .map((s) => s.trim())
        .filter((s) => /^[A-Z]{2,5}$/.test(s));
      setMyDepartments(parsed);
    },
    [setMyDepartments],
  );

  useEffect(() => {
    loadGraph()
      .then((g) => {
        setGraph(g);
        setFocus((current) =>
          g.courses[current]
            ? current
            : Object.keys(g.courses).sort()[0] ?? current,
        );
      })
      .catch((e) => setError(String(e)));
  }, []);

  const completedKey = useMemo(
    () => parseCompletedList(completedRaw).sort().join(","),
    [completedRaw],
  );
  const completed = useMemo(
    () => new Set(completedKey ? completedKey.split(",") : []),
    [completedKey],
  );

  const searchResults = useMemo(() => {
    if (!graph || query.trim().length < 2) return [];
    const q = query.toUpperCase();
    return Object.values(graph.courses)
      .filter((c) => c.code.includes(q) || c.title.toUpperCase().includes(q))
      .slice(0, 30);
  }, [graph, query]);

  const onSelectCourse = useCallback(
    (code: string) => {
      if (graph?.courses[code]) {
        setFocus(code);
        setDrawerOpen(false);
      }
    },
    [graph],
  );

  const focusCourse = graph?.courses[focus];

  if (error) {
    return (
      <main style={{ padding: 24 }}>
        <h1>UCSD Prereq Graph</h1>
        <p style={{ color: "var(--color-ruby)" }}>Failed to load graph data: {error}</p>
      </main>
    );
  }
  if (!graph) {
    return (
      <main style={{ padding: 24 }}>
        <h1>UCSD Prereq Graph</h1>
        <p>Loading…</p>
      </main>
    );
  }

  const courseCount = Object.keys(graph.courses).length;

  return (
    <div className="shell">
      <header className="mobile-bar" aria-label="App header">
        <h1 style={{ ...styles.brand, fontSize: 16 }}>
          UCSD <span style={styles.brandPurple}>Prereq Graph</span>
        </h1>
        <button
          className="menu-toggle"
          onClick={() => setDrawerOpen((v) => !v)}
          aria-expanded={drawerOpen}
          aria-controls="sidebar"
        >
          {drawerOpen ? "Close" : "Menu"}
        </button>
      </header>
      <button
        className={`sidebar-backdrop${drawerOpen ? " open" : ""}`}
        onClick={() => setDrawerOpen(false)}
        aria-label="Close menu"
        tabIndex={drawerOpen ? 0 : -1}
      />
      <aside
        id="sidebar"
        className={`sidebar scroll-y${drawerOpen ? " open" : ""}`}
      >
        <h1 style={styles.brand}>
          UCSD <span style={styles.brandPurple}>Prereq Graph</span>
        </h1>
        <p style={styles.intro}>
          {courseCount.toLocaleString()} courses across UCSD. Search a course to see its upstream
          prereqs and downstream unlocks.
        </p>

        <div style={styles.field}>
          <label style={labelStyle} htmlFor="search-input">
            Search
          </label>
          <input
            id="search-input"
            data-testid="search-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder='e.g. "MATH 20A" or "neural"'
          />
          {searchResults.length > 0 && (
            <ul
              data-testid="search-results"
              style={styles.searchResults}
              className="scroll-y search-results"
            >
              {searchResults.map((c) => (
                <li key={c.code}>
                  <button
                    className="search-result-btn"
                    onClick={() => {
                      setFocus(c.code);
                      setQuery("");
                    }}
                    style={styles.searchResultButton}
                  >
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-purple)",
                        fontSize: 11.5,
                        fontWeight: 500,
                      }}
                    >
                      {c.code}
                    </span>{" "}
                    <span style={{ color: "var(--color-body)" }}>{c.title}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div style={styles.field}>
          <label style={labelStyle} htmlFor="completed-input">
            My completed courses
          </label>
          <textarea
            id="completed-input"
            data-testid="completed-input"
            value={completedRaw}
            onChange={(e) => setCompletedRaw(e.target.value)}
            placeholder="Paste a list — e.g. MATH 20A, MATH 20B, CSE 11"
            rows={4}
            style={{ fontFamily: "var(--font-mono)", fontSize: 12, lineHeight: 1.5 }}
          />
          <div style={styles.recognizedRow}>
            <span style={styles.recognizedCount}>
              {completed.size} recognized
            </span>
            {completed.size > 0 && (
              <button
                className="btn-ghost"
                onClick={() => setCompletedRaw("")}
                style={{ padding: "2px 8px", fontSize: 11 }}
              >
                Clear
              </button>
            )}
          </div>
        </div>

        <div style={styles.field}>
          <label style={labelStyle} htmlFor="depth-select">
            Upstream depth
          </label>
          <select
            id="depth-select"
            value={expandDepth}
            onChange={(e) => setExpandDepth(Number(e.target.value))}
            style={{ fontSize: 12 }}
          >
            {DEPTH_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div style={styles.field}>
          <label style={labelStyle} htmlFor="dept-input">
            My departments
          </label>
          <input
            id="dept-input"
            data-testid="dept-input"
            value={deptsRaw}
            onChange={(e) => {
              setDeptsRaw(e.target.value);
              commitDepartments(e.target.value);
            }}
            placeholder='e.g. "CSE, MATH" — empty means all'
            style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
          />
          {profile.myDepartments.length > 0 && (
            <span style={{ ...styles.recognizedCount, marginTop: 4 }}>
              {profile.myDepartments.length} dept
              {profile.myDepartments.length === 1 ? "" : "s"} · others appear faded
            </span>
          )}
        </div>

        {pickCount > 0 && (
          <div style={styles.recognizedRow}>
            <span style={styles.recognizedCount}>
              {pickCount} pick{pickCount === 1 ? "" : "s"} saved
            </span>
            <button
              className="btn-ghost"
              onClick={() => clearAllPicks()}
              style={{ padding: "2px 8px", fontSize: 11 }}
            >
              Reset picks
            </button>
          </div>
        )}

        {profile.muted.length > 0 && (
          <div style={{ ...styles.field, marginBottom: 14 }}>
            <div style={styles.recognizedRow}>
              <span style={styles.recognizedCount}>
                {profile.muted.length} hidden course
                {profile.muted.length === 1 ? "" : "s"}
              </span>
              <button
                className="btn-ghost"
                onClick={() => clearAllMutes()}
                style={{ padding: "2px 8px", fontSize: 11 }}
              >
                Unhide all
              </button>
            </div>
            <ul
              style={{
                listStyle: "none",
                padding: 0,
                margin: "6px 0 0",
                maxHeight: 120,
                overflowY: "auto",
                background: "var(--color-bg-subtle)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
              }}
              className="scroll-y"
            >
              {profile.muted.map((code) => (
                <li
                  key={code}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "4px 8px",
                    fontFamily: "var(--font-mono)",
                    fontSize: 11.5,
                    color: "var(--color-body)",
                  }}
                >
                  <span>{code}</span>
                  <button
                    className="btn-ghost"
                    onClick={() => unmuteCourse(code)}
                    style={{ padding: "0 6px", fontSize: 11 }}
                    aria-label={`Unhide ${code}`}
                  >
                    Unhide
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div style={styles.legend}>
          <div style={styles.legendRow}>
            <div style={{ ...styles.legendSwatch, borderTopColor: "var(--color-purple)" }} />
            <span style={{ color: "var(--color-label)" }}>AND — required</span>
          </div>
          <div style={styles.legendRow}>
            <div
              style={{
                ...styles.legendSwatch,
                borderTopColor: "var(--color-purple)",
                borderTopStyle: "dashed",
              }}
            />
            <span style={{ color: "var(--color-label)" }}>OR — alternative path</span>
          </div>
          <div style={styles.legendRow}>
            <div style={{ ...styles.legendSwatch, borderTopColor: "var(--color-success)" }} />
            <span style={{ color: "var(--color-label)" }}>Unlocked by your completed</span>
          </div>
        </div>

        {focusCourse && (
          <section style={styles.focusCard} aria-label="Focused course details">
            <div style={styles.focusCode}>{focusCourse.code}</div>
            <div style={styles.focusTitle}>{focusCourse.title}</div>
            {focusCourse.units && <span style={styles.metaPill}>{focusCourse.units} units</span>}
            {focusCourse.notes && <div style={styles.notesBadge}>{focusCourse.notes}</div>}
            <div style={{ marginTop: 12 }}>
              {mutedSet.has(focusCourse.code) ? (
                <button
                  className="btn-ghost"
                  onClick={() => unmuteCourse(focusCourse.code)}
                  style={{ padding: "4px 10px", fontSize: 11 }}
                >
                  Unhide this course
                </button>
              ) : (
                <button
                  className="btn-ghost"
                  onClick={() => muteCourse(focusCourse.code)}
                  style={{ padding: "4px 10px", fontSize: 11 }}
                >
                  Hide this course
                </button>
              )}
            </div>
            {focusCourse.raw_prereq_text && (
              <details style={styles.details}>
                <summary
                  style={{ cursor: "pointer", color: "var(--color-label)", fontWeight: 500 }}
                >
                  Raw prereq text
                </summary>
                <p style={styles.rawText}>{focusCourse.raw_prereq_text}</p>
              </details>
            )}
            {focusCourse.description && (
              <details style={styles.details}>
                <summary
                  style={{ cursor: "pointer", color: "var(--color-label)", fontWeight: 500 }}
                >
                  Description
                </summary>
                <p style={{ marginTop: 6, fontSize: 12, lineHeight: 1.5 }}>
                  {focusCourse.description}
                </p>
              </details>
            )}
          </section>
        )}

        <p style={{ ...styles.intro, marginTop: 24, fontSize: 11 }}>
          Data scraped from{" "}
          <a
            href="https://catalog.ucsd.edu"
            target="_blank"
            rel="noreferrer"
            style={{ color: "var(--color-purple)", textDecoration: "none" }}
          >
            catalog.ucsd.edu
          </a>{" "}
          ·{" "}
          <a
            href="https://github.com/CuteSurtr/prereq-dependency"
            target="_blank"
            rel="noreferrer"
            style={{ color: "var(--color-purple)", textDecoration: "none" }}
          >
            source
          </a>
        </p>
      </aside>
      <main className="main-graph">
        <Graph
          graph={graph}
          focusCode={focus}
          completed={completed}
          onSelectCourse={onSelectCourse}
          expandDepth={expandDepth}
        />
      </main>
    </div>
  );
}
