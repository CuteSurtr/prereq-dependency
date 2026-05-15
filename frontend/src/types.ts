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
  prereq_slots: string[][] | null;
  coreq_groups: string[][];
  recommended_groups: string[][];
  required_standing: Standing | null;
  restricted_to_majors: string[] | null;
};

export type GraphData = {
  courses: Record<string, Course>;
  unlocks: Record<string, string[]>;
};
