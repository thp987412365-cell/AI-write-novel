"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Button, Chip } from "@heroui/react";
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api";
import type { Faction } from "@/types/novel";

interface FactionCardsProps {
  novelId: string;
}

export default function FactionCards({ novelId }: FactionCardsProps) {
  const t = useTranslations("writing.factionCards");
  const [factions, setFactions] = useState<Faction[]>([]);
  const [selected, setSelected] = useState<Faction | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<Faction>>({});
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await apiGet<{ data: Faction[] }>(`/api/factions/novel/${novelId}`);
      setFactions(res.data);
    } catch {
    } finally {
      setLoading(false);
    }
  }, [novelId]);

  useEffect(() => { load(); }, [load]);

  const createNew = () => {
    setForm({ name: "", level_type: "core", faction_type: "", positioning: "", core_goal: "", is_public: true });
    setSelected(null);
    setEditing(true);
  };

  const startEdit = (f: Faction) => {
    setForm({ ...f });
    setSelected(f);
    setEditing(true);
  };

  const saveFaction = async () => {
    try {
      if (selected) {
        await apiPut(`/api/factions/${selected.faction_id}`, form);
      } else {
        await apiPost("/api/factions/create", { ...form, novel_id: novelId });
      }
      setEditing(false);
      setSelected(null);
      await load();
    } catch {
    }
  };

  const deleteFaction = async (factionId: string) => {
    try {
      await apiDelete(`/api/factions/${factionId}`);
      if (selected?.faction_id === factionId) setSelected(null);
      setEditing(false);
      await load();
    } catch {
    }
  };

  const levelLabel = (lv: string) => {
    const map: Record<string, string> = { core: t("levelCore"), major_volume: t("levelMajor"), minor: t("levelMinor") };
    return map[lv] || lv;
  };

  const renderForm = () => (
    <div className="space-y-3">
      <div>
        <label className="text-xs font-medium text-muted">名称</label>
        <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-medium text-muted">层级</label>
          <select className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.level_type || "core"} onChange={(e) => setForm({ ...form, level_type: e.target.value })}>
            <option value="core">核心势力</option>
            <option value="major_volume">主要势力</option>
            <option value="minor">次要势力</option>
          </select>
        </div>
        <div>
          <label className="text-xs font-medium text-muted">类型</label>
          <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.faction_type || ""} onChange={(e) => setForm({ ...form, faction_type: e.target.value })} placeholder="宗门/王朝/组织..." />
        </div>
      </div>
      <div>
        <label className="text-xs font-medium text-muted">定位</label>
        <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.positioning || ""} onChange={(e) => setForm({ ...form, positioning: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">核心目标</label>
        <textarea className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm resize-y" rows={2} value={form.core_goal || ""} onChange={(e) => setForm({ ...form, core_goal: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">公开立场</label>
        <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.public_stance || ""} onChange={(e) => setForm({ ...form, public_stance: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">隐藏目标</label>
        <textarea className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm resize-y" rows={2} value={form.hidden_goal || ""} onChange={(e) => setForm({ ...form, hidden_goal: e.target.value })} />
      </div>
      <div className="flex gap-2 pt-2">
        <Button variant="primary" size="sm" onPress={saveFaction}>保存</Button>
        <Button variant="ghost" size="sm" onPress={() => { setEditing(false); setSelected(null); }}>取消</Button>
      </div>
    </div>
  );

  if (loading) return <div className="flex items-center justify-center h-64"><p className="text-muted text-sm">加载中...</p></div>;

  return (
    <div className="h-full flex">
      <div className="w-60 border-r border-border overflow-y-auto shrink-0 p-3 space-y-3">
        <Button variant="primary" size="sm" className="w-full" onPress={createNew}>{t("createFaction")}</Button>
        {factions.length === 0 ? (
          <p className="text-xs text-muted text-center">{t("noFactions")}</p>
        ) : (
          factions.map((f) => (
            <button key={f.faction_id} className={`w-full text-left p-2 rounded-lg border text-sm hover:bg-muted/5 transition-colors ${selected?.faction_id === f.faction_id ? "border-primary bg-primary/5" : "border-border"}`} onClick={() => { setSelected(f); setEditing(false); }}>
              <div className="font-medium text-foreground">{f.name}</div>
              <div className="text-xs text-muted flex items-center gap-1">
                <Chip size="sm" variant="soft">{levelLabel(f.level_type)}</Chip>
                <span>{f.is_public ? "公开" : "隐藏"}</span>
              </div>
            </button>
          ))
        )}
      </div>

      <div className="flex-1 min-w-0 overflow-y-auto p-5">
        {editing ? renderForm() : selected ? (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-foreground">{selected.name}</h2>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onPress={() => startEdit(selected)}>编辑</Button>
                <Button variant="ghost" size="sm" className="text-red-500" onPress={() => deleteFaction(selected.faction_id)}>删除</Button>
              </div>
            </div>
            <div className="flex gap-2">
              <Chip variant="soft">{levelLabel(selected.level_type)}</Chip>
              {selected.faction_type && <Chip variant="soft">{selected.faction_type}</Chip>}
              <Chip variant="soft">{selected.is_public ? "公开" : "隐藏"}</Chip>
              <Chip variant="soft">{selected.active_status === "active" ? "活跃" : selected.active_status}</Chip>
            </div>
            {selected.positioning && <Field label="定位" value={selected.positioning} />}
            {selected.public_stance && <Field label="公开立场" value={selected.public_stance} />}
            {selected.core_goal && <Field label="核心目标" value={selected.core_goal} />}
            {selected.hidden_goal && <Field label="隐藏目标" value={selected.hidden_goal} />}
            {selected.organization_style && <Field label="组织风格" value={selected.organization_style} />}
            {selected.core_values?.length > 0 && <div><span className="text-xs font-medium text-muted">核心价值观</span><div className="flex flex-wrap gap-1 mt-1">{selected.core_values.map((v, i) => <Chip key={i} variant="soft" size="sm">{v}</Chip>)}</div></div>}
            {selected.resources_and_advantages?.length > 0 && <div><span className="text-xs font-medium text-muted">资源与优势</span><div className="flex flex-wrap gap-1 mt-1">{selected.resources_and_advantages.map((r, i) => <Chip key={i} variant="soft" size="sm">{r}</Chip>)}</div></div>}
            {selected.conflict_with_mainline && <Field label="主线冲突" value={selected.conflict_with_mainline} />}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full"><p className="text-muted text-sm">选择左侧势力查看详情</p></div>
        )}
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-xs font-medium text-muted">{label}</span>
      <p className="text-sm text-foreground mt-0.5 whitespace-pre-wrap">{value}</p>
    </div>
  );
}
