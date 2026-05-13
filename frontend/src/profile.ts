export type Standing = "frosh" | "soph" | "junior" | "senior" | "graduate";

export type Profile = {
  picks: Record<string, Record<number, string>>;
  muted: string[];
  myDepartments: string[];
  hideCascading: boolean;
  hideOutOfDept: boolean;
  myStanding: Standing | null;
  hideAboveStanding: boolean;
};

const STORAGE_KEY = "prereq-profile-v1";

const EMPTY_PROFILE: Profile = {
  picks: {},
  muted: [],
  myDepartments: [],
  hideCascading: false,
  hideOutOfDept: false,
  myStanding: null,
  hideAboveStanding: false,
};

const VALID_STANDINGS: ReadonlySet<string> = new Set([
  "frosh",
  "soph",
  "junior",
  "senior",
  "graduate",
]);

export function loadProfile(): Profile {
  if (typeof localStorage === "undefined") return EMPTY_PROFILE;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return EMPTY_PROFILE;
    const parsed = JSON.parse(raw) as Partial<Profile> | null;
    if (!parsed || typeof parsed !== "object") return EMPTY_PROFILE;
    return {
      picks:
        parsed.picks && typeof parsed.picks === "object"
          ? (parsed.picks as Record<string, Record<number, string>>)
          : {},
      muted: Array.isArray(parsed.muted) ? parsed.muted : [],
      myDepartments: Array.isArray(parsed.myDepartments)
        ? parsed.myDepartments
        : [],
      hideCascading: typeof parsed.hideCascading === "boolean" ? parsed.hideCascading : false,
      hideOutOfDept:
        typeof parsed.hideOutOfDept === "boolean" ? parsed.hideOutOfDept : false,
      myStanding:
        typeof parsed.myStanding === "string" && VALID_STANDINGS.has(parsed.myStanding)
          ? (parsed.myStanding as Standing)
          : null,
      hideAboveStanding:
        typeof parsed.hideAboveStanding === "boolean" ? parsed.hideAboveStanding : false,
    };
  } catch {
    return EMPTY_PROFILE;
  }
}

const STANDING_RANK: Record<Standing, number> = {
  frosh: 1,
  soph: 2,
  junior: 3,
  senior: 4,
  graduate: 5,
};

const REQUIRED_RANK: Record<"junior" | "senior" | "graduate", number> = {
  junior: 3,
  senior: 4,
  graduate: 5,
};

/** True iff the user with `myStanding` is allowed to take a course requiring
 *  `required`. */
export function meetsStanding(
  myStanding: Standing | null,
  required: "junior" | "senior" | "graduate" | null,
): boolean {
  if (!required) return true;
  if (!myStanding) return false;
  return STANDING_RANK[myStanding] >= REQUIRED_RANK[required];
}

export function saveProfile(p: Profile): void {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(p));
  } catch {
    // quota or private-mode: silently drop persistence
  }
}

export function totalPicks(p: Profile): number {
  return Object.values(p.picks).reduce(
    (sum, slots) => sum + Object.keys(slots).length,
    0,
  );
}
