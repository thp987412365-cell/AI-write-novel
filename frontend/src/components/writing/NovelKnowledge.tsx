"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { apiGet, apiPost, apiDelete } from "@/lib/api";
import type { NovelKnowledgeLink, KnowledgeDoc } from "@/types/novel";

interface NovelKnowledgeProps {
  novelId: string;
}

export default function NovelKnowledge({ novelId }: NovelKnowledgeProps) {
  const t = useTranslations("writing.knowledgeBase");
  const [linkedDocs, setLinkedDocs] = useState<NovelKnowledgeLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showLinkModal, setShowLinkModal] = useState(false);
  const [globalDocs, setGlobalDocs] = useState<KnowledgeDoc[]>([]);
  const [globalLoading, setGlobalLoading] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [linking, setLinking] = useState(false);
  const [searchGlobal, setSearchGlobal] = useState("");

  const fetchLinkedDocs = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiGet<{ data: NovelKnowledgeLink[] }>(
        `/api/novels/${novelId}/knowledge`
      );
      setLinkedDocs(res.data || []);
      setError("");
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [novelId]);

  useEffect(() => {
    fetchLinkedDocs();
  }, [fetchLinkedDocs]);

  const openLinkModal = async () => {
    setShowLinkModal(true);
    setGlobalLoading(true);
    setSelectedIds(new Set(linkedDocs.map((d) => d.doc_id)));
    try {
      const params = new URLSearchParams();
      if (searchGlobal) params.set("keyword", searchGlobal);
      const res = await apiGet<{ data: KnowledgeDoc[] }>(
        `/api/knowledge/docs?${params.toString()}`
      );
      setGlobalDocs(res.data || []);
    } catch (e) {
      setError(String(e));
    } finally {
      setGlobalLoading(false);
    }
  };

  const handleLink = async () => {
    setLinking(true);
    try {
      const ids = Array.from(selectedIds);
      await apiPost(`/api/novels/${novelId}/knowledge/link`, { doc_ids: ids });
      setShowLinkModal(false);
      await fetchLinkedDocs();
    } catch (e) {
      setError(String(e));
    } finally {
      setLinking(false);
    }
  };

  const handleUnlink = async (doc: NovelKnowledgeLink) => {
    if (!confirm(t("unlinkConfirm", { title: doc.title }))) return;
    try {
      await apiDelete(`/api/novels/${novelId}/knowledge/${doc.doc_id}`);
      await fetchLinkedDocs();
    } catch (e) {
      setError(String(e));
    }
  };

  const toggleSelect = (docId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(docId)) next.delete(docId);
      else next.add(docId);
      return next;
    });
  };


  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-6 h-6 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-4xl mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">{t("title")}</h2>
          <button
            onClick={openLinkModal}
            className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90 transition-colors flex items-center gap-2"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
            </svg>
            {t("linkDocs")}
          </button>
        </div>

        {error && (
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 text-sm">
            {error}
          </div>
        )}

        {/* Linked docs list */}
        {linkedDocs.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-muted">
              <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
              <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
            </svg>
            <p className="text-muted text-sm text-center max-w-sm">{t("noDocs")}</p>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-xs text-muted">{t("linkedCount", { count: linkedDocs.length })}</p>
            {linkedDocs.map((doc) => (
              <div
                key={doc.doc_id}
                className="flex items-center gap-3 px-4 py-3 rounded-lg border border-border bg-surface hover:bg-surface-secondary/50 transition-colors"
              >
                <span className="text-sm font-bold text-violet-500 bg-violet-500/10 px-2 py-0.5 rounded shrink-0">
                  MD
                </span>
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-medium truncate block">{doc.title}</span>
                  <div className="flex items-center gap-3 text-xs text-muted mt-0.5">
                    <span>{t("wordCount")}: {doc.word_count?.toLocaleString() || 0}</span>
                  </div>
                </div>
                <button
                  onClick={() => handleUnlink(doc)}
                  className="p-1.5 rounded-md text-muted hover:text-red-500 hover:bg-red-500/10 transition-colors shrink-0"
                  title={t("unlink")}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Link modal */}
        {showLinkModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowLinkModal(false)}>
            <div
              className="bg-surface rounded-xl border border-border shadow-xl w-full max-w-lg mx-4 max-h-[75vh] flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-5 py-3 border-b border-border shrink-0">
                <h3 className="font-semibold">{t("linkDocs")}</h3>
                <button
                  onClick={() => setShowLinkModal(false)}
                  className="p-1.5 rounded-md text-muted hover:text-foreground hover:bg-surface-secondary transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>

              <div className="px-5 py-3 border-b border-border shrink-0">
                <input
                  type="text"
                  value={searchGlobal}
                  onChange={(e) => setSearchGlobal(e.target.value)}
                  placeholder={t("searchPlaceholder")}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-surface-secondary text-sm focus:outline-none focus:ring-2 focus:ring-accent/20"
                />
              </div>

              <div className="flex-1 overflow-y-auto p-3 space-y-1">
                {globalLoading ? (
                  <div className="flex justify-center py-8">
                    <div className="w-6 h-6 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
                  </div>
                ) : globalDocs.length === 0 ? (
                  <p className="text-center py-8 text-muted text-sm">{t("noGlobalDocs")}</p>
                ) : (
                  globalDocs.map((doc) => {
                    const isSelected = selectedIds.has(doc._id);
                    return (
                      <label
                        key={doc._id}
                        className={`flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
                          isSelected
                            ? "bg-accent/10 border border-accent/20"
                            : "hover:bg-surface-secondary border border-transparent"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => toggleSelect(doc._id)}
                          className="w-4 h-4 rounded border-border text-accent focus:ring-accent/20"
                        />
                        <span className="text-sm font-bold text-violet-500 bg-violet-500/10 px-2 py-0.5 rounded shrink-0">MD</span>
                        <div className="flex-1 min-w-0">
                          <span className="text-sm truncate block">{doc.title}</span>
                          <span className="text-xs text-muted">
                            {doc.word_count?.toLocaleString() || 0} 字
                          </span>
                        </div>
                      </label>
                    );
                  })
                )}
              </div>

              <div className="flex justify-end gap-3 px-5 py-3 border-t border-border shrink-0">
                <button
                  onClick={() => setShowLinkModal(false)}
                  className="px-4 py-2 rounded-lg text-sm border border-border hover:bg-surface-secondary transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleLink}
                  disabled={linking || selectedIds.size === 0}
                  className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90 disabled:opacity-50 transition-colors"
                >
                  {linking ? "..." : t("linkDocs")}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
