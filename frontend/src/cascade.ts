import type { Course, GraphData } from "./types";

/**
 * For each course, return the set of courses you are guaranteed to take on
 * the way to satisfying its prereqs, regardless of which OR alternatives you
 * pick. This is the "mandatory ancestors" set.
 *
 * Uses `prereq_slots` when available; falls back to `prereq_groups` (DNF)
 * when the parser couldn't factor the prose into clean slots.
 */
export function computeMandatoryAncestors(
  graph: GraphData,
): Map<string, Set<string>> {
  const memo = new Map<string, Set<string>>();
  const visiting = new Set<string>();

  const compute = (code: string): Set<string> => {
    const cached = memo.get(code);
    if (cached) return cached;
    if (visiting.has(code)) return new Set();
    visiting.add(code);

    const course: Course | undefined = graph.courses[code];
    if (!course) {
      visiting.delete(code);
      const empty = new Set<string>();
      memo.set(code, empty);
      return empty;
    }

    let result: Set<string>;
    const slots = course.prereq_slots;
    if (slots !== null) {
      // Slots are AND-joined. For each slot, the mandatory contribution is
      // the intersection over alts of ({alt} ∪ ancestors(alt)).
      result = new Set();
      for (const slot of slots) {
        if (slot.length === 0) continue;
        let slotMandatory: Set<string> | null = null;
        for (const alt of slot) {
          const altSet = new Set<string>([alt]);
          for (const a of compute(alt)) altSet.add(a);
          if (slotMandatory === null) {
            slotMandatory = altSet;
          } else {
            const next = new Set<string>();
            for (const c of slotMandatory) if (altSet.has(c)) next.add(c);
            slotMandatory = next;
          }
        }
        if (slotMandatory) {
          for (const c of slotMandatory) result.add(c);
        }
      }
    } else {
      // Unfactored: each DNF group is an alt-satisfying-set. Mandatory =
      // intersection over groups of (group ∪ ancestors(group)).
      const groups = course.prereq_groups;
      if (!groups || groups.length === 0) {
        result = new Set();
      } else {
        let intersection: Set<string> | null = null;
        for (const group of groups) {
          const gSet = new Set<string>(group);
          for (const c of group) {
            for (const a of compute(c)) gSet.add(a);
          }
          if (intersection === null) {
            intersection = gSet;
          } else {
            const next = new Set<string>();
            for (const c of intersection) if (gSet.has(c)) next.add(c);
            intersection = next;
          }
        }
        result = intersection ?? new Set();
      }
    }

    visiting.delete(code);
    memo.set(code, result);
    return result;
  };

  for (const code of Object.keys(graph.courses)) compute(code);
  return memo;
}

/**
 * For each course, return the set of direct prereqs that are made redundant
 * by other direct prereqs (i.e., some other direct prereq already requires
 * them transitively).
 */
export function computeRedundantDirects(
  graph: GraphData,
): Map<string, Set<string>> {
  const mandatory = computeMandatoryAncestors(graph);
  const out = new Map<string, Set<string>>();

  for (const [code, course] of Object.entries(graph.courses)) {
    const directs = new Set<string>();
    if (course.prereq_slots !== null) {
      for (const slot of course.prereq_slots) {
        for (const a of slot) directs.add(a);
      }
    } else {
      for (const g of course.prereq_groups) {
        for (const a of g) directs.add(a);
      }
    }
    if (directs.size < 2) continue;

    const redundant = new Set<string>();
    for (const p of directs) {
      for (const q of directs) {
        if (q === p) continue;
        if (mandatory.get(q)?.has(p)) {
          redundant.add(p);
          break;
        }
      }
    }
    if (redundant.size > 0) out.set(code, redundant);
  }
  return out;
}
