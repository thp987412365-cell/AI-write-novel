"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Button, Chip } from "@heroui/react";
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api";
import type { Item } from "@/types/novel";

interface ItemCardsProps {
  novelId: string;
}

const RARITY_COLORS: Record<string, string> = {
  common: "bg-gray-500", uncommon: "bg-green-500", rare: "bg-blue-500",
  epic: "bg-purple-500", legendary: "bg-amber-500",
};

export default function ItemCards({ novelId }: ItemCardsProps) {
  const t = useTranslations("writing.itemCards");
  const [items, setItems] = useState<Item[]>([]);
  const [filterType, setFilterType] = useState<string>("");
  const [selected, setSelected] = useState<Item | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<Item>>({});
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (filterType) params.set("type", filterType);
      const qs = params.toString();
      const res = await apiGet<{ data: Item[] }>(`/api/items/novel/${novelId}${qs ? "?" + qs : ""}`);
      setItems(res.data);
    } catch {
    } finally {
      setLoading(false);
    }
  }, [novelId, filterType]);

  useEffect(() => { load(); }, [load]);

  const createNew = () => {
    setForm({ name: "", type: "artifact", rarity: "common", description: "", abilities: [], origin: "", significance: "" });
    setSelected(null);
    setEditing(true);
  };

  const startEdit = (item: Item) => {
    setForm({ ...item });
    setSelected(item);
    setEditing(true);
  };

  const saveItem = async () => {
    try {
      if (selected) {
        await apiPut(`/api/items/${selected._id}`, form);
      } else {
        await apiPost("/api/items/create", { ...form, novel_id: novelId });
      }
      setEditing(false);
      setSelected(null);
      await load();
    } catch {
    }
  };

  const deleteItem = async (id: string) => {
    try {
      await apiDelete(`/api/items/${id}`);
      if (selected?._id === id) setSelected(null);
      setEditing(false);
      await load();
    } catch {
    }
  };

  const rarityLabel = (r: string) => {
    const map: Record<string, string> = { common: t("rarityCommon"), uncommon: t("rarityUncommon"), rare: t("rarityRare"), epic: t("rarityEpic"), legendary: t("rarityLegendary") };
    return map[r] || r;
  };

  const typeLabel = (tp: string) => {
    const map: Record<string, string> = { weapon: t("filterWeapon"), artifact: t("filterArtifact"), consumable: t("filterConsumable"), treasure: t("filterTreasure") };
    return map[tp] || tp;
  };

  const renderForm = () => (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-medium text-muted">名称</label>
          <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div>
          <label className="text-xs font-medium text-muted">稀有度</label>
          <select className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.rarity || "common"} onChange={(e) => setForm({ ...form, rarity: e.target.value })}>
            <option value="common">普通</option>
            <option value="uncommon">精良</option>
            <option value="rare">稀有</option>
            <option value="epic">史诗</option>
            <option value="legendary">传说</option>
          </select>
        </div>
      </div>
      <div>
        <label className="text-xs font-medium text-muted">类型</label>
        <select className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.type || "artifact"} onChange={(e) => setForm({ ...form, type: e.target.value })}>
          <option value="weapon">武器</option>
          <option value="artifact">法宝/神器</option>
          <option value="consumable">消耗品</option>
          <option value="treasure">宝物/材料</option>
          <option value="document">文献/卷轴</option>
          <option value="other">其他</option>
        </select>
      </div>
      <div>
        <label className="text-xs font-medium text-muted">描述</label>
        <textarea className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm resize-y" rows={3} value={form.description || ""} onChange={(e) => setForm({ ...form, description: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">来源</label>
        <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.origin || ""} onChange={(e) => setForm({ ...form, origin: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">主线作用</label>
        <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm" value={form.significance || ""} onChange={(e) => setForm({ ...form, significance: e.target.value })} />
      </div>
      <div className="flex gap-2 pt-2">
        <Button variant="primary" size="sm" onPress={saveItem}>保存</Button>
        <Button variant="ghost" size="sm" onPress={() => { setEditing(false); setSelected(null); }}>取消</Button>
      </div>
    </div>
  );

  if (loading) return <div className="flex items-center justify-center h-64"><p className="text-muted text-sm">加载中...</p></div>;

  return (
    <div className="h-full flex">
      <div className="w-60 border-r border-border overflow-y-auto shrink-0 p-3 space-y-3">
        <Button variant="primary" size="sm" className="w-full" onPress={createNew}>{t("createItem")}</Button>
        <div className="flex flex-wrap gap-1">
          <button className={`text-xs px-2 py-1 rounded-full border ${filterType === "" ? "bg-primary/10 border-primary text-primary" : "border-border text-muted"}`} onClick={() => setFilterType("")}>{t("filterAll")}</button>
          {["weapon", "artifact", "consumable", "treasure"].map((tp) => (
            <button key={tp} className={`text-xs px-2 py-1 rounded-full border ${filterType === tp ? "bg-primary/10 border-primary text-primary" : "border-border text-muted"}`} onClick={() => setFilterType(tp)}>
              {typeLabel(tp)}
            </button>
          ))}
        </div>
        {items.length === 0 ? (
          <p className="text-xs text-muted text-center">{t("noItems")}</p>
        ) : (
          items.map((item) => (
            <button key={item._id} className={`w-full text-left p-2 rounded-lg border text-sm hover:bg-muted/5 transition-colors ${selected?._id === item._id ? "border-primary bg-primary/5" : "border-border"}`} onClick={() => { setSelected(item); setEditing(false); }}>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full shrink-0 ${RARITY_COLORS[item.rarity] || "bg-gray-400"}`} />
                <span className="font-medium text-foreground truncate">{item.name}</span>
              </div>
              <div className="text-xs text-muted flex items-center gap-1 ml-4">
                <span>{rarityLabel(item.rarity)}</span>
                <span>·</span>
                <span>{typeLabel(item.type)}</span>
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
                <Button variant="ghost" size="sm" className="text-red-500" onPress={() => deleteItem(selected._id)}>删除</Button>
              </div>
            </div>
            <div className="flex gap-2">
              <Chip variant="soft">{rarityLabel(selected.rarity)}</Chip>
              <Chip variant="soft">{typeLabel(selected.type)}</Chip>
            </div>
            {selected.description && <Field label="描述" value={selected.description} />}
            {selected.origin && <Field label="来源" value={selected.origin} />}
            {selected.significance && <Field label="主线作用" value={selected.significance} />}
            {selected.limitations && <Field label="使用限制" value={selected.limitations} />}
            {selected.history && <Field label="历史" value={selected.history} />}
            {selected.abilities?.length > 0 && <div><span className="text-xs font-medium text-muted">能力</span><div className="flex flex-wrap gap-1 mt-1">{selected.abilities.map((a, i) => <Chip key={i} variant="soft" size="sm">{a}</Chip>)}</div></div>}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full"><p className="text-muted text-sm">选择左侧物品查看详情</p></div>
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
