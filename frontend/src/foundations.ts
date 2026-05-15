
export const FOUNDATION_CODES: ReadonlySet<string> = new Set<string>([
  "MATH 3C",
  "MATH 4C",
  "MATH 10A", "MATH 10B", "MATH 10C",
  "MATH 11",
  "MATH 15A",
  "MATH 18",
  "MATH 20A", "MATH 20B", "MATH 20C", "MATH 20D", "MATH 20E", "MATH 20F",
  "MATH 31AH", "MATH 31BH", "MATH 31CH",

  "PHYS 1A", "PHYS 1B", "PHYS 1C",
  "PHYS 2A", "PHYS 2B", "PHYS 2C", "PHYS 2D",
  "PHYS 2BL", "PHYS 2CL", "PHYS 2DL",
  "PHYS 4A", "PHYS 4B", "PHYS 4C", "PHYS 4D", "PHYS 4E",

  "CHEM 6A", "CHEM 6B", "CHEM 6C",
  "CHEM 6AH", "CHEM 6BH", "CHEM 6CH",
  "CHEM 7L", "CHEM 7LM",
  "CHEM 40A", "CHEM 40B", "CHEM 40C",
  "CHEM 41A", "CHEM 41B", "CHEM 41C",

  "BILD 1", "BILD 2", "BILD 3", "BILD 4",
]);

export function isFoundationCourse(code: string): boolean {
  return FOUNDATION_CODES.has(code);
}
