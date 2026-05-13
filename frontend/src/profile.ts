export type Profile = {
  picks: Record<string, Record<number, string>>;
  muted: string[];
  myDepartments: string[];
  hideCascading: boolean;
};

const STORAGE_KEY = "prereq-profile-v1";

const EMPTY_PROFILE: Profile = {
  picks: {},
  muted: [],
  myDepartments: [],
  hideCascading: false,
};

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
    };
  } catch {
    return EMPTY_PROFILE;
  }
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
