import type DagreType from "dagre";
import { useEffect, useMemo, useState } from "react";
import { computeRedundantDirects } from "./cascade";
import { FOUNDATION_CODES } from "./foundations";
import { meetsStanding } from "./profile";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  Position,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import { useProfile } from "./ProfileContext";
import type { Course, GraphData } from "./types";

type CourseNodeData = {
  code: string;
  title: string;
  variant: "focus" | "prereq" | "unlock";
  eligible: boolean;
  completed: boolean;
  picked?: boolean;
  pickable?: boolean;
  outOfDept?: boolean;
  mutedAlt?: boolean;
  /** Course's minimum class standing, when present. Drives the corner badge. */
  requiredStanding?: "junior" | "senior" | "graduate" | null;
  onClick: (code: string) => void;
  onPickInstead?: () => void;
};

type SlotJoinData = {
  label: string;
};

type HiddenAltsBadgeData = {
  label: string;
  onClick: () => void;
};

const COLORS = {
  navy: "#061b31",
  label: "#273951",
  body: "#64748d",
  purple: "#533afd",
  purpleSoft: "#d6d9fc",
  purpleLight: "#b9b9f9",
  border: "#e5edf5",
  bg: "#ffffff",
  bgSubtle: "#f6f9fc",
  successText: "#108c3d",
  successBg: "rgba(21, 190, 83, 0.15)",
  successBorder: "rgba(21, 190, 83, 0.45)",
  bodyMuted: "#94a3b8",
};

