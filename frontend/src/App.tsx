import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Graph } from "./Graph";
import { loadGraph } from "./data";
import { useProfile } from "./ProfileContext";
import { totalPicks, type Standing } from "./profile";
import { loadMajors, type MajorEntry } from "./data";
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

const STANDING_OPTIONS: { value: Standing | ""; label: string }[] = [
  { value: "", label: "-" },
  { value: "frosh", label: "Freshman" },
  { value: "soph", label: "Sophomore" },
  { value: "junior", label: "Junior" },
  { value: "senior", label: "Senior" },
  { value: "graduate", label: "Graduate" },
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
    setHideCascading,
    setHideOutOfDept,
    setMyStanding,
    setHideAboveStanding,
    setMyMajorCodes,
    setHideMajorRestricted,
    setOrLabels,
  } = useProfile();
  const [deptsRaw, setDeptsRaw] = useState<string>(() =>
    profile.myDepartments.join(", "),
  );
  const [majorPickerInput, setMajorPickerInput] = useState<string>("");
  const [majorPickerOpen, setMajorPickerOpen] = useState<boolean>(false);
  const majorPickerRef = useRef<HTMLDivElement>(null);
  const [majors, setMajors] = useState<MajorEntry[]>([]);
  const pickCount = totalPicks(profile);
  const mutedSet = useMemo(() => new Set(profile.muted), [profile.muted]);
  const majorByCode = useMemo(() => {
    const m = new Map<string, MajorEntry>();
    for (const row of majors) m.set(row.code, row);
    return m;
  }, [majors]);

  useEffect(() => {
    loadMajors().then(setMajors).catch(() => setMajors([]));
  }, []);

  useEffect(() => {
    if (!majorPickerOpen) return;
    const onDocMouseDown = (e: MouseEvent) => {
      if (
        majorPickerRef.current &&
        !majorPickerRef.current.contains(e.target as Node)
      ) {
        setMajorPickerOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocMouseDown);
    return () => document.removeEventListener("mousedown", onDocMouseDown);
  }, [majorPickerOpen]);

  const pickedMajorSet = useMemo(
    () => new Set(profile.myMajorCodes),
    [profile.myMajorCodes],
  );
  const filteredMajors = useMemo(() => {
    const q = majorPickerInput.trim().toLowerCase();
    const base = majors.filter((m) => !pickedMajorSet.has(m.code));
    if (!q) return base;
    return base.filter(
      (m) =>
        m.code.toLowerCase().includes(q) ||
        m.name.toLowerCase().includes(q) ||
        m.department.toLowerCase().includes(q),
    );
  }, [majors, majorPickerInput, pickedMajorSet]);

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

  const addMajorCode = useCallback(
    (raw: string) => {
      const m = raw.toUpperCase().match(/[A-Z]{2}\s*\d{2}/);
      if (!m) return false;
      const code = m[0].replace(/\s+/g, "");
      if (profile.myMajorCodes.includes(code)) {
        setMajorPickerInput("");
        return true;
      }
      setMyMajorCodes([...profile.myMajorCodes, code]);
      setMajorPickerInput("");
      return true;
    },
    [profile.myMajorCodes, setMyMajorCodes],
  );

  const removeMajorCode = useCallback(
    (code: string) => {
      setMyMajorCodes(profile.myMajorCodes.filter((c) => c !== code));
    },
    [profile.myMajorCodes, setMyMajorCodes],
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
            placeholder="Paste a list: e.g. MATH 20A, MATH 20B, CSE 11"
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
          <label style={labelStyle} htmlFor="standing-select">
            My class standing
          </label>
          <select
            id="standing-select"
            value={profile.myStanding ?? ""}
            onChange={(e) =>
              setMyStanding((e.target.value || null) as Standing | null)
            }
            style={{ fontSize: 12 }}
          >
            {STANDING_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        <div style={styles.field}>
          <label style={labelStyle} htmlFor="major-input">
            My major(s)
          </label>
          {profile.myMajorCodes.length > 0 && (
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 4,
                marginBottom: 6,
              }}
            >
              {profile.myMajorCodes.map((code) => {
                const m = majorByCode.get(code);
                return (
                  <span
                    key={code}
                    title={m ? `${m.name} (${m.department})` : "Unknown code"}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                      padding: "2px 4px 2px 8px",
                      fontSize: 11,
                      fontFamily: "var(--font-mono)",
                      color: "var(--color-purple)",
                      background: "var(--color-purple-tint)",
                      borderRadius: "var(--radius-sm)",
                      lineHeight: 1.3,
                    }}
                  >
                    {code}
                    <button
                      onClick={() => removeMajorCode(code)}
                      aria-label={`Remove ${code}`}
                      style={{
                        background: "transparent",
                        border: 0,
                        padding: "0 4px",
                        color: "var(--color-purple)",
                        cursor: "pointer",
                        fontSize: 13,
                        lineHeight: 1,
                      }}
                    >
                      ×
                    </button>
                  </span>
                );
              })}
            </div>
          )}
          <div ref={majorPickerRef} style={{ position: "relative" }}>
            <input
              id="major-input"
              data-testid="major-input"
              value={majorPickerInput}
              onFocus={() => setMajorPickerOpen(true)}
              onChange={(e) => {
                setMajorPickerInput(e.target.value);
                setMajorPickerOpen(true);
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  if (filteredMajors.length > 0) {
                    addMajorCode(filteredMajors[0].code);
                  } else {
                    addMajorCode(majorPickerInput);
                  }
                } else if (e.key === "Escape") {
                  setMajorPickerOpen(false);
                }
              }}
              placeholder={
                majors.length
                  ? "Search by name or code (e.g. 'Probability' or 'CS27')"
                  : "Code only (e.g. CS27)"
              }
              style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
            />
            {majorPickerOpen && majors.length > 0 && (
              <ul
                role="listbox"
                style={{
                  position: "absolute",
                  top: "100%",
                  left: 0,
                  right: 0,
                  marginTop: 4,
                  maxHeight: 260,
                  overflowY: "auto",
                  background: "var(--color-bg)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-md)",
                  boxShadow: "var(--shadow-elevated)",
                  listStyle: "none",
                  padding: 0,
                  zIndex: 20,
                }}
                className="scroll-y"
              >
                {filteredMajors.length === 0 ? (
                  <li
                    style={{
                      padding: "10px 12px",
                      fontSize: 12,
                      color: "var(--color-body)",
                    }}
                  >
                    No match. Press Enter to add{" "}
                    <code style={{ fontFamily: "var(--font-mono)" }}>
                      {majorPickerInput.toUpperCase()}
                    </code>{" "}
                    as a custom code.
                  </li>
                ) : (
                  filteredMajors.map((m) => (
                    <li key={m.code}>
                      <button
                        type="button"
                        onClick={() => {
                          addMajorCode(m.code);
                          setMajorPickerOpen(false);
                        }}
                        style={{
                          display: "block",
                          width: "100%",
                          textAlign: "left",
                          padding: "8px 12px",
                          border: "none",
                          background: "transparent",
                          cursor: "pointer",
                          fontSize: 12,
                          lineHeight: 1.35,
                        }}
                        className="search-result-btn"
                      >
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            color: "var(--color-purple)",
                            fontWeight: 500,
                            marginRight: 8,
                          }}
                        >
                          {m.code}
                        </span>
                        <span style={{ color: "var(--color-label)" }}>{m.name}</span>
                        <div
                          style={{
                            fontSize: 10.5,
                            color: "var(--color-body)",
                            marginTop: 2,
                            letterSpacing: "0.02em",
                          }}
                        >
                          {m.department}
                        </div>
                      </button>
                    </li>
                  ))
                )}
              </ul>
            )}
          </div>
        </div>

        <div style={{ ...styles.field, marginBottom: 14, gap: 6 }}>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: 12,
              color:
                profile.myStanding === null
                  ? "var(--color-body-muted, var(--color-body))"
                  : "var(--color-label)",
              cursor: profile.myStanding === null ? "not-allowed" : "pointer",
              opacity: profile.myStanding === null ? 0.55 : 1,
            }}
            title={
              profile.myStanding === null
                ? "Set My class standing first"
                : "Courses needing higher standing disappear from the graph."
            }
          >
            <input
              type="checkbox"
              checked={profile.hideAboveStanding}
              disabled={profile.myStanding === null}
              onChange={(e) => setHideAboveStanding(e.target.checked)}
              style={{ accentColor: "var(--color-purple)" }}
            />
            <span>
              Hide courses above my standing
            </span>
          </label>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: 12,
              color:
                profile.myMajorCodes.length === 0
                  ? "var(--color-body-muted, var(--color-body))"
                  : "var(--color-label)",
              cursor:
                profile.myMajorCodes.length === 0 ? "not-allowed" : "pointer",
              opacity: profile.myMajorCodes.length === 0 ? 0.55 : 1,
            }}
            title={
              profile.myMajorCodes.length === 0
                ? "Set My major code(s) first"
                : "Courses restricted to majors not in your list disappear from the graph."
            }
          >
            <input
              type="checkbox"
              checked={profile.hideMajorRestricted}
              disabled={profile.myMajorCodes.length === 0}
              onChange={(e) => setHideMajorRestricted(e.target.checked)}
              style={{ accentColor: "var(--color-purple)" }}
            />
            <span>
              Hide courses my major can&apos;t take
            </span>
          </label>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: 12,
              color: "var(--color-label)",
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              checked={profile.hideCascading}
              onChange={(e) => setHideCascading(e.target.checked)}
              style={{ accentColor: "var(--color-purple)" }}
            />
            <span>
              Hide redundant prereqs{" "}
              <span style={{ color: "var(--color-body)", fontSize: 11 }}>
                (cascading)
              </span>
            </span>
          </label>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: 12,
              color: "var(--color-label)",
              cursor: "pointer",
            }}
            title="Place an OR badge between adjacent alternatives in a slot. Easier to read than just the dashed fan-in lines."
          >
            <input
              type="checkbox"
              checked={profile.orLabels}
              onChange={(e) => setOrLabels(e.target.checked)}
              style={{ accentColor: "var(--color-purple)" }}
            />
            <span>
              Compact OR layout{" "}
              <span style={{ color: "var(--color-body)", fontSize: 11 }}>
                (vertical stack)
              </span>
            </span>
          </label>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontSize: 12,
              color: profile.myDepartments.length === 0
                ? "var(--color-body-muted, var(--color-body))"
                : "var(--color-label)",
              cursor: profile.myDepartments.length === 0 ? "not-allowed" : "pointer",
              opacity: profile.myDepartments.length === 0 ? 0.55 : 1,
            }}
            title={
              profile.myDepartments.length === 0
                ? "Set My departments first"
                : "STEM foundation courses (MATH 20 series, PHYS 2/4, CHEM 6, BILD 1–4, intro programming) stay visible."
            }
          >
            <input
              type="checkbox"
              checked={profile.hideOutOfDept}
              disabled={profile.myDepartments.length === 0}
              onChange={(e) => setHideOutOfDept(e.target.checked)}
              style={{ accentColor: "var(--color-purple)" }}
            />
            <span>
              Hide out-of-dept{" "}
              <span style={{ color: "var(--color-body)", fontSize: 11 }}>
                (except STEM core)
              </span>
            </span>
          </label>
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
            placeholder='e.g. "CSE, MATH": empty means all'
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
            <span style={{ color: "var(--color-label)" }}>AND: required</span>
          </div>
          <div style={styles.legendRow}>
            <div
              style={{
                ...styles.legendSwatch,
                borderTopColor: "var(--color-purple)",
                borderTopStyle: "dashed",
              }}
            />
            <span style={{ color: "var(--color-label)" }}>OR: alternative path</span>
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
