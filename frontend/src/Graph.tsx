import { useMemo } from "react";
import ReactFlow, {
  Background,
  BackgroundVariant,
  Controls,
  Handle,
  MarkerType,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import type { GraphData } from "./types";

type CourseNodeData = {
  code: string;
  title: string;
  variant: "focus" | "prereq" | "unlock";
  eligible: boolean;
  completed: boolean;
  onClick: (code: string) => void;
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

  const bg = isCompleted
    ? COLORS.successBg
    : isFocus
      ? "linear-gradient(180deg, #ffffff 0%, #f6f9fc 100%)"
      : isEligible
        ? "#ffffff"
        : "#ffffff";

  const border = isFocus
    ? `2px solid ${COLORS.purple}`
    : isCompleted
      ? `1px solid ${COLORS.successBorder}`
      : isEligible
        ? `1px solid ${COLORS.purpleLight}`
        : `1px solid ${COLORS.border}`;

  const shadow = isFocus
    ? "rgba(50,50,93,0.25) 0px 30px 45px -30px, rgba(0,0,0,0.1) 0px 18px 36px -18px"
    : isEligible
      ? "rgba(83,58,253,0.18) 0px 8px 18px -8px, rgba(23,23,23,0.06) 0px 3px 6px"
      : "rgba(23,23,23,0.06) 0px 3px 6px";

  const codeColor = isCompleted
    ? COLORS.successText
    : isFocus
      ? COLORS.navy
      : isEligible
        ? COLORS.purple
        : COLORS.label;

  const titleColor = isFocus ? COLORS.label : COLORS.body;

  return (
    <div
      onClick={() => data.onClick(data.code)}
      style={{
        padding: "10px 14px",
        borderRadius: 6,
        border,
        background: bg,
        minWidth: 140,
        maxWidth: 220,
        cursor: "pointer",
        boxShadow: shadow,
        transition: "transform 120ms ease, box-shadow 120ms ease",
        position: "relative",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = "translateY(-1px)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = "none";
      }}
    >
      <Handle type="target" position={Position.Left} style={{ visibility: "hidden" }} />
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

const NODE_TYPES = { course: CourseNode };

const ROW_H = 78;
const COL_X = { prereq: 0, focus: 380, unlock: 760 };

export type GraphProps = {
  graph: GraphData;
  focusCode: string;
  completed: Set<string>;
  onSelectCourse: (code: string) => void;
};

export function Graph({ graph, focusCode, completed, onSelectCourse }: GraphProps) {
  const { nodes, edges } = useMemo(() => {
    const focus = graph.courses[focusCode];
    if (!focus) return { nodes: [], edges: [] };

    const prereqGroups = focus.prereq_groups;
    const flatPrereqs: string[] = [];
    const groupOfPrereq: Record<string, number[]> = {};
    prereqGroups.forEach((group, gi) => {
      group.forEach((c) => {
        if (!groupOfPrereq[c]) {
          groupOfPrereq[c] = [];
          flatPrereqs.push(c);
        }
        groupOfPrereq[c].push(gi);
      });
    });
    const unlocks = (graph.unlocks[focusCode] ?? []).slice(0, 12);

    const nodes: Node<CourseNodeData>[] = [];
    const edges: Edge[] = [];

    const isEligible = (code: string): boolean => {
      const c = graph.courses[code];
      if (!c) return false;
      if (completed.has(code)) return false;
      if (c.prereq_groups.length === 0) return true;
      return c.prereq_groups.some((g) => g.every((p) => completed.has(p)));
    };

    const mkNode = (
      code: string,
      x: number,
      y: number,
      variant: CourseNodeData["variant"],
    ): Node<CourseNodeData> => {
      const c = graph.courses[code];
      return {
        id: code,
        type: "course",
        position: { x, y },
        data: {
          code,
          title: c?.title ?? "(unknown)",
          variant,
          eligible: variant !== "focus" && isEligible(code),
          completed: completed.has(code),
          onClick: onSelectCourse,
        },
      };
    };

    const isOr = prereqGroups.length > 1;

    flatPrereqs.forEach((code, i) => {
      const y = i * ROW_H - ((flatPrereqs.length - 1) * ROW_H) / 2;
      nodes.push(mkNode(code, COL_X.prereq, y, "prereq"));
      const groups = groupOfPrereq[code];
      const labelText = isOr
        ? groups.length === 1
          ? `OR · group ${groups[0] + 1}`
          : `OR · groups ${groups.map((g) => g + 1).join(", ")}`
        : "AND";
      edges.push({
        id: `e-${code}->${focusCode}`,
        source: code,
        target: focusCode,
        animated: false,
        label: labelText,
        labelStyle: {
          fontSize: 10,
          fill: COLORS.label,
          fontFamily:
            "'Inter', -apple-system, BlinkMacSystemFont, system-ui, sans-serif",
          fontWeight: 500,
          letterSpacing: "0.02em",
        },
        labelBgStyle: {
          fill: "#ffffff",
          stroke: COLORS.border,
          strokeWidth: 1,
        },
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

    nodes.push(mkNode(focusCode, COL_X.focus, 0, "focus"));

    unlocks.forEach((code, i) => {
      const y = i * ROW_H - ((unlocks.length - 1) * ROW_H) / 2;
      nodes.push(mkNode(code, COL_X.unlock, y, "unlock"));
      const eligible = isEligible(code);
      const stroke = eligible ? COLORS.successText : COLORS.bodyMuted;
      edges.push({
        id: `e-${focusCode}->${code}`,
        source: focusCode,
        target: code,
        animated: false,
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

    return { nodes, edges };
  }, [graph, focusCode, completed, onSelectCourse]);

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
    </ReactFlow>
  );
}
