"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useTranslations } from "next-intl";
import { apiGet } from "@/lib/api";
import type { CharacterGraph } from "@/types/novel";

interface RelationshipMapProps {
  novelId: string;
}

export default function RelationshipMap({ novelId }: RelationshipMapProps) {
  const t = useTranslations("writing.relationshipMap");
  const [graph, setGraph] = useState<CharacterGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<string>("all");
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiGet<CharacterGraph>(`/api/characters/novel/${novelId}/graph`);
      setGraph(res);
    } catch {
    } finally {
      setLoading(false);
    }
  }, [novelId]);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="flex items-center justify-center h-full"><p className="text-muted text-sm">{t("loading")}</p></div>;

  if (!graph || graph.nodes.length === 0) {
    return <div className="flex items-center justify-center h-full"><p className="text-muted text-sm">{t("noData")}</p></div>;
  }

  const filteredEdges = filterType === "all"
    ? graph.edges
    : graph.edges.filter((e) => e.relation_type === filterType);

  const relatedNodeIds = new Set<string>();
  if (selectedNode) {
    relatedNodeIds.add(selectedNode);
    filteredEdges.forEach((e) => {
      if (e.source === selectedNode) relatedNodeIds.add(e.target);
      if (e.target === selectedNode) relatedNodeIds.add(e.source);
    });
  }

  const roleColor = (role: string) => {
    const map: Record<string, string> = { protagonist: "#3b82f6", antagonist: "#ef4444", supporting: "#10b981", cameo: "#6b7280" };
    return map[role] || "#6b7280";
  };

  const relationColor = (type: string) => {
    const map: Record<string, string> = { "敌对": "#ef4444", "敌对关系": "#ef4444", "盟友": "#3b82f6", "亲属": "#f59e0b", "师徒": "#8b5cf6", "情感": "#ec4899", "暗恋": "#ec4899", "恋人": "#ec4899", "朋友": "#10b981" };
    return map[type] || "#9ca3af";
  };

  const nodeRadius = 28;
  const nodes = graph.nodes;
  const cols = Math.ceil(Math.sqrt(nodes.length));
  const spacingX = 180;
  const spacingY = 140;
  const width = Math.max(800, cols * spacingX + 80);
  const height = Math.max(600, Math.ceil(nodes.length / cols) * spacingY + 80);

  const nodePositions = nodes.map((node, i) => ({
    ...node,
    x: 60 + (i % cols) * spacingX,
    y: 60 + Math.floor(i / cols) * spacingY,
  }));

  const nodeMap = new Map(nodePositions.map((n) => [n.id, n]));

  const relationFilters = [
    { key: "all", label: t("filterAll") },
    { key: "敌对", label: t("filterEnemy") },
    { key: "盟友", label: t("filterAlly") },
    { key: "亲属", label: t("filterFamily") },
    { key: "师徒", label: t("filterMaster") },
    { key: "情感", label: t("filterLove") },
  ];

  const selectedChar = selectedNode ? nodeMap.get(selectedNode) : null;

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-2 border-b border-border flex items-center gap-2 shrink-0 overflow-x-auto">
        {relationFilters.map((f) => (
          <button key={f.key} className={`text-xs px-3 py-1 rounded-full border whitespace-nowrap ${filterType === f.key ? "bg-primary/10 border-primary text-primary" : "border-border text-muted"}`} onClick={() => setFilterType(f.key)}>
            {f.label}
          </button>
        ))}
        <div className="flex-1" />
        {selectedChar && (
          <div className="text-sm text-foreground flex items-center gap-2">
            <span className="w-2 h-2 rounded-full" style={{ background: roleColor(selectedChar.role) }} />
            <span className="font-medium">{selectedChar.name}</span>
            <Chip variant="soft" size="sm">{selectedChar.role}</Chip>
          </div>
        )}
      </div>

      <div className="flex-1 overflow-auto bg-muted/5">
        <svg width={width} height={height} ref={svgRef} className="min-w-full min-h-full">
          <defs>
            <filter id="glow">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>
          {filteredEdges.map((edge, i) => {
            const s = nodeMap.get(edge.source);
            const t = nodeMap.get(edge.target);
            if (!s || !t) return null;
            const isRelated = selectedNode && (edge.source === selectedNode || edge.target === selectedNode);
            const color = relationColor(edge.relation_type);
            return (
              <g key={i}>
                <line x1={s.x} y1={s.y} x2={t.x} y2={t.y} stroke={color} strokeWidth={isRelated ? 2.5 : 1} opacity={selectedNode && !isRelated ? 0.15 : 0.6} />
                <text x={(s.x + t.x) / 2} y={(s.y + t.y) / 2} textAnchor="middle" fontSize="11" fill={color} dy={-4} opacity={selectedNode && !isRelated ? 0.15 : 0.9}>{edge.relation_type}</text>
              </g>
            );
          })}
          {nodePositions.map((node) => {
            const isSelected = node.id === selectedNode;
            const isRelated = selectedNode && relatedNodeIds.has(node.id);
            const opacity = selectedNode && !isRelated ? 0.3 : 1;
            return (
              <g key={node.id} opacity={opacity} onClick={() => setSelectedNode(isSelected ? null : node.id)} style={{ cursor: "pointer" }}>
                {isSelected && <circle cx={node.x} cy={node.y} r={nodeRadius + 6} fill="none" stroke={roleColor(node.role)} strokeWidth={3} opacity={0.3} />}
                <circle cx={node.x} cy={node.y} r={nodeRadius} fill={roleColor(node.role)} stroke="#fff" strokeWidth={2} filter={isSelected ? "url(#glow)" : undefined} />
                <text x={node.x} y={node.y + 4} textAnchor="middle" fontSize="12" fontWeight="bold" fill="#fff">
                  {node.name.length > 3 ? node.name.slice(0, 3) : node.name}
                </text>
                <text x={node.x} y={node.y + nodeRadius + 16} textAnchor="middle" fontSize="11" fill={roleColor(node.role)}>{node.name}</text>
                <text x={node.x} y={node.y + nodeRadius + 30} textAnchor="middle" fontSize="10" fill="#9ca3af">{node.role}</text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}

function Chip({ children }: { variant?: string; size?: string; children: React.ReactNode }) {
  return <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-primary/10 text-primary">{children}</span>;
}
