import type { GraphData } from "./types";

export type MajorEntry = {
  code: string;
  name: string;
  department: string;
};

let cached: Promise<GraphData> | null = null;
let cachedMajors: Promise<MajorEntry[]> | null = null;

export function loadGraph(): Promise<GraphData> {
  if (!cached) {
    const url = `${import.meta.env.BASE_URL}graph.json`.replace(/\/+/g, "/");
    cached = fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(`Failed to load graph.json: ${r.status}`);
        return r.json() as Promise<GraphData>;
      })
      .catch((e) => {
        cached = null;
        throw e;
      });
  }
  return cached;
}

export function loadMajors(): Promise<MajorEntry[]> {
  if (!cachedMajors) {
    const url = `${import.meta.env.BASE_URL}majors.json`.replace(/\/+/g, "/");
    cachedMajors = fetch(url)
      .then((r) => (r.ok ? (r.json() as Promise<MajorEntry[]>) : []))
      .then((rows) => {
        const seen = new Set<string>();
        const out: MajorEntry[] = [];
        for (const m of rows) {
          if (seen.has(m.code)) continue;
          seen.add(m.code);
          out.push(m);
        }
        return out;
      })
      .catch(() => []);
  }
  return cachedMajors;
}

export function isEligible(courseCode: string, completed: Set<string>, graph: GraphData): boolean {
  const course = graph.courses[courseCode];
  if (!course) return false;
  if (completed.has(courseCode)) return false;
  if (course.prereq_groups.length === 0) return true;
  return course.prereq_groups.some((g) => g.every((p) => completed.has(p)));
}
