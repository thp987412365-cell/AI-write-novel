"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { apiGet, apiDelete } from "@/lib/api";

interface LLMLogItem {
  _id: string;
  provider: string;
  model: string;
  system_prompt: string;
  messages: { role: string; content: string }[];
  temperature: number | null;
  max_tokens: number | null;
  response_content: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  duration_ms: number;
  finish_reason: string;
  success: boolean;
  error: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

interface LLMLogListResponse {
  data: LLMLogItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export function LLMLogCard() {
  const t = useTranslations("settings.llmLog");
  const [logs, setLogs] = useState<LLMLogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [providerFilter, setProviderFilter] = useState("");
  const [successFilter, setSuccessFilter] = useState<string>("");

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLog, setDetailLog] = useState<LLMLogItem | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const [clearing, setClearing] = useState(false);

  const pageSize = 20;

  const fetchLogs = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("page_size", String(pageSize));
      if (providerFilter) params.set("provider", providerFilter);
      if (successFilter !== "") params.set("success", successFilter);

      const res = await apiGet<LLMLogListResponse>(
        `/api/llm-logs?${params.toString()}`
      );
      setLogs(res.data || []);
      setTotal(res.total);
      setTotalPages(res.total_pages);
      setError("");
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [page, providerFilter, successFilter]);

  useEffect(() => {
    setPage(1);
  }, [providerFilter, successFilter]);

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  const openDetail = async (log: LLMLogItem) => {
    setDetailLog(log);
    setDetailOpen(true);
    setDetailLoading(true);
    try {
      const res = await apiGet<{ data: LLMLogItem }>(`/api/llm-logs/${log._id}`);
      setDetailLog(res.data);
    } catch {
    } finally {
      setDetailLoading(false);
    }
  };

  const handleClearAll = async () => {
    if (!confirm(t("clearConfirm"))) return;
    setClearing(true);
    try {
      await apiDelete("/api/llm-logs");
      setPage(1);
      await fetchLogs();
    } catch (e) {
      setError(String(e));
    } finally {
      setClearing(false);
    }
  };

  const formatTime = (dateStr: string) => {
    if (!dateStr) return "";
    try {
      return new Date(dateStr).toLocaleString("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      });
    } catch {
      return dateStr;
    }
  };

  const truncateContent = (content: string, maxLen = 150) => {
    if (!content) return "";
    if (content.length <= maxLen) return content;
    return content.slice(0, maxLen) + "……";
  };

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center gap-3 flex-wrap">
        <span className="text-xs text-muted">
          {t("totalCount", { count: total })}
        </span>

        <input
          type="text"
          value={providerFilter}
          onChange={(e) => setProviderFilter(e.target.value)}
          placeholder={t("filterProvider")}
          className="w-36 px-3 py-1.5 rounded-lg border border-border bg-surface-secondary text-sm focus:outline-none focus:ring-2 focus:ring-accent/20"
        />

        <select
          value={successFilter}
          onChange={(e) => setSuccessFilter(e.target.value)}
          className="px-3 py-1.5 rounded-lg border border-border bg-surface-secondary text-sm focus:outline-none focus:ring-2 focus:ring-accent/20"
        >
          <option value="">{t("allStatus")}</option>
          <option value="true">{t("successOnly")}</option>
          <option value="false">{t("failedOnly")}</option>
        </select>

        <div className="flex-1" />

        <button
          onClick={handleClearAll}
          disabled={clearing || total === 0}
          className="px-3 py-1.5 rounded-lg border border-red-500/30 bg-red-500/10 text-red-600 text-sm hover:bg-red-500/20 transition-colors disabled:opacity-50"
        >
          {clearing ? t("clearing") : t("clearAll")}
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* Log list */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-6 h-6 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
        </div>
      ) : logs.length === 0 ? (
        <div className="text-center py-12 text-muted text-sm">{t("noLogs")}</div>
      ) : (
        <>
          <div className="space-y-1.5">
            {logs.map((log) => (
              <div
                key={log._id}
                onClick={() => openDetail(log)}
                className="flex items-center gap-3 px-4 py-2.5 rounded-lg border border-border bg-surface hover:bg-surface-secondary/50 transition-colors cursor-pointer"
              >
                {/* Status dot */}
                <span
                  className={`w-2 h-2 rounded-full shrink-0 ${
                    log.success ? "bg-green-500" : "bg-red-500"
                  }`}
                  title={log.success ? "成功" : "失败"}
                />

                {/* Provider / Model */}
                <div className="shrink-0 min-w-[120px]">
                  <div className="text-sm font-medium">{log.provider || "-"}</div>
                  <div className="text-xs text-muted">{log.model || "-"}</div>
                </div>

                {/* Prompt preview */}
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-muted truncate">
                    {truncateContent(
                      log.messages?.[0]?.content || log.system_prompt || ""
                    )}
                  </div>
                </div>

                {/* Token usage & duration */}
                <div className="shrink-0 flex items-center gap-3 text-xs text-muted">
                  <span title="Input / Output tokens">
                    {log.input_tokens} / {log.output_tokens}
                  </span>
                  <span>{log.duration_ms}ms</span>
                </div>

                {/* Timestamp */}
                <div className="shrink-0 text-xs text-muted w-[140px] text-right">
                  {formatTime(log.created_at)}
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="px-3 py-1.5 rounded-lg border border-border text-sm hover:bg-surface-secondary disabled:opacity-40"
              >
                {t("prev")}
              </button>
              <span className="text-sm text-muted">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-3 py-1.5 rounded-lg border border-border text-sm hover:bg-surface-secondary disabled:opacity-40"
              >
                {t("next")}
              </button>
            </div>
          )}
        </>
      )}

