"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Button, Chip } from "@heroui/react";
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api";
import type { Rule } from "@/types/novel";

interface RuleCardsProps {
  novelId: string;
}

const CATEGORY_FILTERS = [
  { value: "", labelKey: "filterAll" },
  { value: "magic_system", labelKey: "filterMagic" },
  { value: "cultivation", labelKey: "filterMagic" },
  { value: "social", labelKey: "filterSocial" },
  { value: "law", labelKey: "filterSocial" },
  { value: "technology", labelKey: "filterTechnology" },
  { value: "custom", labelKey: "filterCustom" },
];

export default function RuleCards({ novelId }: RuleCardsProps) {
  const t = useTranslations("writing.ruleCards");
  const [rules, setRules] = useState<Rule[]>([]);
  const [filterCat, setFilterCat] = useState<string>("");
  const [selected, setSelected] = useState<Rule | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<Rule>>({});
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filterCat) params.set("category", filterCat);
      const qs = params.toString();
      const res = await apiGet<{ data: Rule[] }>(`/api/rules/novel/${novelId}${qs ? "?" + qs : ""}`);
      setRules(res.data);
    } catch {
    } finally {
      setLoading(false);
    }
  }, [novelId, filterCat]);

  useEffect(() => { load(); }, [load]);

  const createNew = () => {
    setForm({ name: "", category: "custom", description: "", principles: [], exceptions: [], limitations: "", impact_on_plot: "" });
    setSelected(null);
    setEditing(true);
  };

  const startEdit = (r: Rule) => {
    setForm({ ...r });
    setSelected(r);
    setEditing(true);
  };

  const saveRule = async () => {
    try {
      if (selected) {
        await apiPut(`/api/rules/${selected._id}`, form);
      } else {
        await apiPost("/api/rules/create", { ...form, novel_id: novelId });
      }
      setEditing(false);
      setSelected(null);
      await load();
    } catch {
    }
  };

  const deleteRule = async (id: string) => {
    try {
      await apiDelete(`/api/rules/${id}`);
      if (selected?._id === id) setSelected(null);
      setEditing(false);
      await load();
    } catch {
    }
  };

  const catLabel = (c: string) => {
    const map: Record<string, string> = { magic_system: "修炼/魔法", cultivation: "修炼/魔法", social: "社会/法律", law: "社会/法律", technology: "科技", custom: "自定义" };
    return map[c] || c;
  };

  const uniqueFilters = CATEGORY_FILTERS.filter((f, i, arr) => !f.value || arr.findIndex((x) => x.labelKey === f.labelKey) === i);

  const renderForm = () => (
    <div className="space-y-3">
      <div>
        <label className="text-xs font-medium text-muted">名称</label>
        <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">分类</label>
        <select className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.category || "custom"} onChange={(e) => setForm({ ...form, category: e.target.value })}>
          <option value="magic_system">修炼/魔法体系</option>
          <option value="cultivation">修炼体系</option>
          <option value="social">社会体系</option>
          <option value="law">法律体系</option>
          <option value="technology">科技体系</option>
          <option value="biology">生物/种族体系</option>
          <option value="physics">物理法则</option>
          <option value="custom">自定义</option>
        </select>
      </div>
      <div>
        <label className="text-xs font-medium text-muted">详细说明</label>
        <textarea className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm resize-y" rows={3} value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">限制条件</label>
        <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.limitations || ""} onChange={(e) => setForm({ ...form, limitations: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">对剧情的影响</label>
        <textarea className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm resize-y" rows={2} value={form.impact_on_plot || ""} onChange={(e) => setForm({ ...form, impact_on_plot: e.target.value })} />
      </div>
      <div className="flex gap-2 pt-2">
        <Button variant="primary" size="sm" onPress={saveRule}>保存</Button>
        <Button variant="ghost" size="sm" onPress={() => { setEditing(false); setSelected(null); }}>取消</Button>
      </div>
    </div>
  );

  if (loading) return <div className="flex items-center justify-center h-64"><p className="text-muted text-sm">加载中...</p></div>;

  return (
    <div className="h-full flex">
      <div className="w-60 border-r border-border overflow-y-auto shrink-0 p-3 space-y-3">
        <Button variant="primary" size="sm" className="w-full" onPress={createNew}>{t("createRule")}</Button>
        <div className="flex flex-wrap gap-1">
          {uniqueFilters.map((f) => (
            <button key={f.value} className={`text-xs px-2 py-1 rounded-full border ${filterCat === f.value ? "bg-primary/10 border-primary text-primary" : "border-border text-muted"}`} onClick={() => setFilterCat(f.value)}>
              {f.value === "" ? t("filterAll") : catLabel(f.value)}
            </button>
          ))}
        </div>
        {rules.length === 0 ? (
          <p className="text-xs text-muted text-center">{t("noRules")}</p>
        ) : (
          rules.map((r) => (
            <button key={r._id} className={`w-full text-left p-2 rounded-lg border text-sm hover:bg-muted/5 transition-colors ${selected?._id === r._id ? "border-primary bg-primary/5" : "border-border"}`} onClick={() => { setSelected(r); setEditing(false); }}>
              <div className="font-medium text-foreground">{r.name}</div>
              <Chip size="sm" variant="soft">{catLabel(r.category)}</Chip>
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
                <Button variant="ghost" size="sm" className="text-red-500" onPress={() => deleteRule(selected._id)}>删除</Button>
              </div>
            </div>
            <Chip variant="soft">{catLabel(selected.category)}</Chip>
            {selected.description && <Field label="详细说明" value={selected.description} />}
            {selected.limitations && <Field label="限制条件" value={selected.limitations} />}
            {selected.impact_on_plot && <Field label="对剧情影响" value={selected.impact_on_plot} />}
            {selected.principles?.length > 0 && <div><span className="text-xs font-medium text-muted">核心法则</span><ul className="list-disc list-inside text-sm mt-1">{selected.principles.map((p, i) => <li key={i}>{p}</li>)}</ul></div>}
            {selected.exceptions?.length > 0 && <div><span className="text-xs font-medium text-muted">特殊情况</span><ul className="list-disc list-inside text-sm mt-1">{selected.exceptions.map((e, i) => <li key={i}>{e}</li>)}</ul></div>}
            {selected.related_factions?.length > 0 && <div><span className="text-xs font-medium text-muted">相关势力</span><div className="flex flex-wrap gap-1 mt-1">{selected.related_factions.map((f, i) => <Chip key={i} variant="soft" size="sm">{f}</Chip>)}</div></div>}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full"><p className="text-muted text-sm">选择左侧规则查看详情</p></div>
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
