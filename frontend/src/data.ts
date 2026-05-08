import type { GraphData } from "./types";

let cached: Promise<GraphData> | null = null;

export function loadGraph(): Promise<GraphData> {
  if (!cached) {
    cached = fetch("/graph.json").then((r) => {
      if (!r.ok) throw new Error(`Failed to load graph.json: ${r.status}`);
      return r.json() as Promise<GraphData>;
    });
  }
  return cached;
}

export function isEligible(courseCode: string, completed: Set<string>, graph: GraphData): boolean {
  const course = graph.courses[courseCode];
  if (!course) return false;
  if (completed.has(courseCode)) return false; // already done
  if (course.prereq_groups.length === 0) return true; // no prereqs
  return course.prereq_groups.some((g) => g.every((p) => completed.has(p)));
}
