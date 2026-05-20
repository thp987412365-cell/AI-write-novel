"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api";
import type { KnowledgeDoc } from "@/types/novel";

export function KnowledgeCard() {
  const t = useTranslations("settings.knowledge");
  const [docs, setDocs] = useState<KnowledgeDoc[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");

  // Create / Edit modal
  const [showEditor, setShowEditor] = useState(false);
  const [editingDoc, setEditingDoc] = useState<KnowledgeDoc | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);

  // Preview
  const [previewDoc, setPreviewDoc] = useState<KnowledgeDoc | null>(null);
  const [previewContent, setPreviewContent] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);

  const fetchDocs = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (search) params.set("keyword", search);
      const res = await apiGet<{ data: KnowledgeDoc[] }>(
        `/api/knowledge/docs?${params.toString()}`
      );
      setDocs(res.data || []);
      setError("");
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => {
    fetchDocs();
  }, [fetchDocs]);

  // ---- Create ----
  const openCreate = () => {
    setEditingDoc(null);
    setEditTitle("");
    setEditContent("");
    setShowEditor(true);
  };

  // ---- Edit ----
  const openEdit = async (doc: KnowledgeDoc) => {
    try {
      const res = await apiGet<{ data: KnowledgeDoc }>(
        `/api/knowledge/docs/${doc._id}`
      );
      const full = res.data;
      setEditingDoc(full);
      setEditTitle(full.title);
      setEditContent(full.content || "");
      setShowEditor(true);
    } catch (e) {
      setError(String(e));
    }
  };

  const handleSave = async () => {
    if (!editTitle.trim() || !editContent.trim()) {
      setError("标题和内容不能为空");
      return;
    }
    setSaving(true);
    setError("");
    try {
      if (editingDoc) {
        await apiPut(`/api/knowledge/docs/${editingDoc._id}`, {
          title: editTitle.trim(),
          content: editContent,
        });
      } else {
        await apiPost("/api/knowledge/docs", {
          title: editTitle.trim(),
          content: editContent,
        });
      }
      setShowEditor(false);
      await fetchDocs();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  // ---- Delete ----
  const handleDelete = async (doc: KnowledgeDoc) => {
    if (!confirm(t("deleteConfirm", { title: doc.title }))) return;
    try {
      await apiDelete(`/api/knowledge/docs/${doc._id}`);
      await fetchDocs();
      if (previewDoc?._id === doc._id) setPreviewDoc(null);
    } catch (e) {
      setError(String(e));
    }
  };

  // ---- Preview ----
  const handlePreview = async (doc: KnowledgeDoc) => {
    setPreviewDoc(doc);
    setPreviewLoading(true);
    try {
      const res = await apiGet<{ data: KnowledgeDoc }>(
        `/api/knowledge/docs/${doc._id}`
      );
      setPreviewContent(res.data.content || "");
    } catch (e) {
      setPreviewContent("加载失败: " + String(e));
    } finally {
      setPreviewLoading(false);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "";
    try {
      return new Date(dateStr).toLocaleDateString("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={openCreate}
          className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90 transition-colors flex items-center gap-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          {t("createDoc")}
        </button>
        <span className="text-xs text-muted">{t("createHint")}</span>

        <div className="flex-1" />

        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t("search")}
          className="w-48 px-3 py-2 rounded-lg border border-border bg-surface-secondary text-sm focus:outline-none focus:ring-2 focus:ring-accent/20"
        />
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* Doc list */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-6 h-6 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
        </div>
      ) : docs.length === 0 ? (
        <div className="text-center py-12 text-muted text-sm">{t("noDocs")}</div>
      ) : (
        <div className="space-y-2">
          {docs.map((doc) => (
            <div
              key={doc._id}
              className="flex items-center gap-3 px-4 py-3 rounded-lg border border-border bg-surface hover:bg-surface-secondary/50 transition-colors"
            >
              <span className="text-sm font-bold text-violet-500 bg-violet-500/10 px-2 py-0.5 rounded shrink-0">
                MD
              </span>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium truncate">{doc.title}</span>
                </div>
                <div className="flex items-center gap-3 text-xs text-muted mt-0.5">
                  <span>{t("wordCount")}: {doc.word_count?.toLocaleString() || 0}</span>
                  <span>{formatDate(doc.updated_at || doc.created_at)}</span>
                </div>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  onClick={() => handlePreview(doc)}
                  className="p-1.5 rounded-md text-muted hover:text-foreground hover:bg-surface-secondary transition-colors"
                  title={t("preview")}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </button>
                <button
                  onClick={() => openEdit(doc)}
                  className="p-1.5 rounded-md text-muted hover:text-foreground hover:bg-surface-secondary transition-colors"
                  title={t("edit")}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M12 20h9" />
                    <path d="M16.376 3.622a1 1 0 0 1 3.002 3.002L7.368 18.635a2 2 0 0 1-.855.506l-2.872.838a.5.5 0 0 1-.62-.62l.838-2.872a2 2 0 0 1 .506-.854z" />
                  </svg>
                </button>
                <button
                  onClick={() => handleDelete(doc)}
                  className="p-1.5 rounded-md text-muted hover:text-red-500 hover:bg-red-500/10 transition-colors"
                  title={t("delete")}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="3 6 5 6 21 6" />
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create/Edit Modal */}
      {showEditor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setShowEditor(false)}>
          <div
            className="bg-surface rounded-xl border border-border shadow-xl w-full max-w-3xl mx-4 max-h-[90vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-3 border-b border-border shrink-0">
              <h3 className="font-semibold">
                {editingDoc ? t("editDoc") : t("createDoc")}
              </h3>
              <button
                onClick={() => setShowEditor(false)}
                className="p-1.5 rounded-md text-muted hover:text-foreground hover:bg-surface-secondary transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div className="p-5 space-y-4 flex-1 overflow-y-auto">
              <div>
                <label className="text-xs text-muted block mb-1">{t("docTitle")}</label>
                <input
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  placeholder={t("titlePlaceholder")}
                  className="w-full px-3 py-2 rounded-lg border border-border bg-surface-secondary text-sm focus:outline-none focus:ring-2 focus:ring-accent/20"
                />
              </div>

              <div className="flex-1 flex flex-col min-h-0">
                <label className="text-xs text-muted block mb-1">
                  {t("docContent")} <span className="text-muted/60">(Markdown)</span>
                </label>
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  placeholder={t("contentPlaceholder")}
                  rows={20}
                  className="w-full flex-1 min-h-[400px] px-3 py-2 rounded-lg border border-border bg-surface-secondary text-sm font-mono focus:outline-none focus:ring-2 focus:ring-accent/20 resize-none leading-relaxed"
                  spellCheck={false}
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 px-5 py-3 border-t border-border shrink-0">
              <button
                onClick={() => setShowEditor(false)}
                className="px-4 py-2 rounded-lg text-sm border border-border hover:bg-surface-secondary transition-colors"
              >
                {t("cancel")}
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent/90 disabled:opacity-50 transition-colors"
              >
                {saving ? "..." : t("save")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Preview modal */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setPreviewDoc(null)}>
          <div
            className="bg-surface rounded-xl border border-border shadow-xl w-full max-w-3xl mx-4 max-h-[80vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-3 border-b border-border">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-violet-500 bg-violet-500/10 px-1.5 py-0.5 rounded">MD</span>
                <h3 className="font-semibold truncate">{previewDoc.title}</h3>
              </div>
              <button
                onClick={() => setPreviewDoc(null)}
                className="p-1.5 rounded-md text-muted hover:text-foreground hover:bg-surface-secondary transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-5">
              {previewLoading ? (
                <div className="flex justify-center py-8">
                  <div className="w-6 h-6 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
                </div>
              ) : (
                <pre className="text-sm whitespace-pre-wrap font-mono leading-relaxed text-muted">
                  {previewContent}
                </pre>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
