"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { useRouter, usePathname } from "next/navigation";
import { Button } from "@heroui/react";
import { apiGet, apiPost } from "@/lib/api";
import type { NovelDetail, WritingDraft, CreateNovelRequest, GeneratedCharacter, GeneratedFaction, GeneratedLocation, GeneratedItem, GeneratedRule, GeneratedRelation } from "@/types/novel";
import NovelInfoSection, { type SectionKey } from "./NovelInfoSection";
import StickyActionBar from "./StickyActionBar";

const SECTIONS: SectionKey[] = ["basic", "creative", "scale", "content", "style"];
const DRAFT_KEY = "writing_draft";

interface NovelInfoWorkspaceProps {
  mode: "create" | "edit";
  novelId?: string;
}

export default function NovelInfoWorkspace({ mode, novelId }: NovelInfoWorkspaceProps) {
  const tw = useTranslations("writing.novelInfo");
  const twd = useTranslations("writing");
  const router = useRouter();
  const pathname = usePathname();
  const locale = pathname.startsWith("/en") ? "en" : "zh";

  /* state */
  const [data, setData] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(mode === "edit");
  const [loadError, setLoadError] = useState(false);
  const [noDraft, setNoDraft] = useState(false);
  const [editingSection, setEditingSection] = useState<SectionKey | null>(null);
  const [creating, setCreating] = useState(false);
  const [hasChapters, setHasChapters] = useState(false);

  /* danger confirm */
  const [showDangerModal, setShowDangerModal] = useState(false);
  const [dangerResolve, setDangerResolve] = useState<((v: boolean) => void) | null>(null);

  /* load data */
  const loadNovel = useCallback(async () => {
    if (!novelId) return;
    try {
      setLoading(true);
      setLoadError(false);
      const novel = await apiGet<NovelDetail>(`/api/novels/${novelId}`);
      setData(novel as unknown as Record<string, unknown>);
      setHasChapters((novel.stats?.chapter_count ?? 0) > 0);
    } catch {
      setLoadError(true);
    } finally {
      setLoading(false);
    }
  }, [novelId]);

  useEffect(() => {
    if (mode === "edit") {
      loadNovel();
    } else {
      // create mode: load from sessionStorage
      try {
        const raw = sessionStorage.getItem(DRAFT_KEY);
        if (raw) {
          const draft: WritingDraft = JSON.parse(raw);
          setData(draft as unknown as Record<string, unknown>);
        } else {
          setNoDraft(true);
        }
      } catch {
        setNoDraft(true);
      }
    }
  }, [mode, loadNovel]);

  /* create novel */
  const handleCreate = async () => {
    try {
      setCreating(true);
      const payload: CreateNovelRequest = {
        title: String(data.title || ""),
        subtitle: data.subtitle ? String(data.subtitle) : undefined,
        genre: data.genre ? String(data.genre) : undefined,
        tags: Array.isArray(data.tags) ? data.tags : undefined,
        introduction: data.introduction ? String(data.introduction) : undefined,
        summary: data.summary ? String(data.summary) : undefined,
        core_seed: data.core_seed ? String(data.core_seed) : undefined,
        worldview: data.worldview ? String(data.worldview) : undefined,
        writing_style: data.writing_style ? String(data.writing_style) : undefined,
        narrative_pov: data.narrative_pov ? String(data.narrative_pov) : undefined,
        era_background: data.era_background ? String(data.era_background) : undefined,
        cover_image: data.cover_image ? String(data.cover_image) : undefined,
        plot: data.plot ? String(data.plot) : undefined,
        tone: data.tone ? String(data.tone) : undefined,
        target_audience: data.target_audience ? String(data.target_audience) : undefined,
        core_idea: data.core_idea ? String(data.core_idea) : undefined,
        number_of_chapters: data.number_of_chapters ? Number(data.number_of_chapters) : undefined,
        words_per_chapter: data.words_per_chapter ? Number(data.words_per_chapter) : undefined,
        characters: Array.isArray(data.characters) ? data.characters as GeneratedCharacter[] : undefined,
        factions: Array.isArray(data.factions) ? data.factions as GeneratedFaction[] : undefined,
        locations: Array.isArray(data.locations) ? data.locations as GeneratedLocation[] : undefined,
        items: Array.isArray(data.items) ? data.items as GeneratedItem[] : undefined,
        rules: Array.isArray(data.rules) ? data.rules as GeneratedRule[] : undefined,
        relationships: Array.isArray(data.relationships) ? data.relationships as GeneratedRelation[] : undefined,
      };
      const res = await apiPost<{ id: string }>("/api/novels/create", payload);
      sessionStorage.removeItem(DRAFT_KEY);
      router.push(`/${locale}/writing/${res.id}`);
    } catch {
      alert(tw("createFailed"));
    } finally {
      setCreating(false);
    }
  };

  /* field change (create mode) */
  const handleFieldChange = (field: string, value: unknown) => {
    setData((prev) => ({ ...prev, [field]: value }));
  };

  /* danger confirm promise */
  const requestDangerConfirm = (): Promise<boolean> => {
    return new Promise((resolve) => {
      setDangerResolve(() => resolve);
      setShowDangerModal(true);
    });
  };

  const handleDangerResponse = (confirmed: boolean) => {
    setShowDangerModal(false);
    dangerResolve?.(confirmed);
    setDangerResolve(null);
  };

  /* render */

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted">{twd("loading")}</p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <p className="text-muted">{twd("loadFailed")}</p>
        <Button variant="outline" onPress={loadNovel}>{tw("saveSection")}</Button>
      </div>
    );
  }

  if (mode === "create" && noDraft) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-3">
        <p className="text-muted">{tw("noDraft")}</p>
        <Button
          variant="outline"
          onPress={() => router.push(`/${locale}`)}
        >
          {twd("backToCreate")}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Danger Confirm Modal */}
      {showDangerModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-background rounded-xl shadow-xl p-6 max-w-md mx-4 border border-border">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-warning/10 flex items-center justify-center shrink-0">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-warning">
                  <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
                  <path d="M12 9v4" /><path d="M12 17h.01" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-foreground">{twd("dangerEditTitle")}</h3>
            </div>
            <p className="text-sm text-muted mb-5">{twd("dangerEditMessage")}</p>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onPress={() => handleDangerResponse(false)}>
                {twd("cancel")}
              </Button>
              <Button variant="primary" size="sm" className="bg-accent text-white hover:bg-accent-hover" onPress={() => handleDangerResponse(true)}>
                {twd("confirmContinue")}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="px-6 py-4 border-b border-border">
        <h2 className="text-lg font-bold text-foreground">
          {mode === "create" ? tw("createTitle") : tw("editTitle")}
        </h2>
        {mode === "create" && (
          <p className="text-sm text-muted mt-1">{tw("createDescription")}</p>
        )}
      </div>

      {/* Sections */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {SECTIONS.map((sk) => (
          <NovelInfoSection
            key={sk}
            sectionKey={sk}
            data={data}
            novelId={novelId}
            isCreateMode={mode === "create"}
            isEditing={mode === "create" || editingSection === sk}
            onStartEdit={() => setEditingSection(sk)}
            onCancelEdit={() => setEditingSection(null)}
            onSaved={() => {
              setEditingSection(null);
              loadNovel();
            }}
            onChange={mode === "create" ? handleFieldChange : undefined}
            hasChapters={hasChapters}
            onDangerConfirm={requestDangerConfirm}
          />
        ))}

        {mode === "create" && (
          <EntityPreviewSection
            data={data}
            onChange={handleFieldChange}
            twd={twd}
          />
        )}
      </div>

      {/* Sticky action bar - create mode */}
      {mode === "create" && (
        <StickyActionBar>
          <Button
            variant="ghost"
            onPress={() => router.push(`/${locale}`)}
          >
            {twd("backToCreate")}
          </Button>
          <Button
            variant="primary"
            onPress={handleCreate}
            isDisabled={creating || !data.title}
            className="bg-accent text-white hover:bg-accent-hover"
          >
            {creating ? tw("creating") : tw("saveCreate")}
          </Button>
        </StickyActionBar>
      )}
    </div>
  );
}

