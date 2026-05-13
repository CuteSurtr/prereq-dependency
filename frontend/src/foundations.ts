// STEM foundation courses: the universal lower-division sequences that
// effectively every STEM major touches at some point. When the user enables
// "Hide out-of-department prereqs", these stay visible so the graph doesn't
// hide the genuine path through math / physics / chemistry / biology basics.
//
// Scope is deliberately tight: a CS student looking at COGS 108 should still
// see those CSE-intro prereqs disappear when they hide out-of-dept, because
// CSE 11 / CSE 8A / DSC 10 / MAE 8 are intro-programming alternatives that
// only matter to a specific major chain, not universal STEM core.
//
// What stays in the list:
//   - Engineering math: calculus, linear algebra, vector calc, diff eq, stats
//   - Calc-based physics (intro and majors variants)
//   - General + organic chemistry intro sequences
//   - Intro biology sequence (BILD 1–4)

export const FOUNDATION_CODES: ReadonlySet<string> = new Set<string>([
  // Math: engineering calculus and supporting basics
  "MATH 3C",
  "MATH 4C",
  "MATH 10A", "MATH 10B", "MATH 10C",
  "MATH 11",
  "MATH 15A",
  "MATH 18",
  "MATH 20A", "MATH 20B", "MATH 20C", "MATH 20D", "MATH 20E", "MATH 20F",
  "MATH 31AH", "MATH 31BH", "MATH 31CH",

  // Physics: classical mechanics, E&M, waves, intro quantum
  "PHYS 1A", "PHYS 1B", "PHYS 1C",
  "PHYS 2A", "PHYS 2B", "PHYS 2C", "PHYS 2D",
  "PHYS 2BL", "PHYS 2CL", "PHYS 2DL",
  "PHYS 4A", "PHYS 4B", "PHYS 4C", "PHYS 4D", "PHYS 4E",

  // Chemistry: general and organic intro sequences
  "CHEM 6A", "CHEM 6B", "CHEM 6C",
  "CHEM 6AH", "CHEM 6BH", "CHEM 6CH",
  "CHEM 7L", "CHEM 7LM",
  "CHEM 40A", "CHEM 40B", "CHEM 40C",
  "CHEM 41A", "CHEM 41B", "CHEM 41C",

  // Biology: full intro sequence
  "BILD 1", "BILD 2", "BILD 3", "BILD 4",
]);

export function isFoundationCourse(code: string): boolean {
  return FOUNDATION_CODES.has(code);
}
