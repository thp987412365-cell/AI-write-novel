"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import type { WritingSidebarItem } from "@/types/novel";
import WritingSidebar from "./WritingSidebar";
import WritingPlaceholder from "./WritingPlaceholder";
import NovelInfoWorkspace from "./novel-info/NovelInfoWorkspace";
import ChapterEditor from "./ChapterEditor";
import CharacterCards from "./CharacterCards";
import LocationCards from "./LocationCards";
import FactionCards from "./FactionCards";
import ItemCards from "./ItemCards";
import RuleCards from "./RuleCards";
import RelationshipMap from "./RelationshipMap";
import PlotOutline from "./PlotOutline";
import NovelKnowledge from "./NovelKnowledge";

interface WritingContentProps {
  mode: "create" | "edit";
  novelId?: string;
}

export default function WritingContent({ mode, novelId }: WritingContentProps) {
  const t = useTranslations("writing");
  const [activeItem, setActiveItem] = useState<WritingSidebarItem>("novel-info");

  const renderMainArea = () => {
    if (activeItem === "novel-info") {
      return <NovelInfoWorkspace mode={mode} novelId={novelId} />;
    }
    if (!novelId) {
      return (
        <WritingPlaceholder
          moduleKey={activeItem}
          message={t("placeholder.noNovelId")}
          hint={t("placeholder.hint")}
        />
      );
    }
    switch (activeItem) {
      case "chapter-editor":
        return <ChapterEditor novelId={novelId} />;
      case "plot-outline":
        return <PlotOutline novelId={novelId} />;
      case "knowledge-base":
        return <NovelKnowledge novelId={novelId} />;
      case "character-cards":
        return <CharacterCards novelId={novelId} />;
      case "location-cards":
        return <LocationCards novelId={novelId} />;
      case "faction-cards":
        return <FactionCards novelId={novelId} />;
      case "item-cards":
        return <ItemCards novelId={novelId} />;
      case "rule-cards":
        return <RuleCards novelId={novelId} />;
      case "relationship-map":
        return <RelationshipMap novelId={novelId} />;
      default:
        return <WritingPlaceholder moduleKey={activeItem} />;
    }
  };

  return (
    <div className="h-[calc(100vh-3.5rem)] flex">
      <WritingSidebar activeItem={activeItem} onSelect={setActiveItem} />
      <div className="flex-1 min-w-0 overflow-hidden flex flex-col">
        {renderMainArea()}
      </div>
    </div>
  );
}
