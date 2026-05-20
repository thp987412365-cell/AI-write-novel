"use client";

import { useState, useEffect, useCallback } from "react";
import { useTranslations } from "next-intl";
import { Button, Chip } from "@heroui/react";
import { apiGet, apiPost, apiPut, apiDelete } from "@/lib/api";
import type { Character } from "@/types/novel";

interface CharacterCardsProps {
  novelId: string;
}

const ROLE_FILTERS = ["all", "protagonist", "antagonist", "supporting"] as const;

export default function CharacterCards({ novelId }: CharacterCardsProps) {
  const t = useTranslations("writing.characterCards");
  const [characters, setCharacters] = useState<Character[]>([]);
  const [filterRole, setFilterRole] = useState<string>("all");
  const [selected, setSelected] = useState<Character | null>(null);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<Partial<Character>>({});
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const roleParam = filterRole !== "all" ? `?role=${filterRole}` : "";
      const res = await apiGet<{ data: Character[] }>(`/api/characters/novel/${novelId}${roleParam}`);
      setCharacters(res.data);
    } catch {
    } finally {
      setLoading(false);
    }
  }, [novelId, filterRole]);

  useEffect(() => { load(); }, [load]);

  const createNew = () => {
    setForm({
      name: "",
      role: "supporting",
      gender: "",
      appearance: "",
      personality: "",
      background: "",
      abilities: [],
      goals: "",
      secrets: "",
    });
    setSelected(null);
    setEditing(true);
  };

  const startEdit = (ch: Character) => {
    setForm({ ...ch });
    setSelected(ch);
    setEditing(true);
  };

  const saveCharacter = async () => {
    try {
      if (selected) {
        await apiPut(`/api/characters/${selected._id}`, form);
      } else {
        await apiPost("/api/characters/create", { ...form, novel_id: novelId });
      }
      setEditing(false);
      setSelected(null);
      await load();
    } catch {
    }
  };

  const deleteCharacter = async (id: string) => {
    try {
      await apiDelete(`/api/characters/${id}`);
      if (selected?._id === id) setSelected(null);
      setEditing(false);
      await load();
    } catch {
    }
  };

  const roleLabel = (role: string) => {
    const map: Record<string, string> = { protagonist: t("filterProtagonist"), antagonist: t("filterAntagonist"), supporting: t("filterSupporting") };
    return map[role] || role;
  };

  const renderForm = () => (
    <div className="space-y-3">
      <div>
        <label className="text-xs font-medium text-muted">姓名</label>
        <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm text-foreground" value={form.name || ""} onChange={(e) => setForm({ ...form, name: e.target.value })} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-medium text-muted">身份</label>
          <select className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm text-foreground" value={form.role || "supporting"} onChange={(e) => setForm({ ...form, role: e.target.value })}>
            <option value="protagonist">主角</option>
            <option value="antagonist">反派</option>
            <option value="supporting">配角</option>
            <option value="cameo">客串</option>
          </select>
        </div>
        <div>
          <label className="text-xs font-medium text-muted">性别</label>
          <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm text-foreground" value={form.gender || ""} onChange={(e) => setForm({ ...form, gender: e.target.value })} />
        </div>
      </div>
      <div>
        <label className="text-xs font-medium text-muted">年龄</label>
        <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm text-foreground" value={form.age || ""} onChange={(e) => setForm({ ...form, age: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">外貌</label>
        <textarea className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm text-foreground resize-y" rows={2} value={form.appearance || ""} onChange={(e) => setForm({ ...form, appearance: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">性格</label>
        <textarea className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm text-foreground resize-y" rows={2} value={form.personality || ""} onChange={(e) => setForm({ ...form, personality: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">背景故事</label>
        <textarea className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm text-foreground resize-y" rows={3} value={form.background || ""} onChange={(e) => setForm({ ...form, background: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">目标/动机</label>
        <input className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm text-foreground" value={form.goals || ""} onChange={(e) => setForm({ ...form, goals: e.target.value })} />
      </div>
      <div>
        <label className="text-xs font-medium text-muted">秘密</label>
        <textarea className="w-full rounded border border-border bg-background px-3 py-1.5 text-sm text-foreground resize-y" rows={2} value={form.secrets || ""} onChange={(e) => setForm({ ...form, secrets: e.target.value })} />
      </div>
      <div className="flex gap-2 pt-2">
        <Button variant="primary" size="sm" onPress={saveCharacter}>保存</Button>
        <Button variant="ghost" size="sm" onPress={() => { setEditing(false); setSelected(null); }}>取消</Button>
      </div>
    </div>
  );

  if (loading) return <div className="flex items-center justify-center h-64"><p className="text-muted text-sm">加载中...</p></div>;

  return (
    <div className="h-full flex">
      <div className="w-60 border-r border-border overflow-y-auto shrink-0 p-3 space-y-3">
        <Button variant="primary" size="sm" className="w-full" onPress={createNew}>{t("createCharacter")}</Button>
        <div className="flex flex-wrap gap-1">
          {ROLE_FILTERS.map((rf) => (
            <button key={rf} className={`text-xs px-2 py-1 rounded-full border ${filterRole === rf ? "bg-primary/10 border-primary text-primary" : "border-border text-muted"}`} onClick={() => setFilterRole(rf)}>
              {rf === "all" ? t("filterAll") : roleLabel(rf)}
            </button>
          ))}
        </div>
        {characters.length === 0 ? (
          <p className="text-xs text-muted text-center">{t("noCharacters")}</p>
        ) : (
          characters.map((ch) => (
            <button key={ch._id} className={`w-full text-left p-2 rounded-lg border text-sm hover:bg-muted/5 transition-colors ${selected?._id === ch._id ? "border-primary bg-primary/5" : "border-border"}`} onClick={() => { setSelected(ch); setEditing(false); }}>
              <div className="font-medium text-foreground">{ch.name}</div>
              <div className="text-xs text-muted flex items-center gap-1">
                <Chip size="sm" variant="soft">{roleLabel(ch.role)}</Chip>
                <span>{ch.status === "alive" ? "存活" : ch.status === "dead" ? "已故" : "未知"}</span>
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
                <Button variant="ghost" size="sm" className="text-red-500" onPress={() => deleteCharacter(selected._id)}>删除</Button>
              </div>
            </div>
            <div className="flex gap-2"><Chip variant="soft">{roleLabel(selected.role)}</Chip>{selected.gender && <Chip variant="soft">{selected.gender}</Chip>}{selected.age && <Chip variant="soft">{selected.age}</Chip>}</div>
            {selected.appearance && <Field label="外貌" value={selected.appearance} />}
            {selected.personality && <Field label="性格" value={selected.personality} />}
            {selected.background && <Field label="背景故事" value={selected.background} />}
            {selected.goals && <Field label="目标/动机" value={selected.goals} />}
            {selected.secrets && <Field label="秘密" value={selected.secrets} />}
            {selected.abilities.length > 0 && <div><span className="text-xs font-medium text-muted">能力</span><div className="flex flex-wrap gap-1 mt-1">{selected.abilities.map((a, i) => <Chip key={i} variant="soft" size="sm">{a}</Chip>)}</div></div>}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full"><p className="text-muted text-sm">选择左侧角色查看详情</p></div>
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
