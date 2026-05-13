import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { loadProfile, saveProfile, type Profile } from "./profile";

type ProfileCtx = {
  profile: Profile;
  setPick: (courseCode: string, slotIdx: number, alt: string) => void;
  clearPick: (courseCode: string, slotIdx: number) => void;
  clearAllPicks: () => void;
  muteCourse: (code: string) => void;
  unmuteCourse: (code: string) => void;
  clearAllMutes: () => void;
  setMyDepartments: (depts: string[]) => void;
};

const Ctx = createContext<ProfileCtx | null>(null);

export function ProfileProvider({ children }: { children: ReactNode }) {
  const [profile, setProfile] = useState<Profile>(() => loadProfile());

  useEffect(() => {
    saveProfile(profile);
  }, [profile]);

  const setPick = useCallback(
    (courseCode: string, slotIdx: number, alt: string) => {
      setProfile((p) => {
        const slots = { ...(p.picks[courseCode] ?? {}) };
        if (slots[slotIdx] === alt) return p;
        slots[slotIdx] = alt;
        return { ...p, picks: { ...p.picks, [courseCode]: slots } };
      });
    },
    [],
  );

  const clearPick = useCallback((courseCode: string, slotIdx: number) => {
    setProfile((p) => {
      const slots = { ...(p.picks[courseCode] ?? {}) };
      if (!(slotIdx in slots)) return p;
      delete slots[slotIdx];
      const picks = { ...p.picks };
      if (Object.keys(slots).length === 0) {
        delete picks[courseCode];
      } else {
        picks[courseCode] = slots;
      }
      return { ...p, picks };
    });
  }, []);

  const clearAllPicks = useCallback(() => {
    setProfile((p) => (Object.keys(p.picks).length === 0 ? p : { ...p, picks: {} }));
  }, []);

  const muteCourse = useCallback((code: string) => {
    setProfile((p) =>
      p.muted.includes(code) ? p : { ...p, muted: [...p.muted, code] },
    );
  }, []);

  const unmuteCourse = useCallback((code: string) => {
    setProfile((p) =>
      p.muted.includes(code)
        ? { ...p, muted: p.muted.filter((c) => c !== code) }
        : p,
    );
  }, []);

  const clearAllMutes = useCallback(() => {
    setProfile((p) => (p.muted.length === 0 ? p : { ...p, muted: [] }));
  }, []);

  const setMyDepartments = useCallback((depts: string[]) => {
    setProfile((p) => {
      const next = Array.from(new Set(depts.map((d) => d.toUpperCase()).filter(Boolean)));
      next.sort();
      const sortedCurrent = [...p.myDepartments].sort();
      if (
        sortedCurrent.length === next.length &&
        sortedCurrent.every((d, i) => d === next[i])
      ) {
        return p;
      }
      return { ...p, myDepartments: next };
    });
  }, []);

  const value = useMemo<ProfileCtx>(
    () => ({
      profile,
      setPick,
      clearPick,
      clearAllPicks,
      muteCourse,
      unmuteCourse,
      clearAllMutes,
      setMyDepartments,
    }),
    [
      profile,
      setPick,
      clearPick,
      clearAllPicks,
      muteCourse,
      unmuteCourse,
      clearAllMutes,
      setMyDepartments,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useProfile(): ProfileCtx {
  const v = useContext(Ctx);
  if (!v) throw new Error("useProfile must be used inside ProfileProvider");
  return v;
}
