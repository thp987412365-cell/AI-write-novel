"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter, usePathname } from "next/navigation";
import { Card, Button } from "@heroui/react";
import AICreateStepper from "./AICreateStepper";
import type { AICreateResponse, WritingDraft } from "@/types/novel";

const DRAFT_KEY = "writing_draft";

interface NewNovelPanelProps {
  onCreated: (novelId: string) => void;
  onCancel: () => void;
}

export default function NewNovelPanel({ onCancel }: NewNovelPanelProps) {
  const t = useTranslations("create");
  const tb = useTranslations("bookshelf");
  const router = useRouter();
  const pathname = usePathname();
  const locale = pathname.startsWith("/en") ? "en" : "zh";
  const [redirecting, setRedirecting] = useState(false);
  const [draftError, setDraftError] = useState<string | null>(null);

  const handleAIComplete = (result: AICreateResponse, chapters: number, wordsPerChapter: number) => {
    try {
      const meta = result.novel_meta;
      const extract = result.extract_idea;
      const seed = result.core_seed;

      if (!meta) throw new Error("Missing novel_meta in response");
      if (!extract) throw new Error("Missing extract_idea in response");
      if (!seed) throw new Error("Missing core_seed in response");

      const plot = result.expand_idea?.plot ?? extract.plot ?? "";
      const draft: WritingDraft = {
        _fromAI: true,
        title: meta.title ?? "",
        subtitle: meta.subtitle ?? "",
        genre: extract.genre ?? "",
        tags: meta.tags ?? [],
        introduction: meta.introduction ?? "",
        summary: meta.summary ?? "",
        core_seed: seed.core_seed ?? "",
        worldview: meta.worldview ?? "",
        writing_style: meta.writing_style ?? "",
        narrative_pov: meta.narrative_pov ?? "",
        era_background: meta.era_background ?? "",
        plot,
        tone: extract.tone ?? "",
        target_audience: extract.target_audience ?? "",
        core_idea: extract.core_idea ?? "",
        number_of_chapters: chapters,
        words_per_chapter: wordsPerChapter,
        characters: result.characters ?? [],
        factions: result.factions ?? [],
        locations: result.locations ?? [],
        items: result.items ?? [],
        rules: result.rules ?? [],
        relationships: result.relationships ?? [],
      };
      sessionStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
      setRedirecting(true);
      router.push(`/${locale}/writing/new`);
    } catch (err) {
      setDraftError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div className="h-full flex flex-col">
      <Card className="h-full flex flex-col overflow-hidden">
        <Card.Header className="shrink-0">
          <div className="flex items-center justify-between w-full">
            <h2 className="text-lg font-bold text-foreground">{t("title")}</h2>
            <Button variant="ghost" size="sm" onPress={onCancel}>
              {t("back")}
            </Button>
          </div>
        </Card.Header>

        <Card.Content className="flex-1 overflow-y-auto">
          {draftError ? (
            <div className="flex flex-col items-center justify-center h-32 gap-3">
              <p className="text-sm text-red-500">{draftError}</p>
              <Button variant="outline" size="sm" onPress={() => setDraftError(null)}>
                {t("retryStep")}
              </Button>
            </div>
          ) : redirecting ? (
            <div className="flex items-center justify-center h-32">
              <p className="text-sm text-muted">{tb("aiCompleteRedirect")}</p>
            </div>
          ) : (
            <AICreateStepper onComplete={handleAIComplete} />
          )}
        </Card.Content>
      </Card>
    </div>
  );
}
