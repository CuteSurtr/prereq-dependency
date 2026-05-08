import { useMemo } from "react";
import ReactFlow, {
  Background,
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

function CourseNode({ data }: NodeProps<CourseNodeData>) {
  const bg = data.completed
    ? "#bbf7d0"
    : data.variant === "focus"
      ? "#dbeafe"
      : data.eligible
        ? "#fef9c3"
        : "#fff";
  const border = data.variant === "focus" ? "#2563eb" : "#94a3b8";
  return (
    <div
      onClick={() => data.onClick(data.code)}
      style={{
        padding: "10px 14px",
        borderRadius: 8,
        border: `2px solid ${border}`,
        background: bg,
        minWidth: 130,
        maxWidth: 220,
        cursor: "pointer",
        fontSize: 13,
        boxShadow: data.variant === "focus" ? "0 4px 14px rgba(37,99,235,.15)" : "none",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ visibility: "hidden" }} />
      <div style={{ fontWeight: 600 }}>{data.code}</div>
      <div style={{ color: "#475569", fontSize: 11, lineHeight: 1.3, marginTop: 2 }}>
        {data.title.length > 60 ? data.title.slice(0, 57) + "…" : data.title}
      </div>
      <Handle type="source" position={Position.Right} style={{ visibility: "hidden" }} />
    </div>
  );
}

const NODE_TYPES = { course: CourseNode };

const ROW_H = 75;
const COL_X = { prereq: 0, focus: 360, unlock: 720 };

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
    const unlocks = (graph.unlocks[focusCode] ?? []).slice(0, 12); // cap for readability

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

    flatPrereqs.forEach((code, i) => {
      const y = i * ROW_H - ((flatPrereqs.length - 1) * ROW_H) / 2;
      nodes.push(mkNode(code, COL_X.prereq, y, "prereq"));
      const groups = groupOfPrereq[code];
      // Edge style: SOLID if this prereq is in only one group AND single group total OR
      //             single group exists; DASHED if there are multiple groups (OR semantics).
      const isOr = prereqGroups.length > 1;
      edges.push({
        id: `e-${code}->${focusCode}`,
        source: code,
        target: focusCode,
        animated: false,
        label: isOr ? `OR g${groups.join(",")}` : "AND",
        labelStyle: { fontSize: 10, fill: "#64748b" },
        labelBgStyle: { fill: "#fff" },
        labelBgPadding: [2, 4],
        style: {
          stroke: isOr ? "#a855f7" : "#0ea5e9",
          strokeWidth: 1.6,
          strokeDasharray: isOr ? "5,4" : undefined,
        },
        markerEnd: { type: MarkerType.ArrowClosed, color: isOr ? "#a855f7" : "#0ea5e9" },
      });
    });

    nodes.push(mkNode(focusCode, COL_X.focus, 0, "focus"));

    unlocks.forEach((code, i) => {
      const y = i * ROW_H - ((unlocks.length - 1) * ROW_H) / 2;
      nodes.push(mkNode(code, COL_X.unlock, y, "unlock"));
      const eligible = isEligible(code);
      edges.push({
        id: `e-${focusCode}->${code}`,
        source: focusCode,
        target: code,
        animated: false,
        style: {
          stroke: eligible ? "#16a34a" : "#94a3b8",
          strokeWidth: eligible ? 2 : 1.2,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: eligible ? "#16a34a" : "#94a3b8",
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
      fitViewOptions={{ padding: 0.15 }}
      minZoom={0.3}
      maxZoom={1.5}
      proOptions={{ hideAttribution: true }}
    >
      <Background gap={24} size={1} color="#e5e7eb" />
      <Controls showInteractive={false} />
    </ReactFlow>
  );
}
