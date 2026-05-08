export type Course = {
  code: string;
  title: string;
  department: string;
  units: string | null;
  description: string | null;
  raw_prereq_text: string | null;
  notes: string | null;
  prereq_groups: string[][];
  coreq_groups: string[][];
  recommended_groups: string[][];
};

export type GraphData = {
  courses: Record<string, Course>;
  unlocks: Record<string, string[]>;
};