      {/* Detail Modal */}
      {detailOpen && detailLog && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setDetailOpen(false)}
        >
          <div
            className="bg-surface rounded-xl border border-border shadow-2xl w-full max-w-4xl max-h-[85vh] overflow-hidden flex flex-col mx-4"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-3 border-b border-border">
              <div>
                <span
                  className={`inline-flex items-center gap-1.5 text-sm font-medium ${
                    detailLog.success ? "text-green-600" : "text-red-600"
                  }`}
                >
                  <span
                    className={`w-2 h-2 rounded-full ${
                      detailLog.success ? "bg-green-500" : "bg-red-500"
                    }`}
                  />
                  {detailLog.provider} / {detailLog.model}
                </span>
                <span className="ml-3 text-xs text-muted">
                  {formatTime(detailLog.created_at)}
                </span>
              </div>
              <button
                onClick={() => setDetailOpen(false)}
                className="p-1.5 rounded-lg hover:bg-surface-secondary text-muted transition-colors"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            {/* Meta info */}
            <div className="flex items-center gap-4 px-5 py-2 text-xs text-muted border-b border-border/50">
              <span>{t("inputTokens")}: {detailLog.input_tokens}</span>
              <span>{t("outputTokens")}: {detailLog.output_tokens}</span>
              <span>{t("totalTokens")}: {detailLog.total_tokens}</span>
              <span>{t("duration")}: {detailLog.duration_ms}ms</span>
              {detailLog.finish_reason && (
                <span>{t("finishReason")}: {detailLog.finish_reason}</span>
              )}
              {detailLog.temperature != null && (
                <span>Temp: {detailLog.temperature}</span>
              )}
              {detailLog.max_tokens != null && (
                <span>max_tokens: {detailLog.max_tokens}</span>
              )}
            </div>

            {/* Content */}
            {detailLoading ? (
              <div className="flex items-center justify-center py-16">
                <div className="w-6 h-6 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
              </div>
            ) : (
              <div className="flex-1 overflow-auto p-5 space-y-4">
                {/* System Prompt */}
                {detailLog.system_prompt && (
                  <div>
                    <div className="text-xs font-medium text-muted mb-1.5 uppercase tracking-wide">
                      {t("systemPrompt")}
                    </div>
                    <pre className="p-3 rounded-lg bg-surface-secondary border border-border text-sm whitespace-pre-wrap break-words max-h-[200px] overflow-auto">
                      {detailLog.system_prompt}
                    </pre>
                  </div>
                )}

                {/* User Messages (Prompt) */}
                <div>
                  <div className="text-xs font-medium text-muted mb-1.5 uppercase tracking-wide">
                    {t("userPrompt")}
                  </div>
                  {detailLog.messages?.map((msg, idx) => (
                    <pre
                      key={idx}
                      className="p-3 rounded-lg bg-surface-secondary border border-border text-sm whitespace-pre-wrap break-words max-h-[300px] overflow-auto mt-1"
                    >
                      {msg.content}
                    </pre>
                  ))}
                </div>

                {/* Error */}
                {!detailLog.success && detailLog.error && (
                  <div>
                    <div className="text-xs font-medium text-red-500 mb-1.5 uppercase tracking-wide">
                      {t("error")}
                    </div>
                    <pre className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 text-sm whitespace-pre-wrap break-words max-h-[200px] overflow-auto">
                      {detailLog.error}
                    </pre>
                  </div>
                )}

                {/* Response */}
                <div>
                  <div className="text-xs font-medium text-muted mb-1.5 uppercase tracking-wide">
                    {t("response")}
                  </div>
                  <pre className="p-3 rounded-lg bg-surface-secondary border border-border text-sm whitespace-pre-wrap break-words max-h-[400px] overflow-auto">
                    {detailLog.response_content || t("emptyResponse")}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
