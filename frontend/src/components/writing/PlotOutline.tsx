"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { apiGet, apiPut, apiPostSSE } from "@/lib/api";
import type { PlotOutline as PlotOutlineType } from "@/types/novel";

interface PlotOutlineProps {
  novelId: string;
}

export default function PlotOutlineView({ novelId }: PlotOutlineProps) {
  const t = useTranslations("writing.plotOutline");

  const [outline, setOutline] = useState<PlotOutlineType | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [genProgress, setGenProgress] = useState("");
  const [error, setError] = useState("");
  const [useKnowledge, setUseKnowledge] = useState(false);
  const [expandedArcs, setExpandedArcs] = useState<Set<number>>(new Set([0]));
  const [expandedPoints, setExpandedPoints] = useState<Set<string>>(new Set());
  const [editingPoint, setEditingPoint] = useState<{
    arcIndex: number;
    pointIndex: number;
    title: string;
    description: string;
    target_chapters: number;
    key_characters: string;
    key_locations: string;
  } | null>(null);
  const [saving, setSaving] = useState(false);

  const fetchOutline = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiGet<{ data: PlotOutlineType | null }>(
        `/api/outlines/novel/${novelId}`
      );
      setOutline(res.data);
      setError("");
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [novelId]);

  useEffect(() => {
    fetchOutline();
  }, [fetchOutline]);

  const handleGenerate = async () => {
    setGenerating(true);
    setGenProgress(t("generating"));
    setError("");

    try {
      await apiPostSSE(
        "/api/llm/generate-plot-outline",
        { novel_id: novelId, use_knowledge: useKnowledge },
        (event, data) => {
          if (event === "step" && data.status === "running") {
            setGenProgress(t("generating"));
          } else if (event === "step" && data.status === "done") {
            setGenProgress(t("generateSuccess"));
            if (data.data) {
              setOutline(data.data as unknown as PlotOutlineType);
            }
          } else if (event === "step" && data.status === "error") {
            setError(String(data.error || t("generateFailed")));
          }
        }
      );
      await fetchOutline();
    } catch (e) {
      setError(String(e));
    } finally {
      setGenerating(false);
    }
  };

  const toggleArc = (idx: number) => {
    setExpandedArcs((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const togglePoint = (key: string) => {
    setExpandedPoints((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const openEdit = (
    arcIndex: number,
    pointIndex: number,
    point: {
      title: string;
      description: string;
      target_chapters: number;
      key_characters: string[];
      key_locations: string[];
    }
  ) => {
    setEditingPoint({
      arcIndex,
      pointIndex,
      title: point.title,
      description: point.description,
      target_chapters: point.target_chapters,
      key_characters: point.key_characters?.join("、") || "",
      key_locations: point.key_locations?.join("、") || "",
    });
  };

  const handleSaveEdit = async () => {
    if (!editingPoint) return;
    setSaving(true);
    try {
      const body: Record<string, unknown> = {};
      if (editingPoint.title) body.title = editingPoint.title;
      if (editingPoint.description) body.description = editingPoint.description;
      if (editingPoint.target_chapters) body.target_chapters = editingPoint.target_chapters;
      if (editingPoint.key_characters) {
        body.key_characters = editingPoint.key_characters
          .split(/[、,，]/)
          .map((s) => s.trim())
          .filter(Boolean);
      }
      if (editingPoint.key_locations) {
        body.key_locations = editingPoint.key_locations
          .split(/[、,，]/)
          .map((s) => s.trim())
          .filter(Boolean);
      }

      await apiPut(
        `/api/outlines/novel/${novelId}/point?arc_index=${editingPoint.arcIndex}&point_index=${editingPoint.pointIndex}`,
        body
      );
      setEditingPoint(null);
      await fetchOutline();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const statusIcon = (status: string) => {
    if (status === "completed") {
      return (
        <span className="text-green-500 text-lg" title={t("statusCompleted")}>
          ✓
        </span>
      );
    }
    if (status === "in_progress") {
      return (
        <span className="text-blue-500 text-lg animate-pulse" title={t("statusInProgress")}>
          ◉
        </span>
      );
    }
    return (
      <span className="text-muted text-lg" title={t("statusPending")}>
        ○
      </span>
    );
  };

  const statusLabel = (status: string) => {
    if (status === "completed") return t("statusCompleted");
    if (status === "in_progress") return t("statusInProgress");
    return t("statusPending");
  };

  const statusBadgeClass = (status: string) => {
    if (status === "completed") return "bg-green-500/10 text-green-600 border-green-500/20";
    if (status === "in_progress") return "bg-blue-500/10 text-blue-600 border-blue-500/20";
    return "bg-surface-secondary text-muted border-border";
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-muted">
          <div className="w-6 h-6 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
          <span className="text-sm">Loading...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h2 className="text-xl font-bold">{t("title")}</h2>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 cursor-pointer text-sm">
              <input
                type="checkbox"
                checked={useKnowledge}
                onChange={(e) => setUseKnowledge(e.target.checked)}
                className="w-4 h-4 rounded border-border text-accent focus:ring-accent/20"
                disabled={generating}
              />
              <span className="text-muted">📚 结合知识库</span>
            </label>
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {generating
                ? genProgress
                : outline
                  ? t("regenerateOutline")
                  : t("generateOutline")}
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 text-sm">
            {error}
          </div>
        )}

        {generating && (
          <div className="p-6 rounded-xl bg-accent/5 border border-accent/20 flex flex-col items-center gap-4">
            <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
            <p className="text-sm text-muted">{genProgress}</p>
          </div>
        )}

        {/* Empty state */}
        {!outline && !generating && (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="48"
              height="48"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              className="text-muted"
            >
              <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2" />
              <rect x="9" y="3" width="6" height="4" rx="1" />
              <path d="M9 12h6" />
              <path d="M9 16h6" />
              <path d="M9 8h6" />
            </svg>
            <p className="text-muted">{t("noOutline")}</p>
          </div>
        )}

        {/* Outline content */}
        {outline && !generating && (
          <div className="space-y-4">
            {outline.arcs?.map((arc, arcIdx) => {
              const isArcExpanded = expandedArcs.has(arcIdx);
              const completedPoints = arc.plot_points?.filter(
                (p) => p.status === "completed"
              ).length || 0;
              const totalPoints = arc.plot_points?.length || 0;
              const arcProgress =
                totalPoints > 0 ? Math.round((completedPoints / totalPoints) * 100) : 0;

              return (
                <div
                  key={arcIdx}
                  className="rounded-xl border border-border bg-surface overflow-hidden"
                >
                  {/* Arc header */}
                  <button
                    onClick={() => toggleArc(arcIdx)}
                    className="w-full flex items-center gap-3 px-5 py-4 hover:bg-surface-secondary/50 transition-colors text-left"
                  >
                    <svg
                      xmlns="http://www.w3.org/2000/svg"
                      width="16"
                      height="16"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      className={`text-muted shrink-0 transition-transform ${
                        isArcExpanded ? "rotate-90" : ""
                      }`}
                    >
                      <path d="m9 18 6-6-6-6" />
                    </svg>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted font-mono">
                          ARC {arcIdx + 1}
                        </span>
                        <h3 className="font-semibold truncate">{arc.title}</h3>
                      </div>
                      {!isArcExpanded && arc.summary && (
                        <p className="text-xs text-muted mt-0.5 line-clamp-1">
                          {arc.summary}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <div className="w-20 h-1.5 bg-surface-secondary rounded-full overflow-hidden">
                        <div
                          className="h-full bg-accent rounded-full transition-all"
                          style={{ width: `${arcProgress}%` }}
                        />
                      </div>
                      <span className="text-xs text-muted w-12 text-right">
                        {completedPoints}/{totalPoints}
                      </span>
                    </div>
                  </button>

                  {/* Arc body */}
                  {isArcExpanded && (
                    <div className="px-5 pb-4 space-y-3">
                      {arc.summary && (
                        <p className="text-sm text-muted px-1">{arc.summary}</p>
                      )}

                      {/* Plot points */}
                      <div className="space-y-2">
                        {arc.plot_points?.map((point, ptIdx) => {
                          const pointKey = `${arcIdx}-${ptIdx}`;
                          const isPointExpanded = expandedPoints.has(pointKey);

                          return (
                            <div
                              key={ptIdx}
                              className="rounded-lg border border-border/50 bg-surface-secondary/30 overflow-hidden"
                            >
                              {/* Point header */}
                              <button
                                onClick={() => togglePoint(pointKey)}
                                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-surface-secondary/50 transition-colors text-left"
                              >
                                <span className="shrink-0">{statusIcon(point.status)}</span>
                                <span className="flex-1 text-sm font-medium truncate">
                                  {ptIdx + 1}. {point.title}
                                </span>
                                <span
                                  className={`text-xs px-2 py-0.5 rounded-full border ${statusBadgeClass(
                                    point.status
                                  )}`}
                                >
                                  {statusLabel(point.status)}
                                </span>
                                {point.target_chapters > 0 && (
                                  <span className="text-xs text-muted">
                                    {point.chapter_ids?.length || 0}/{point.target_chapters}{" "}
                                    {t("targetChapters")}
                                  </span>
                                )}
                              </button>

                              {/* Point detail */}
                              {isPointExpanded && (
                                <div className="px-4 pb-4 pt-1 space-y-3">
                                  <p className="text-sm text-muted leading-relaxed">
                                    {point.description}
                                  </p>

                                  {/* Meta tags */}
                                  <div className="flex flex-wrap gap-4 text-xs text-muted">
                                    {point.target_chapters > 0 && (
                                      <span>
                                        {t("targetChapters")}: {point.chapter_ids?.length || 0}/
                                        {point.target_chapters}
                                      </span>
                                    )}
                                    {point.key_characters?.length > 0 && (
                                      <span className="flex items-center gap-1">
                                        <span className="text-[10px]">👤</span>
                                        {point.key_characters.join("、")}
                                      </span>
                                    )}
                                    {point.key_locations?.length > 0 && (
                                      <span className="flex items-center gap-1">
                                        <span className="text-[10px]">📍</span>
                                        {point.key_locations.join("、")}
                                      </span>
                                    )}
                                  </div>

                                  {/* Edit button */}
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      openEdit(arcIdx, ptIdx, point);
                                    }}
                                    className="text-xs text-accent hover:underline"
                                  >
                                    {t("editPoint")}
                                  </button>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Edit Modal */}
        {editingPoint && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="bg-surface rounded-xl border border-border shadow-xl w-full max-w-lg mx-4 p-6 space-y-4">
              <h3 className="text-lg font-semibold">{t("editPoint")}</h3>

              <div className="space-y-3">
                <div>
                  <label className="text-xs text-muted block mb-1">标题</label>
                  <input
                    value={editingPoint.title}
                    onChange={(e) =>
                      setEditingPoint({ ...editingPoint, title: e.target.value })
                    }
                    className="w-full px-3 py-2 rounded-lg border border-border bg-surface-secondary text-sm focus:outline-none focus:ring-2 focus:ring-accent/20"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted block mb-1">描述</label>
                  <textarea
                    value={editingPoint.description}
                    onChange={(e) =>
                      setEditingPoint({
                        ...editingPoint,
                        description: e.target.value,
                      })
                    }
                    rows={4}
                    className="w-full px-3 py-2 rounded-lg border border-border bg-surface-secondary text-sm focus:outline-none focus:ring-2 focus:ring-accent/20 resize-none"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted block mb-1">计划章节数</label>
                  <input
                    type="number"
                    value={editingPoint.target_chapters}
                    onChange={(e) =>
                      setEditingPoint({
                        ...editingPoint,
                        target_chapters: Number(e.target.value),
                      })
                    }
                    min={1}
                    max={20}
                    className="w-24 px-3 py-2 rounded-lg border border-border bg-surface-secondary text-sm focus:outline-none focus:ring-2 focus:ring-accent/20"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted block mb-1">
                    {t("characters")}（用、或逗号分隔）
                  </label>
                  <input
                    value={editingPoint.key_characters}
                    onChange={(e) =>
                      setEditingPoint({
                        ...editingPoint,
                        key_characters: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 rounded-lg border border-border bg-surface-secondary text-sm focus:outline-none focus:ring-2 focus:ring-accent/20"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted block mb-1">
                    {t("locations")}（用、或逗号分隔）
                  </label>
                  <input
                    value={editingPoint.key_locations}
                    onChange={(e) =>
                      setEditingPoint({
                        ...editingPoint,
                        key_locations: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 rounded-lg border border-border bg-surface-secondary text-sm focus:outline-none focus:ring-2 focus:ring-accent/20"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-2">
                <button
                  onClick={() => setEditingPoint(null)}
                  className="px-4 py-2 rounded-lg text-sm border border-border hover:bg-surface-secondary transition-colors"
                >
                  {t("cancelEdit")}
                </button>
                <button
                  onClick={handleSaveEdit}
                  disabled={saving}
                  className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90 disabled:opacity-50 transition-colors"
                >
                  {saving ? "..." : t("saveEdit")}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
