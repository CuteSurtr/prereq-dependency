import { useEffect, useMemo, useState } from "react";
import { Graph } from "./Graph";
import { loadGraph } from "./data";
import type { GraphData } from "./types";

const COURSE_CODE_RE = /\b[A-Z]{2,5}\s+\d+[A-Z]{0,3}\b/g;

function normalize(code: string): string {
  return code.replace(/\s+/g, " ").trim().toUpperCase();
}

function parseCompletedList(text: string): string[] {
  const found = text.toUpperCase().match(COURSE_CODE_RE) ?? [];
  return Array.from(new Set(found.map(normalize)));
}

export default function App() {
  const [graph, setGraph] = useState<GraphData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [focus, setFocus] = useState<string>("CSE 110");
  const [completedRaw, setCompletedRaw] = useState("");

  useEffect(() => {
    loadGraph()
      .then(setGraph)
      .catch((e) => setError(String(e)));
  }, []);

  const completed = useMemo(() => new Set(parseCompletedList(completedRaw)), [completedRaw]);

  const searchResults = useMemo(() => {
    if (!graph || query.trim().length < 2) return [];
    const q = query.toUpperCase();
    return Object.values(graph.courses)
      .filter((c) => c.code.includes(q) || c.title.toUpperCase().includes(q))
      .slice(0, 30);
  }, [graph, query]);

  const focusCourse = graph?.courses[focus];

  if (error) {
    return (
      <main style={{ padding: 24 }}>
        <h1>UCSD Prereq Graph</h1>
        <p style={{ color: "#dc2626" }}>Failed to load graph data: {error}</p>
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

  return (
    <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", height: "100vh" }}>
      <aside
        style={{
          padding: 16,
          borderRight: "1px solid #e2e8f0",
          overflowY: "auto",
          background: "#f8fafc",
        }}
      >
        <h1 style={{ fontSize: 18, margin: "0 0 4px" }}>UCSD Prereq Graph</h1>
        <p style={{ fontSize: 12, color: "#64748b", margin: "0 0 16px" }}>
          {Object.keys(graph.courses).length} courses across Tier 1 majors. Solid edges = AND
          (required). Dashed = OR alternatives.
        </p>

        <label style={{ fontSize: 12, fontWeight: 600 }}>Search course</label>
        <input
          data-testid="search-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='e.g. "MATH 20A" or "neural"'
          style={{
            width: "100%",
            padding: "6px 8px",
            margin: "4px 0 6px",
            border: "1px solid #cbd5e1",
            borderRadius: 4,
            fontSize: 13,
          }}
        />
        {searchResults.length > 0 && (
          <ul
            data-testid="search-results"
            style={{
              listStyle: "none",
              padding: 0,
              margin: "0 0 12px",
              maxHeight: 220,
              overflowY: "auto",
              border: "1px solid #e2e8f0",
              borderRadius: 4,
              background: "white",
            }}
          >
            {searchResults.map((c) => (
              <li key={c.code}>
                <button
                  onClick={() => {
                    setFocus(c.code);
                    setQuery("");
                  }}
                  style={{
                    display: "block",
                    width: "100%",
                    textAlign: "left",
                    padding: "6px 8px",
                    border: "none",
                    background: "transparent",
                    borderBottom: "1px solid #f1f5f9",
                    cursor: "pointer",
                    fontSize: 12,
                  }}
                >
                  <span style={{ fontWeight: 600 }}>{c.code}</span>{" "}
                  <span style={{ color: "#64748b" }}>{c.title}</span>
                </button>
              </li>
            ))}
          </ul>
        )}

        <label style={{ fontSize: 12, fontWeight: 600 }}>My completed courses</label>
        <textarea
          value={completedRaw}
          onChange={(e) => setCompletedRaw(e.target.value)}
          placeholder="Paste a list, e.g. MATH 20A, MATH 20B, CSE 11"
          rows={4}
          style={{
            width: "100%",
            padding: 6,
            margin: "4px 0 4px",
            border: "1px solid #cbd5e1",
            borderRadius: 4,
            fontSize: 12,
            fontFamily: "ui-monospace, monospace",
          }}
        />
        <div style={{ fontSize: 11, color: "#64748b", marginBottom: 16 }}>
          Recognized: {completed.size} course{completed.size === 1 ? "" : "s"}. Eligible-next
          courses are highlighted yellow on the graph; finished ones are green.
        </div>

        {focusCourse && (
          <section
            style={{
              borderTop: "1px solid #e2e8f0",
              paddingTop: 12,
              fontSize: 12,
              color: "#334155",
            }}
          >
            <div style={{ fontWeight: 700, fontSize: 14 }}>{focusCourse.code}</div>
            <div style={{ color: "#475569", margin: "2px 0 8px" }}>{focusCourse.title}</div>
            {focusCourse.units && (
              <div>
                <em>{focusCourse.units} units</em>
              </div>
            )}
            {focusCourse.raw_prereq_text && (
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: "pointer" }}>Raw prereq text</summary>
                <p
                  style={{
                    margin: "6px 0 0",
                    fontSize: 11,
                    fontFamily: "ui-monospace, monospace",
                    whiteSpace: "pre-wrap",
                    color: "#475569",
                  }}
                >
                  {focusCourse.raw_prereq_text}
                </p>
              </details>
            )}
            {focusCourse.notes && (
              <p style={{ marginTop: 8, color: "#92400e", fontSize: 11 }}>
                Notes: {focusCourse.notes}
              </p>
            )}
            {focusCourse.description && (
              <details style={{ marginTop: 8 }}>
                <summary style={{ cursor: "pointer" }}>Description</summary>
                <p style={{ marginTop: 6, fontSize: 11, color: "#475569" }}>
                  {focusCourse.description}
                </p>
              </details>
            )}
          </section>
        )}
      </aside>
      <main style={{ position: "relative" }}>
        <Graph
          graph={graph}
          focusCode={focus}
          completed={completed}
          onSelectCourse={(code) => {
            if (graph.courses[code]) setFocus(code);
          }}
        />
      </main>
    </div>
  );
}
