export type Standing = "junior" | "senior" | "graduate";

export type Course = {
  code: string;
  title: string;
  department: string;
  units: string | null;
  description: string | null;
  raw_prereq_text: string | null;
  notes: string | null;
  prereq_groups: string[][];
  // Factored AND-of-OR slots. Each inner array is a list of OR-alternatives;
  // the outer list is AND-joined. Null when the prereq AST can't be expressed
  // in flat slot form: in that case, fall back to `prereq_groups`.
  prereq_slots: string[][] | null;
  coreq_groups: string[][];
  recommended_groups: string[][];
  // Minimum class standing the course requires, derived from prose markers
  // (e.g. "graduate standing", "junior or senior standing") plus course-number
  // convention (200+ = graduate). Null = no detectable restriction.
  required_standing: Standing | null;
  // Major codes the course is restricted to (e.g. ["CS25", "CS26", "CS27"]).
  // Null when the catalog lists no explicit major-code restriction.
  restricted_to_majors: string[] | null;
};

export type GraphData = {
  courses: Record<string, Course>;
  unlocks: Record<string, string[]>;
};
