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
  // in flat slot form — in that case, fall back to `prereq_groups`.
  prereq_slots: string[][] | null;
  coreq_groups: string[][];
  recommended_groups: string[][];
};

export type GraphData = {
  courses: Record<string, Course>;
  unlocks: Record<string, string[]>;
};