function EntityPreviewSection({
  data,
  onChange,
  twd,
}: {
  data: Record<string, unknown>;
  onChange: (field: string, value: unknown) => void;
  twd: ReturnType<typeof useTranslations>;
}) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggle = (key: string) => setExpanded((prev) => ({ ...prev, [key]: !prev[key] }));

  const entities: { key: string; label: string; items: unknown[] | undefined }[] = [
    { key: "characters", label: "角色卡", items: data.characters as GeneratedCharacter[] | undefined },
    { key: "factions", label: "势力卡", items: data.factions as GeneratedFaction[] | undefined },
    { key: "locations", label: "地点卡", items: data.locations as GeneratedLocation[] | undefined },
    { key: "items", label: "物品卡", items: data.items as GeneratedItem[] | undefined },
    { key: "rules", label: "设定规则", items: data.rules as GeneratedRule[] | undefined },
    { key: "relationships", label: "角色关系", items: data.relationships as GeneratedRelation[] | undefined },
  ];

  const hasAny = entities.some((e) => Array.isArray(e.items) && e.items!.length > 0);
  if (!hasAny) return null;

  return (
    <div className="space-y-3">
      <div className="pt-2 border-t border-border">
        <h3 className="text-sm font-semibold text-foreground mb-3">🤖 AI 生成的实体数据</h3>
      </div>
      {entities.map(({ key, label, items }) => {
        if (!Array.isArray(items) || items.length === 0) return null;
        const isOpen = expanded[key] ?? true;

        return (
          <div key={key} className="rounded-lg border border-border overflow-hidden">
            <button
              className="w-full flex items-center justify-between px-4 py-2.5 bg-surface-secondary/40 hover:bg-surface-secondary/60 transition-colors text-sm font-medium text-foreground"
              onClick={() => toggle(key)}
            >
              <span>{label}（{items.length}）</span>
              <svg className={`w-4 h-4 transition-transform ${isOpen ? "rotate-180" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            {isOpen && (
              <div className="divide-y divide-border">
                {items.map((item: unknown, idx: number) => {
                  const record = item as Record<string, unknown>;
                  return (
                    <div key={idx} className="px-4 py-3 bg-surface-secondary/10">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-foreground">
                          {String(record.name ?? record.source_name ?? `#${idx + 1}`)}
                        </span>
                        <button
                          className="text-xs text-red-500 hover:text-red-700"
                          onClick={() => {
                            const newItems = items.filter((_, i) => i !== idx);
                            onChange(key, newItems);
                          }}
                        >
                          删除
                        </button>
                      </div>
                      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                        {Object.entries(record).map(([k, v]) => {
                          if (k === "name" || k === "source_name" || v === undefined || v === "") return null;
                          const display = Array.isArray(v) ? (v as string[]).join("、") : String(v);
                          return (
                            <div key={k} className="text-xs">
                              <span className="text-muted">{k}: </span>
                              <span className="text-foreground">{display.length > 80 ? display.slice(0, 80) + "…" : display}</span>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