function CourseNode({ data }: NodeProps<CourseNodeData>) {
  const isFocus = data.variant === "focus";
  const isCompleted = data.completed;
  const isEligible = data.eligible && !isFocus;
  const isPicked = data.picked === true;
  const isOutOfDept = data.outOfDept === true && !isFocus;
  const isMutedAlt = data.mutedAlt === true;

  const bg = isCompleted
    ? COLORS.successBg
    : isFocus
      ? "linear-gradient(180deg, #ffffff 0%, #f6f9fc 100%)"
      : isOutOfDept
        ? COLORS.bgSubtle
        : "#ffffff";

  const border = isFocus
    ? `2px solid ${COLORS.purple}`
    : isCompleted
      ? `1px solid ${COLORS.successBorder}`
      : isPicked
        ? `1.5px solid ${COLORS.purple}`
        : isOutOfDept
          ? `1px dashed ${COLORS.bodyMuted}`
          : isEligible
            ? `1px solid ${COLORS.purpleLight}`
            : `1px solid ${COLORS.border}`;

  const shadow = isFocus
    ? "rgba(50,50,93,0.25) 0px 30px 45px -30px, rgba(0,0,0,0.1) 0px 18px 36px -18px"
    : isPicked
      ? "rgba(83,58,253,0.22) 0px 8px 18px -8px, rgba(23,23,23,0.06) 0px 3px 6px"
      : isEligible
        ? "rgba(83,58,253,0.18) 0px 8px 18px -8px, rgba(23,23,23,0.06) 0px 3px 6px"
        : "rgba(23,23,23,0.06) 0px 3px 6px";

  const codeColor = isCompleted
    ? COLORS.successText
    : isFocus
      ? COLORS.navy
      : isPicked || isEligible
        ? COLORS.purple
        : COLORS.label;

  const titleColor = isFocus ? COLORS.label : COLORS.body;

  const handleClick = () => {
    if (isMutedAlt) return;
    if (isFocus) return;
    if (data.onPickInstead) {
      data.onPickInstead();
    } else {
      data.onClick(data.code);
    }
  };

  const cardOpacity = isMutedAlt ? 0.4 : isOutOfDept ? 0.75 : 1;
  const cardCursor = isMutedAlt
    ? "not-allowed"
    : isFocus
      ? "default"
      : "pointer";

  return (
    <div
      onClick={handleClick}
      title={
        isMutedAlt
          ? "Hidden — unhide from the sidebar to use this alternative"
          : data.pickable
            ? isPicked
              ? "Picked — click to keep, or pick another alternative"
              : "Click to pick this alternative"
            : undefined
      }
      style={{
        padding: "10px 14px",
        borderRadius: 6,
        border,
        background: bg,
        minWidth: 140,
        maxWidth: 220,
        cursor: cardCursor,
        boxShadow: shadow,
        transition: "transform 120ms ease, box-shadow 120ms ease",
        position: "relative",
        opacity: cardOpacity,
        textDecoration: isMutedAlt ? "line-through" : undefined,
      }}
      onMouseEnter={(e) => {
        if (!isMutedAlt && !isFocus) e.currentTarget.style.transform = "translateY(-1px)";
      }}
      onMouseLeave={(e) => {
        if (!isMutedAlt && !isFocus) e.currentTarget.style.transform = "none";
      }}
    >
      <Handle type="target" position={Position.Left} style={{ visibility: "hidden" }} />
      {data.requiredStanding && !isFocus && (
        <div
          style={{
            position: "absolute",
            top: -7,
            left: 8,
            padding: "1px 6px",
            background: "#ffffff",
            border: `1px solid ${COLORS.border}`,
            borderRadius: 999,
            fontSize: 9,
            fontWeight: 500,
            color: COLORS.body,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            fontFamily:
              "'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
            lineHeight: 1.4,
          }}
          title={
            data.requiredStanding === "graduate"
              ? "Graduate standing required"
              : data.requiredStanding === "senior"
                ? "Senior standing required"
                : "Junior+ standing required"
          }
        >
          {data.requiredStanding === "graduate"
            ? "Grad"
            : data.requiredStanding === "senior"
              ? "Sr+"
              : "Jr+"}
        </div>
      )}
      {isCompleted && (
        <div
          style={{
            position: "absolute",
            top: -6,
            right: -6,
            background: COLORS.successText,
            color: "#fff",
            width: 16,
            height: 16,
            borderRadius: "50%",
            fontSize: 10,
            fontWeight: 500,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 2px 4px rgba(16,140,61,0.3)",
          }}
          aria-hidden
        >
          ✓
        </div>
      )}
      {isPicked && !isCompleted && (
        <div
          style={{
            position: "absolute",
            top: -6,
            right: -6,
            background: COLORS.purple,
            color: "#fff",
            width: 16,
            height: 16,
            borderRadius: "50%",
            fontSize: 10,
            fontWeight: 500,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            boxShadow: "0 2px 4px rgba(83,58,253,0.3)",
          }}
          aria-label="Picked alternative"
          title="Picked"
        >
          ✓
        </div>
      )}
      <div
        style={{
          fontFamily:
            "'JetBrains Mono', 'SF Mono', 'Source Code Pro', Menlo, monospace",
          fontWeight: 500,
          fontSize: 12.5,
          color: codeColor,
          letterSpacing: 0,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {data.code}
      </div>
      <div
        style={{
          color: titleColor,
          fontSize: 11,
          lineHeight: 1.35,
          marginTop: 3,
          fontWeight: 300,
        }}
      >
        {data.title.length > 58 ? data.title.slice(0, 55) + "…" : data.title}
      </div>
      <Handle type="source" position={Position.Right} style={{ visibility: "hidden" }} />
    </div>
  );
}

function SlotJoinNode({ data }: NodeProps<SlotJoinData>) {
  return (
    <div
      style={{
        padding: "3px 10px",
        borderRadius: 999,
        background: COLORS.bg,
        border: `1px dashed ${COLORS.purpleLight}`,
        fontSize: 10,
        fontWeight: 500,
        color: COLORS.purple,
        letterSpacing: "0.04em",
        textTransform: "uppercase",
        fontFamily:
          "'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
        boxShadow: "rgba(83,58,253,0.10) 0px 2px 6px",
        position: "relative",
        whiteSpace: "nowrap",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ visibility: "hidden" }} />
      {data.label}
      <Handle type="source" position={Position.Right} style={{ visibility: "hidden" }} />
    </div>
  );
}

function HiddenAltsBadge({ data }: NodeProps<HiddenAltsBadgeData>) {
  return (
    <div
      onClick={data.onClick}
      title="Click to show all alternatives again"
      style={{
        padding: "3px 10px",
        borderRadius: 999,
        background: COLORS.bgSubtle,
        border: `1px solid ${COLORS.border}`,
        fontSize: 10,
        fontWeight: 500,
        color: COLORS.body,
        letterSpacing: "0.04em",
        textTransform: "uppercase",
        fontFamily:
          "'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
        cursor: "pointer",
        whiteSpace: "nowrap",
        transition: "background 120ms ease, color 120ms ease",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = "#ffffff";
        e.currentTarget.style.color = COLORS.purple;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = COLORS.bgSubtle;
        e.currentTarget.style.color = COLORS.body;
      }}
    >
      <Handle type="target" position={Position.Left} style={{ visibility: "hidden" }} />
      {data.label}
      <Handle type="source" position={Position.Right} style={{ visibility: "hidden" }} />
    </div>
  );
}

const NODE_TYPES = {
  course: CourseNode,
  slotJoin: SlotJoinNode,
  hiddenAlts: HiddenAltsBadge,
};

const ROW_H = 78;
const SLOT_GAP = 28;
const COL_X = { prereq: 0, join: 320, focus: 480, unlock: 820 };

export type GraphProps = {
  graph: GraphData;
  focusCode: string;
  completed: Set<string>;
  onSelectCourse: (code: string) => void;
  expandDepth: number;
};

const UNLOCK_CAP = 12;
const CHAIN_NODE_CAP = 160;
const CHAIN_NODE_W = 180;
const CHAIN_NODE_H = 64;

type ChainEdge = { source: string; target: string; kind: "and" | "or" };

function effectivePrereqs(
  course: Course,
  picks: Record<number, string>,
  mutedSet: Set<string>,
): { slot: string[]; kind: "and" | "or"; empty: boolean }[] {
  if (course.prereq_slots && course.prereq_slots.length > 0) {
    return course.prereq_slots.map((alts, slotIdx) => {
      const filtered = alts.filter((a) => !mutedSet.has(a));
      if (filtered.length === 0) return { slot: alts, kind: "and", empty: true };
      if (filtered.length === 1) return { slot: filtered, kind: "and", empty: false };
      const picked = picks[slotIdx];
      if (picked && filtered.includes(picked))
        return { slot: [picked], kind: "and", empty: false };
      return { slot: filtered, kind: "or", empty: false };
    });
  }
  if (course.prereq_groups.length === 0) return [];
  const seen = new Set<string>();
  const flat: string[] = [];
  course.prereq_groups.forEach((g) =>
    g.forEach((c) => {
      if (!seen.has(c)) {
        seen.add(c);
        flat.push(c);
      }
    }),
  );
  const filtered = flat.filter((c) => !mutedSet.has(c));
  return [
    {
      slot: filtered.length ? filtered : flat,
      kind: course.prereq_groups.length > 1 ? "or" : "and",
      empty: filtered.length === 0,
    },
  ];
}

function buildUpstreamChain(
  graph: GraphData,
  focusCode: string,
  picks: Record<string, Record<number, string>>,
  mutedSet: Set<string>,
  maxDepth: number,
): { courseCodes: string[]; edges: ChainEdge[]; truncated: boolean } {
  const courseCodes = new Set<string>([focusCode]);
  const edges: ChainEdge[] = [];
  const queue: { code: string; depth: number }[] = [{ code: focusCode, depth: 0 }];
  let truncated = false;

  while (queue.length > 0) {
    const { code, depth } = queue.shift()!;
    if (depth >= maxDepth) continue;
    if (courseCodes.size >= CHAIN_NODE_CAP) {
      truncated = true;
      break;
    }
    const course = graph.courses[code];
    if (!course) continue;
    const prereqs = effectivePrereqs(course, picks[code] ?? {}, mutedSet);
    for (const { slot, kind, empty } of prereqs) {
      if (empty) continue;
      for (const prereqCode of slot) {
        if (mutedSet.has(prereqCode)) continue;
        edges.push({ source: prereqCode, target: code, kind });
        if (!courseCodes.has(prereqCode)) {
          if (courseCodes.size >= CHAIN_NODE_CAP) {
            truncated = true;
            break;
          }
          courseCodes.add(prereqCode);
          queue.push({ code: prereqCode, depth: depth + 1 });
        }
      }
      if (truncated) break;
    }
  }

  return { courseCodes: Array.from(courseCodes), edges, truncated };
}

// dagre is lazy-loaded the first time the user opens the chain view. Keeps
// ~33KB of layout code out of the depth=1 critical path.
let dagreModule: typeof DagreType | null = null;
let dagreLoadPromise: Promise<typeof DagreType> | null = null;
function loadDagre(): Promise<typeof DagreType> {
  if (dagreModule) return Promise.resolve(dagreModule);
  if (!dagreLoadPromise) {
    dagreLoadPromise = import("dagre").then((m) => {
      dagreModule = (m.default ?? (m as unknown as typeof DagreType));
      return dagreModule;
    });
  }
  return dagreLoadPromise;
}

function layoutChain(
  courseCodes: string[],
  edges: ChainEdge[],
): Record<string, { x: number; y: number }> | null {
  if (!dagreModule) return null;
  const g = new dagreModule.graphlib.Graph();
  g.setGraph({ rankdir: "LR", ranksep: 90, nodesep: 18, marginx: 20, marginy: 20 });
  g.setDefaultEdgeLabel(() => ({}));
  for (const code of courseCodes) {
    g.setNode(code, { width: CHAIN_NODE_W, height: CHAIN_NODE_H });
  }
  const seenEdgePairs = new Set<string>();
  for (const e of edges) {
    const key = `${e.source}->${e.target}`;
    if (seenEdgePairs.has(key)) continue;
    seenEdgePairs.add(key);
    g.setEdge(e.source, e.target);
  }
  dagreModule.layout(g);
  const positions: Record<string, { x: number; y: number }> = {};
  for (const code of courseCodes) {
    const n = g.node(code);
    positions[code] = {
      x: n.x - CHAIN_NODE_W / 2,
      y: n.y - CHAIN_NODE_H / 2,
    };
  }
  return positions;
}

function GraphInner({
  graph,
  focusCode,
  completed,
  onSelectCourse,
  expandDepth,
}: GraphProps) {
  const reactFlow = useReactFlow();
  const { profile, setPick, clearPick } = useProfile();
  const [dagreReady, setDagreReady] = useState<boolean>(() => dagreModule !== null);

  useEffect(() => {
    if (expandDepth > 1 && !dagreReady) {
      loadDagre().then(() => setDagreReady(true));
    }
  }, [expandDepth, dagreReady]);

  useEffect(() => {
    const t = setTimeout(() => reactFlow.fitView({ padding: 0.2, duration: 250 }), 50);
    return () => clearTimeout(t);
  }, [focusCode, expandDepth, dagreReady, reactFlow]);

  const mutedSet = useMemo(() => new Set(profile.muted), [profile.muted]);
  const myDeptSet = useMemo(
    () => new Set(profile.myDepartments),
    [profile.myDepartments],
  );
  const redundantDirects = useMemo(
    () => (profile.hideCascading ? computeRedundantDirects(graph) : null),
    [graph, profile.hideCascading],
  );
  const cascadeSet = redundantDirects?.get(focusCode);

  // Strict dept hide: build a set of out-of-dept courses that should disappear
  // entirely. STEM foundation courses (MATH 20 series etc.) are exempt so
  // students still see the actual path through math/physics/chem/bio basics.
  const deptHiddenSet = useMemo(() => {
    if (!profile.hideOutOfDept || myDeptSet.size === 0) {
      return new Set<string>();
    }
    const hidden = new Set<string>();
    for (const [code, c] of Object.entries(graph.courses)) {
      if (!myDeptSet.has(c.department) && !FOUNDATION_CODES.has(code)) {
        hidden.add(code);
      }
    }
    return hidden;
  }, [graph, myDeptSet, profile.hideOutOfDept]);

  // Standing hide: when the user has set their standing and toggled the
  // filter, courses that require higher standing are stripped from view.
  const standingHiddenSet = useMemo(() => {
    if (!profile.hideAboveStanding || !profile.myStanding) {
      return new Set<string>();
    }
    const hidden = new Set<string>();
    for (const [code, c] of Object.entries(graph.courses)) {
      if (!meetsStanding(profile.myStanding, c.required_standing)) {
        hidden.add(code);
      }
    }
    return hidden;
  }, [graph, profile.myStanding, profile.hideAboveStanding]);

  const {
    nodes,
    edges,
    hiddenUnlockCount,
    chainTruncated,
    chainNodeCount,
    unreachable,
    spilloverCount,
  } = useMemo<{
    nodes: Node[];
    edges: Edge[];
    hiddenUnlockCount: number;
    chainTruncated: boolean;
    chainNodeCount: number;
    unreachable: boolean;
    spilloverCount: number;
  }>(() => {
    const focus = graph.courses[focusCode];
    if (!focus)
      return {
        nodes: [],
        edges: [],
        hiddenUnlockCount: 0,
        chainTruncated: false,
        chainNodeCount: 0,
        unreachable: false,
        spilloverCount: 0,
      };

    const isOutOfDept = (code: string): boolean => {
      if (myDeptSet.size === 0) return false;
      const c = graph.courses[code];
      return !!c && !myDeptSet.has(c.department);
    };

    const allUnlocks = graph.unlocks[focusCode] ?? [];
    const unlocks = allUnlocks.slice(0, UNLOCK_CAP);

    const nodes: Node[] = [];
    const edges: Edge[] = [];

    const isEligible = (code: string): boolean => {
      const c = graph.courses[code];
      if (!c) return false;
      if (completed.has(code)) return false;
      if (c.prereq_groups.length === 0) return true;
      return c.prereq_groups.some((g) => g.every((p) => completed.has(p)));
    };

    // ── Chain view (depth > 1) ──
    if (expandDepth > 1) {
      // For the chain BFS, combine user mutes with the strict-dept and
      // standing hidden sets so filtered courses don't appear anywhere in
      // the upstream chain when their respective toggles are on.
      const chainHidden =
        deptHiddenSet.size === 0 && standingHiddenSet.size === 0
          ? mutedSet
          : new Set<string>([
              ...mutedSet,
              ...deptHiddenSet,
              ...standingHiddenSet,
            ]);
      const { courseCodes, edges: chainEdges, truncated } = buildUpstreamChain(
        graph,
        focusCode,
        profile.picks,
        chainHidden,
        expandDepth,
      );
      const positions = layoutChain(courseCodes, chainEdges);
      if (!positions) {
        // dagre not loaded yet; render nothing until the lazy import resolves.
        return {
          nodes: [],
          edges: [],
          hiddenUnlockCount: 0,
          chainTruncated: false,
          chainNodeCount: 0,
          unreachable: false,
          spilloverCount: 0,
        };
      }
      let chainSpillover = 0;

      for (const code of courseCodes) {
        const c = graph.courses[code];
        const pos = positions[code] ?? { x: 0, y: 0 };
        const variant: CourseNodeData["variant"] =
          code === focusCode ? "focus" : "prereq";
        const outOfDept = isOutOfDept(code);
        if (variant !== "focus" && outOfDept) chainSpillover++;
        nodes.push({
          id: `c:${code}`,
          type: "course",
          position: pos,
          data: {
            code,
            title: c?.title ?? "(unknown)",
            variant,
            eligible: variant !== "focus" && isEligible(code),
            completed: completed.has(code),
            outOfDept,
            requiredStanding: c?.required_standing ?? null,
            onClick: onSelectCourse,
          },
        });
      }

      // Edges: dedupe by source/target/kind; OR-edges are dashed.
      const seenEdge = new Set<string>();
      for (const e of chainEdges) {
        const key = `${e.source}->${e.target}|${e.kind}`;
        if (seenEdge.has(key)) continue;
        seenEdge.add(key);
        const isOr = e.kind === "or";
        edges.push({
          id: `chain-${key}`,
          source: `c:${e.source}`,
          target: `c:${e.target}`,
          style: {
            stroke: isOr ? COLORS.purpleLight : COLORS.purple,
            strokeWidth: isOr ? 1.2 : 1.5,
            strokeDasharray: isOr ? "4,4" : undefined,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isOr ? COLORS.purpleLight : COLORS.purple,
            width: 14,
            height: 14,
          },
        });
      }

      const focusPrereqs = effectivePrereqs(focus, profile.picks[focusCode] ?? {}, mutedSet);
      const chainUnreachable = focusPrereqs.some((s) => s.empty);

      return {
        nodes,
        edges,
        hiddenUnlockCount: 0,
        chainTruncated: truncated,
        chainNodeCount: courseCodes.length,
        unreachable: chainUnreachable,
        spilloverCount: chainSpillover,
      };
    }

    const mkCourseNode = (
      code: string,
      x: number,
      y: number,
      variant: CourseNodeData["variant"],
      extra: Partial<CourseNodeData> = {},
    ): Node<CourseNodeData> => {
      const c = graph.courses[code];
      return {
        id: `c:${code}`,
        type: "course",
        position: { x, y },
        data: {
          code,
          title: c?.title ?? "(unknown)",
          variant,
          eligible: variant !== "focus" && isEligible(code),
          completed: completed.has(code),
          outOfDept: isOutOfDept(code),
          requiredStanding: c?.required_standing ?? null,
          onClick: onSelectCourse,
          ...extra,
        },
      };
    };

    const mkJoinNode = (
      id: string,
      x: number,
      y: number,
      label: string,
    ): Node<SlotJoinData> => ({
      id,
      type: "slotJoin",
      position: { x, y },
      data: { label },
      selectable: false,
      draggable: false,
    });

    const mkHiddenBadge = (
      id: string,
      x: number,
      y: number,
      label: string,
      onClick: () => void,
    ): Node<HiddenAltsBadgeData> => ({
      id,
      type: "hiddenAlts",
      position: { x, y },
      data: { label, onClick },
      selectable: false,
      draggable: false,
    });

    const mkAndEdge = (id: string, source: string): Edge => ({
      id,
      source,
      target: `c:${focusCode}`,
      label: "AND",
      labelStyle: {
        fontSize: 10,
        fill: COLORS.label,
        fontFamily:
          "'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
        fontWeight: 500,
        letterSpacing: "0.02em",
      },
      labelBgStyle: { fill: "#ffffff", stroke: COLORS.border, strokeWidth: 1 },
      labelBgPadding: [4, 6],
      labelBgBorderRadius: 4,
      style: { stroke: COLORS.purple, strokeWidth: 1.5 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: COLORS.purple,
        width: 16,
        height: 16,
      },
    });

    const slots = focus.prereq_slots;
    const useSlots = slots !== null && slots.length > 0;
    const picksForFocus = profile.picks[focusCode] ?? {};
    let slotUnreachable = false;
    let slotSpillover = 0;

    if (useSlots) {
      // Build the list of slots to actually render, preserving each slot's
      // original index (for pick state) even when intermediate slots are
      // skipped by cascade filtering.
      //
      // Order of filters:
      //  1. Mute filter — drop user-hidden alts. Empty slot ⇒ unreachable.
      //  2. Cascade filter — drop alts that are transitively implied by some
      //     other direct prereq (when "Hide redundant" is on). If every
      //     remaining alt is redundant, drop the slot entirely.
      type SlotRender = {
        origIdx: number;
        alts: string[];
        muted: boolean;
      };
      const slotRenders: SlotRender[] = [];
      let cascadeSlotsHidden = 0;
      for (let i = 0; i < slots.length; i++) {
        const original = slots[i];
        const afterMute = original.filter((a) => !mutedSet.has(a));
        if (afterMute.length === 0) {
          slotRenders.push({ origIdx: i, alts: original, muted: true });
          slotUnreachable = true;
          continue;
        }
        let alts = afterMute;
        if (cascadeSet && cascadeSet.size > 0) {
          const afterCascade = alts.filter((a) => !cascadeSet.has(a));
          if (afterCascade.length === 0) {
            cascadeSlotsHidden++;
            continue;
          }
          alts = afterCascade;
        }
        if (deptHiddenSet.size > 0) {
          const afterDept = alts.filter((a) => !deptHiddenSet.has(a));
          if (afterDept.length === 0) {
            // All remaining alts are out-of-dept non-foundation; drop slot.
            continue;
          }
          alts = afterDept;
        }
        if (standingHiddenSet.size > 0) {
          const afterStanding = alts.filter((a) => !standingHiddenSet.has(a));
          if (afterStanding.length === 0) {
            // All remaining alts require higher standing than the user; drop.
            continue;
          }
          alts = afterStanding;
        }
        slotRenders.push({ origIdx: i, alts, muted: false });
      }

      // Precompute slot heights. Picked slots get extra height for the
      // "+N hidden" badge.
      const renderedAlts: string[][] = slotRenders.map(({ alts, origIdx }) => {
        if (alts.length === 1) return alts;
        const picked = picksForFocus[origIdx];
        if (picked && alts.includes(picked)) return [picked];
        return alts;
      });
      const slotHeights = renderedAlts.map((rAlts, idx) => {
        const base = rAlts.length * ROW_H;
        const isCollapsedPick = slotRenders[idx].alts.length > 1 && rAlts.length === 1;
        return isCollapsedPick ? base + 36 : base;
      });
      const totalHeight =
        slotHeights.reduce((a, b) => a + b, 0) +
        SLOT_GAP * Math.max(0, slotRenders.length - 1);
      let yCursor = -totalHeight / 2;
      const seenCourseNode = new Set<string>();

      const spilloverSeen = new Set<string>();

      slotRenders.forEach(({ alts, muted: slotMuted, origIdx }, renderIdx) => {
        const slotIdx = origIdx;
        const slotH = slotHeights[renderIdx];
        const slotTop = yCursor;
        const slotCenter = slotTop + slotH / 2 - ROW_H / 2;
        const picked = picksForFocus[slotIdx];
        const isPicked = !slotMuted && alts.length > 1 && picked && alts.includes(picked);
        // Spillover only counts the alternatives the user is actually planning
        // to take: a picked slot contributes just the picked code; an
        // un-picked slot contributes every (un-muted) alternative because
        // any of them might be chosen.
        const altsForSpillover = isPicked ? [picked as string] : alts;
        for (const code of altsForSpillover) {
          if (
            !slotMuted &&
            !mutedSet.has(code) &&
            isOutOfDept(code) &&
            !spilloverSeen.has(code)
          ) {
            spilloverSeen.add(code);
            slotSpillover++;
          }
        }

        if (alts.length === 1) {
          const code = alts[0];
          if (!seenCourseNode.has(code)) {
            nodes.push(mkCourseNode(code, COL_X.prereq, slotCenter, "prereq"));
            seenCourseNode.add(code);
          }
          edges.push(mkAndEdge(`e-slot${slotIdx}-${code}-focus`, `c:${code}`));
        } else if (isPicked) {
          // Collapsed picked slot: only the picked alt + a "+N hidden" badge
          // (positioned below the card) that clears the pick when clicked.
          // The picked alt navigates on click (normal CourseNode behavior);
          // the badge is the affordance to undo the pick.
          const code = picked as string;
          const altY = slotCenter;
          if (!seenCourseNode.has(code)) {
            nodes.push(
              mkCourseNode(code, COL_X.prereq, altY, "prereq", {
                picked: true,
              }),
            );
            seenCourseNode.add(code);
          }
          const hiddenCount = alts.length - 1;
          nodes.push(
            mkHiddenBadge(
              `hidden:${slotIdx}`,
              COL_X.prereq + 8,
              altY + 72,
              `+${hiddenCount} hidden · change`,
              () => clearPick(focusCode, slotIdx),
            ),
          );
          edges.push(mkAndEdge(`e-slot${slotIdx}-picked-focus`, `c:${code}`));
        } else {
          // Expanded multi-alt slot: stack alternatives, route through join.
          // When the slot is fully muted, render the original alts dimmed and
          // strike-through, drop pick handlers, and label the join with the
          // hidden count so the user knows why the focus is unreachable.
          alts.forEach((code, j) => {
            const y = slotTop + j * ROW_H;
            if (!seenCourseNode.has(code)) {
              nodes.push(
                mkCourseNode(code, COL_X.prereq, y, "prereq", {
                  pickable: !slotMuted,
                  mutedAlt: slotMuted,
                  onPickInstead: slotMuted
                    ? undefined
                    : () => setPick(focusCode, slotIdx, code),
                }),
              );
              seenCourseNode.add(code);
            }
            edges.push({
              id: `e-slot${slotIdx}-${code}-join`,
              source: `c:${code}`,
              target: `slot:${slotIdx}`,
              style: {
                stroke: COLORS.purpleLight,
                strokeWidth: 1.2,
                strokeDasharray: "4,4",
                opacity: slotMuted ? 0.5 : 1,
              },
            });
          });
          const joinLabel = slotMuted
            ? `${alts.length} hidden`
            : `1 of ${alts.length}`;
          nodes.push(
            mkJoinNode(`slot:${slotIdx}`, COL_X.join, slotCenter, joinLabel),
          );
          edges.push(mkAndEdge(`e-slot${slotIdx}-join-focus`, `slot:${slotIdx}`));
        }
        yCursor += slotH + SLOT_GAP;
      });
    } else {
      // Legacy fan-in for unfactored prereqs (~16% of courses with prereqs).
      const prereqGroups = focus.prereq_groups;
      const flatPrereqs: string[] = [];
      const groupOfPrereq: Record<string, number[]> = {};
      prereqGroups.forEach((group, gi) => {
        group.forEach((c) => {
          if (mutedSet.has(c)) return;
          if (cascadeSet?.has(c)) return;
          if (deptHiddenSet.has(c)) return;
          if (standingHiddenSet.has(c)) return;
          if (!groupOfPrereq[c]) {
            groupOfPrereq[c] = [];
            flatPrereqs.push(c);
          }
          groupOfPrereq[c].push(gi);
        });
      });
      // Unreachable: every group must contain at least one un-muted course.
      const unreachableFanin =
        prereqGroups.length > 0 &&
        prereqGroups.every((g) => g.every((c) => mutedSet.has(c)));
      if (unreachableFanin) slotUnreachable = true;
      for (const code of flatPrereqs) {
        if (isOutOfDept(code)) slotSpillover++;
      }
      const isOr = prereqGroups.length > 1;
      flatPrereqs.forEach((code, i) => {
        const y = i * ROW_H - ((flatPrereqs.length - 1) * ROW_H) / 2;
        nodes.push(mkCourseNode(code, COL_X.prereq, y, "prereq"));
        const groups = groupOfPrereq[code];
        const labelText = isOr
          ? groups.length === 1
            ? `OR · group ${groups[0] + 1}`
            : `OR · groups ${groups.map((g) => g + 1).join(", ")}`
          : "AND";
        edges.push({
          id: `e-fanin-${code}-focus`,
          source: `c:${code}`,
          target: `c:${focusCode}`,
          label: labelText,
          labelStyle: {
            fontSize: 10,
            fill: COLORS.label,
            fontFamily:
              "'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
            fontWeight: 500,
            letterSpacing: "0.02em",
          },
          labelBgStyle: { fill: "#ffffff", stroke: COLORS.border, strokeWidth: 1 },
          labelBgPadding: [4, 6],
          labelBgBorderRadius: 4,
          style: {
            stroke: COLORS.purple,
            strokeWidth: 1.5,
            strokeDasharray: isOr ? "5,4" : undefined,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: COLORS.purple,
            width: 16,
            height: 16,
          },
        });
      });
    }

    nodes.push(mkCourseNode(focusCode, COL_X.focus, 0, "focus"));

    const visibleUnlocks = unlocks.filter(
      (code) =>
        !mutedSet.has(code) &&
        !deptHiddenSet.has(code) &&
        !standingHiddenSet.has(code),
    );
    visibleUnlocks.forEach((code, i) => {
      const y = i * ROW_H - ((visibleUnlocks.length - 1) * ROW_H) / 2;
      nodes.push(mkCourseNode(code, COL_X.unlock, y, "unlock"));
      const eligible = isEligible(code);
      const stroke = eligible ? COLORS.successText : COLORS.bodyMuted;
      edges.push({
        id: `e-unlock-${focusCode}-${code}`,
        source: `c:${focusCode}`,
        target: `c:${code}`,
        style: {
          stroke,
          strokeWidth: eligible ? 1.8 : 1.2,
          opacity: eligible ? 1 : 0.6,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: stroke,
          width: 16,
          height: 16,
        },
      });
    });

    return {
      nodes,
      edges,
      hiddenUnlockCount:
        Math.max(0, allUnlocks.length - unlocks.length) +
        (unlocks.length - visibleUnlocks.length),
      chainTruncated: false,
      chainNodeCount: 0,
      unreachable: slotUnreachable,
      spilloverCount: slotSpillover,
    };
  }, [
    graph,
    focusCode,
    completed,
    onSelectCourse,
    profile.picks,
    mutedSet,
    myDeptSet,
    cascadeSet,
    deptHiddenSet,
    standingHiddenSet,
    setPick,
    clearPick,
    expandDepth,
    dagreReady,
  ]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={NODE_TYPES}
      fitView
      fitViewOptions={{ padding: 0.2 }}
      minZoom={0.3}
      maxZoom={1.5}
      proOptions={{ hideAttribution: true }}
    >
      <Background
        variant={BackgroundVariant.Dots}
        gap={28}
        size={1.2}
        color={COLORS.purpleSoft}
      />
      <Controls showInteractive={false} />
      {hiddenUnlockCount > 0 && (
        <div
          style={{
            position: "absolute",
            top: 12,
            right: 16,
            padding: "4px 10px",
            background: "#ffffff",
            border: `1px solid ${COLORS.border}`,
            borderRadius: 4,
            boxShadow: "rgba(23,23,23,0.06) 0px 3px 6px",
            fontSize: 11,
            color: COLORS.label,
            fontVariantNumeric: "tabular-nums",
            zIndex: 5,
          }}
          aria-label={`${hiddenUnlockCount} more unlocked courses not shown`}
        >
          +{hiddenUnlockCount} more unlocks not shown
        </div>
      )}
      {chainNodeCount > 0 && (
        <div
          style={{
            position: "absolute",
            top: 12,
            left: 16,
            padding: "4px 10px",
            background: "#ffffff",
            border: `1px solid ${COLORS.border}`,
            borderRadius: 4,
            boxShadow: "rgba(23,23,23,0.06) 0px 3px 6px",
            fontSize: 11,
            color: COLORS.label,
            fontVariantNumeric: "tabular-nums",
            zIndex: 5,
          }}
        >
          {chainNodeCount} course{chainNodeCount === 1 ? "" : "s"} upstream
          {chainTruncated ? ` (truncated at ${CHAIN_NODE_CAP})` : ""}
        </div>
      )}
      {(unreachable || spilloverCount > 0) && (
        <div
          style={{
            position: "absolute",
            bottom: 16,
            left: 16,
            display: "flex",
            flexDirection: "column",
            gap: 6,
            zIndex: 5,
          }}
        >
          {unreachable && (
            <div
              style={{
                padding: "5px 12px",
                background: "#fff0f4",
                border: "1px solid rgba(234, 34, 97, 0.35)",
                borderRadius: 4,
                fontSize: 11,
                color: "#a12252",
                fontWeight: 500,
                boxShadow: "rgba(23,23,23,0.06) 0px 3px 6px",
              }}
            >
              Unreachable — every option in at least one slot is hidden.
            </div>
          )}
          {spilloverCount > 0 && (
            <div
              style={{
                padding: "5px 12px",
                background: "#ffffff",
                border: `1px solid ${COLORS.border}`,
                borderRadius: 4,
                fontSize: 11,
                color: COLORS.label,
                boxShadow: "rgba(23,23,23,0.06) 0px 3px 6px",
                fontVariantNumeric: "tabular-nums",
              }}
            >
              +{spilloverCount}{" "}
              {chainNodeCount > 0
                ? `course${spilloverCount === 1 ? "" : "s"}`
                : `prereq${spilloverCount === 1 ? "" : "s"}`}{" "}
              outside your departments
            </div>
          )}
        </div>
      )}
    </ReactFlow>
  );
}

export function Graph(props: GraphProps) {
  return (
    <ReactFlowProvider>
      <GraphInner {...props} />
    </ReactFlowProvider>
  );
}
