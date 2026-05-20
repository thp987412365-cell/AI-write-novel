"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useTranslations } from "next-intl";
import { Button } from "@heroui/react";
import { apiGet, apiPost, apiPut, apiDelete, apiPostSSE } from "@/lib/api";
import type { Chapter } from "@/types/novel";

interface ChapterEditorProps {
  novelId: string;
}

export default function ChapterEditor({ novelId }: ChapterEditorProps) {
  const t = useTranslations("writing.chapterEditor");
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [editingChapter, setEditingChapter] = useState<Chapter | null>(null);
  const [content, setContent] = useState("");
  const [title, setTitle] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  // AI generation state
  const [showAiModal, setShowAiModal] = useState(false);
  const [aiChapterCount, setAiChapterCount] = useState(3);
  const [useKnowledge, setUseKnowledge] = useState(false);
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiProgress, setAiProgress] = useState({ current: 0, total: 0, title: "" });
  const [aiResult, setAiResult] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const [showCompletion, setShowCompletion] = useState(false);
  const generatingRef = useRef(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const completionTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const loadChapters = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiGet<{ data: Chapter[] }>(`/api/chapters/novel/${novelId}`);
      setChapters(res.data);
    } catch {
    } finally {
      setLoading(false);
    }
  }, [novelId]);

  useEffect(() => {
    loadChapters();
  }, [loadChapters]);

  // 清理完成卡片定时器
  useEffect(() => {
    return () => {
      if (completionTimerRef.current) clearTimeout(completionTimerRef.current);
    };
  }, []);

  // 切换章节时重置滚动条到顶部
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.scrollTop = 0;
    }
  }, [selectedId]);

  const selectChapter = async (ch: Chapter) => {
    setSelectedId(ch._id);
    try {
      const detail = await apiGet<Chapter>(`/api/chapters/${ch._id}`);
      setEditingChapter(detail);
      setContent(detail.content || "");
      setTitle(detail.title || "");
    } catch {
    }
  };

  const createChapter = async () => {
    try {
      const res = await apiPost<{ id: string }>("/api/chapters/create", {
        novel_id: novelId,
        title: t("createChapter"),
      });
      await loadChapters();
      const newChapter: Chapter = {
        _id: res.id,
        novel_id: novelId,
        chapter_index: chapters.length + 1,
        title: t("createChapter"),
        content: "",
        word_count: 0,
        status: "draft",
        summary: "",
        key_events: [],
        sort_order: chapters.length + 1,
      };
      setSelectedId(res.id);
      setEditingChapter(newChapter);
      setTitle(t("createChapter"));
      setContent("");
    } catch {
    }
  };

  const saveChapter = async () => {
    if (!selectedId) return;
    try {
      setSaving(true);
      const wordCount = content.replace(/\s/g, "").length;
      await apiPut(`/api/chapters/${selectedId}`, {
        title: title || "Untitled",
        content,
        word_count: wordCount,
      });
      await loadChapters();
      setEditingChapter((prev) =>
        prev ? { ...prev, title, content, word_count: wordCount } : prev
      );
    } catch {
    } finally {
      setSaving(false);
    }
  };

  const deleteChapter = async () => {
    if (!selectedId) return;
    try {
      await apiDelete(`/api/chapters/${selectedId}`);
      setSelectedId(null);
      setEditingChapter(null);
      setContent("");
      setTitle("");
      await loadChapters();
    } catch {
    }
  };

  // ---- AI Generation ----

  const handleAiGenerate = async () => {
    if (generatingRef.current) return;
    generatingRef.current = true;
    setAiGenerating(true);
    setAiError(null);
    setAiResult(null);
    setShowCompletion(false);
    setAiProgress({ current: 0, total: aiChapterCount, title: "" });

    // 立即关闭弹框，让用户看到编辑器中的实时进度
    setShowAiModal(false);

    let totalNewEntities: Record<string, number> = {};
    let completedCount = 0;

    try {
      await apiPostSSE(
        "/api/llm/generate-chapters",
        { novel_id: novelId, num_chapters: aiChapterCount, use_knowledge: useKnowledge },
        (event, data) => {
          if (event === "step" && data.step === "writing") {
            if (data.status === "running") {
              setAiProgress({
                current: (data.current as number) || 0,
                total: (data.total as number) || aiChapterCount,
                title: "",
              });
            } else if (data.status === "done") {
              completedCount++;
              setAiProgress({
                current: (data.current as number) || 0,
                total: (data.total as number) || aiChapterCount,
                title: (data.title as string) || "",
              });

              // 逐章实时追加到本地章节列表
              const newChapter: Chapter = {
                _id: (data.chapter_id as string) || "",
                novel_id: novelId,
                chapter_index: (data.chapter_index as number) || 0,
                title: (data.title as string) || "",
                content: "",
                word_count: (data.word_count as number) || 0,
                status: "draft",
                summary: "",
                key_events: [],
                sort_order: (data.chapter_index as number) || 0,
              };
              setChapters((prev) => {
                if (prev.some((ch) => ch._id === newChapter._id)) return prev;
                const next = [...prev, newChapter];
                next.sort((a, b) => a.sort_order - b.sort_order);
                return next;
              });

              // 累积新实体统计
              const ne = data.new_entities as Record<string, number> | undefined;
              if (ne) {
                for (const key of Object.keys(ne)) {
                  totalNewEntities[key] = (totalNewEntities[key] || 0) + (ne[key] || 0);
                }
              }
            } else if (data.status === "error") {
              setAiError((data.error as string) || t("generateFailed"));
            }
          } else if (event === "step" && data.step === "workflow") {
            if (data.status === "resume") {
              // 断点续传：已有存量章节
              const existing = (data.existing_chapters as number) || 0;
              const startIdx = (data.start_index as number) || 1;
              setAiResult(
                t("resumeHint", { existing, start: startIdx })
              );
            }
          } else if (event === "done") {
            const count = data.chapters_generated as number;
            let resultMsg = t("generateDone", { count: count || completedCount });

            if (data.total_new_entities) {
              const ne = data.total_new_entities as Record<string, number>;
              const chars = ne.characters || 0;
              const locs = ne.locations || 0;
              const facs = ne.factions || 0;
              const items = ne.items || 0;
              const rules = ne.rules || 0;
              if (chars + locs + facs + items + rules > 0) {
                resultMsg += " — " + t("newEntitiesHint", { chars, locs, facs, items, rules });
              }
            }
            setAiResult(resultMsg);
          }
        },
        // onError: SSE 连接中断时，同步已保存的章节
        async (_err) => {
          await loadChapters();
        }
      );

      await loadChapters();
    } catch (e: unknown) {
      if (!aiResult) {
        setAiError(e instanceof Error ? e.message : t("generateFailed"));
      }
      await loadChapters();
    } finally {
      generatingRef.current = false;
      setAiGenerating(false);
      // 生成结束后显示完成卡片，5 秒后自动消失
      setShowCompletion(true);
      if (completionTimerRef.current) clearTimeout(completionTimerRef.current);
      completionTimerRef.current = setTimeout(() => {
        setShowCompletion(false);
        setAiResult(null);
        setAiError(null);
      }, 5000);
    }
  };

  const openAiModal = () => {
    setShowAiModal(true);
    setAiError(null);
    setAiResult(null);
  };

  return (
    <div className="h-full flex">
      {/* Left sidebar - chapter list */}
      <div className="w-60 border-r border-border overflow-y-auto shrink-0 flex flex-col">
        <div className="p-3 border-b border-border flex flex-col gap-2">
          <Button variant="primary" size="sm" className="w-full" onPress={createChapter}>
            {t("createChapter")}
          </Button>
          <Button
            variant="bordered"
            size="sm"
            className="w-full"
            onPress={openAiModal}
            isDisabled={aiGenerating}
          >
            {aiGenerating ? "..." : `🤖 ${t("aiGenerate")}`}
          </Button>
        </div>

        {/* AI 进度卡片：生成中实时显示 */}
        {aiGenerating && (
          <div className="mx-2 mt-2 p-3 rounded-lg border border-primary/30 bg-primary/5">
            <div className="flex items-center gap-2 mb-2">
              <span className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
              <span className="text-xs font-semibold text-primary">
                {t("generating", { current: aiProgress.current, total: aiProgress.total })}
              </span>
            </div>
            {aiProgress.title && (
              <p className="text-xs text-muted mb-2 truncate">「{aiProgress.title}」</p>
            )}
            <div className="w-full bg-muted/20 rounded-full h-1.5 overflow-hidden">
              <div
                className="bg-primary h-full rounded-full transition-all duration-700 ease-out"
                style={{
                  width: `${aiProgress.total > 0 ? (aiProgress.current / aiProgress.total) * 100 : 0}%`,
                }}
              />
            </div>
          </div>
        )}

        {/* AI 完成卡片：生成结束后短暂显示 */}
        {showCompletion && !aiGenerating && (aiResult || aiError) && (
          <div
            className={`mx-2 mt-2 p-3 rounded-lg border ${
              aiError
                ? "border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20"
                : "border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20"
            }`}
          >
            <div className="flex items-center gap-2">
              <span>{aiError ? "❌" : "✅"}</span>
              <span
                className={`text-xs font-medium ${
                  aiError
                    ? "text-red-700 dark:text-red-300"
                    : "text-green-700 dark:text-green-300"
                }`}
              >
                {aiError || aiResult}
              </span>
            </div>
          </div>
        )}

        {loading ? (
          <p className="text-xs text-muted p-4 text-center">加载中...</p>
        ) : chapters.length === 0 && !aiGenerating ? (
          <p className="text-xs text-muted p-4 text-center">{t("noChapters")}</p>
        ) : (
          chapters.map((ch) => (
            <button
              key={ch._id}
              className={`w-full text-left px-4 py-2.5 text-sm hover:bg-muted/5 transition-colors border-b border-border/30 ${
                selectedId === ch._id
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-foreground"
              }`}
              onClick={() => selectChapter(ch)}
            >
              <div className="truncate">
                第{ch.chapter_index}章 {ch.title}
              </div>
              <div className="text-xs text-muted mt-0.5">
                {ch.word_count || 0} 字
              </div>
            </button>
          ))
        )}
      </div>

      {/* Right - editor */}
      <div className="flex-1 min-w-0 flex flex-col">
        {editingChapter ? (
          <>
            <div className="px-5 py-3 border-b border-border flex items-center gap-3 shrink-0">
              <input
                className="flex-1 text-lg font-semibold bg-transparent border-none outline-none text-foreground"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="章节标题"
              />
              <span className="text-xs text-muted whitespace-nowrap">
                {content.replace(/\s/g, "").length || 0} {t("wordCount")}
              </span>
              <Button variant="outline" size="sm" onPress={saveChapter} isDisabled={saving}>
                {saving ? "..." : "保存"}
              </Button>
              <Button variant="ghost" size="sm" className="text-red-500" onPress={deleteChapter}>
                删除
              </Button>
            </div>
            <textarea
              ref={textareaRef}
              className="flex-1 p-5 bg-transparent border-none outline-none resize-none text-foreground leading-relaxed text-sm font-serif"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="开始书写..."
            />
          </>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-muted text-sm">
              {chapters.length === 0 ? t("noChapters") : "选择左侧章节开始编辑"}
            </p>
          </div>
        )}

      </div>

      {/* AI Generation Modal */}
      {showAiModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-background border border-border rounded-xl p-6 w-96 shadow-2xl">
            <h3 className="text-lg font-semibold mb-4">{t("aiGenerateTitle")}</h3>

            <div className="mb-4">
              <label className="block text-sm font-medium mb-2">{t("chapterCount")}</label>
              <input
                type="number"
                className="w-full px-3 py-2 border border-border rounded-lg bg-transparent text-foreground text-sm"
                value={aiChapterCount}
                min={1}
                max={50}
                onChange={(e) => setAiChapterCount(Math.max(1, Math.min(50, parseInt(e.target.value) || 1)))}
                disabled={aiGenerating}
              />
              <p className="text-xs text-muted mt-1">{t("chapterCountHint")}</p>
            </div>

            <div className="mb-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={useKnowledge}
                  onChange={(e) => setUseKnowledge(e.target.checked)}
                  className="w-4 h-4 rounded border-border text-accent focus:ring-accent/20"
                  disabled={aiGenerating}
                />
                <span className="text-sm">📚 结合知识库</span>
              </label>
              <p className="text-xs text-muted mt-1 ml-6">AI 创作时会参考小说知识库中关联的素材</p>
            </div>

            <div className="flex justify-end gap-3">
              <Button
                variant="ghost"
                size="sm"
                onPress={() => {
                  setShowAiModal(false);
                  setAiError(null);
                  setAiResult(null);
                }}
                isDisabled={aiGenerating}
              >
                {t("cancel")}
              </Button>
              <Button
                variant="primary"
                size="sm"
                onPress={handleAiGenerate}
                isDisabled={aiGenerating}
              >
                {aiGenerating ? "..." : t("startGenerate")}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
