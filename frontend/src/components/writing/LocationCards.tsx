"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Button, Chip } from "@heroui/react";
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api";
import type { Location } from "@/types/novel";

interface LocationCardsProps {
  novelId: string;
}

const TYPE_OPTIONS = [
  { value: "city", labelKey: "filterCity" },
  { value: "realm", labelKey: "filterCity" },
  { value: "building", labelKey: "filterBuilding" },
  { value: "dungeon", labelKey: "filterWilderness" },
  { value: "wilderness", labelKey: "filterWilderness" },
  { value: "dimension", labelKey: "filterWilderness" },
];

export default function LocationCards({ novelId }: LocationCardsProps) {
  const t = useTranslations("writing.locationCards");
  const [locations, setLocations] = useState<Location[]>([]);
  const [filterType, setFilterType] = useState<string>("");
  const [selected, setSelected] = useState<Location | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<Location>>({});
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filterType) params.set("type", filterType);
      const qs = params.toString();
      const res = await apiGet<{ data: Location[] }>(`/api/locations/novel/${novelId}${qs ? "?" + qs : ""}`);
      setLocations(res.data);
    } catch {
    } finally {
      setLoading(false);
    }
  }, [novelId, filterType]);

  useEffect(() => { load(); }, [load]);

  const createNew = () => {
    setForm({ name: "", type: "city", description: "", climate: "", culture: "", significance: "", notable_features: [] });
    setSelected(null);
    setEditing(true);
  };

  const startEdit = (loc: Location) => {
    setForm({ ...loc });
    setSelected(loc);
    setEditing(true);
  };

  const saveLocation = async () => {
    try {
      if (selected) {
        await apiPut(`/api/locations/${selected._id}`, form);
      } else {
        await apiPost("/api/locations/create", { ...form, novel_id: novelId });
      }
      setEditing(false);
      setSelected(null);
      await load();
    } catch {
    }
  };

  const deleteLocation = async (id: string) => {
    try {
      await apiDelete(`/api/locations/${id}`);
      if (selected?._id === id) setSelected(null);
      setEditing(false);
      await load();
    } catch {
    }
  };

  const typeLabel = (type: string) => {
    const opt = TYPE_OPTIONS.find((o) => o.value === type);
    return opt ? t(opt.labelKey as never) : type;
  };

  const renderForm = () => (
    <div className="space-y-3">
      <div>
        <label className="text-xs font-medium text-muted">名称</label>
        <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">类型</label>
        <select className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.type || "city"} onChange={(e) => setForm({ ...form, type: e.target.value })}>
          <option value="city">城市/国家</option>
          <option value="realm">大陆/领域</option>
          <option value="building">建筑/场所</option>
          <option value="dungeon">秘境/遗迹</option>
          <option value="wilderness">野外区域</option>
          <option value="dimension">异空间/维度</option>
        </select>
      </div>
      <div>
        <label className="text-xs font-medium text-muted">描述</label>
        <textarea className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm resize-y" rows={3} value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">气候/环境</label>
        <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.climate || ""} onChange={(e) => setForm({ ...form, climate: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">文化/风俗</label>
        <textarea className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm resize-y" rows={2} value={form.culture || ""} onChange={(e) => setForm({ ...form, culture: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">主线作用</label>
        <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.significance || ""} onChange={(e) => setForm({ ...form, significance: e.target.value })} />
      </div>
      <div className="flex gap-2 pt-2">
        <Button variant="primary" size="sm" onPress={saveLocation}>保存</Button>
        <Button variant="ghost" size="sm" onPress={() => { setEditing(false); setSelected(null); }}>取消</Button>
      </div>
    </div>
  );

  if (loading) return <div className="flex items-center justify-center h-64"><p className="text-muted text-sm">加载中...</p></div>;

  return (
    <div className="h-full flex">
      <div className="w-60 border-r border-border overflow-y-auto shrink-0 p-3 space-y-3">
        <Button variant="primary" size="sm" className="w-full" onPress={createNew}>{t("createLocation")}</Button>
        <div className="flex flex-wrap gap-1">
          <button className={`text-xs px-2 py-1 rounded-full border ${filterType === "" ? "bg-primary/10 border-primary text-primary" : "border-border text-muted"}`} onClick={() => setFilterType("")}>{t("filterAll")}</button>
          {TYPE_OPTIONS.filter((o, i, arr) => arr.findIndex((x) => x.labelKey === o.labelKey) === i).map((o) => (
            <button key={o.labelKey} className={`text-xs px-2 py-1 rounded-full border ${filterType === o.value ? "bg-primary/10 border-primary text-primary" : "border-border text-muted"}`} onClick={() => setFilterType(o.value)}>
              {t(o.labelKey as never)}
            </button>
          ))}
        </div>
        {locations.length === 0 ? (
          <p className="text-xs text-muted text-center">{t("noLocations")}</p>
        ) : (
          locations.map((loc) => (
            <button key={loc._id} className={`w-full text-left p-2 rounded-lg border text-sm hover:bg-muted/5 transition-colors ${selected?._id === loc._id ? "border-primary bg-primary/5" : "border-border"}`} onClick={() => { setSelected(loc); setEditing(false); }}>
              <div className="font-medium text-foreground">{loc.name}</div>
              <Chip size="sm" variant="soft">{typeLabel(loc.type)}</Chip>
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
                <Button variant="ghost" size="sm" className="text-red-500" onPress={() => deleteLocation(selected._id)}>删除</Button>
              </div>
            </div>
            <Chip variant="soft">{typeLabel(selected.type)}</Chip>
            {selected.description && <Field label="描述" value={selected.description} />}
            {selected.climate && <Field label="气候/环境" value={selected.climate} />}
            {selected.culture && <Field label="文化/风俗" value={selected.culture} />}
            {selected.history && <Field label="历史沿革" value={selected.history} />}
            {selected.significance && <Field label="主线作用" value={selected.significance} />}
            {selected.notable_features?.length > 0 && <div><span className="text-xs font-medium text-muted">显著特征</span><div className="flex flex-wrap gap-1 mt-1">{selected.notable_features.map((f, i) => <Chip key={i} variant="soft" size="sm">{f}</Chip>)}</div></div>}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full"><p className="text-muted text-sm">选择左侧地点查看详情</p></div>
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
