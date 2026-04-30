import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { PageBlock, ViewportMode } from "./schema";
import { EditableBlockWrapper } from "./EditableBlockWrapper";
import { useI18n } from "../../i18n";

type Props = {
  blocks: PageBlock[];
  selectedId: string;
  locale: string;
  viewport: ViewportMode;
  zoom: number;
  isEditing: boolean;
  onSelect: (id: string) => void;
  onChange: (block: PageBlock, options?: { record?: boolean; before?: PageBlock }) => void;
  onDelete: (id: string) => void;
  onDuplicate: (block: PageBlock) => void;
};

export function BuilderCanvas({ blocks, selectedId, locale, viewport, zoom, isEditing, onSelect, onChange, onDelete, onDuplicate }: Props) {
  const { t } = useI18n();
  const { setNodeRef, isOver } = useDroppable({ id: "canvas-drop" });
  const normalIds = blocks.filter((block) => block.layout.mode === "normal").map((block) => block.id);
  const canvasWidth = viewport === "mobile" ? 375 : 1200;
  const canvasHeight = Math.max(
    viewport === "mobile" ? 900 : 1200,
    ...blocks.map((block) => {
      const y = Number(block.y ?? block.layout.y ?? 0);
      const height = Number(block.height ?? block.style.height ?? 260);
      return Number.isFinite(y + height) ? y + height + 120 : 0;
    })
  );
  return (
    <div className="builder-root relative overflow-auto rounded-3xl bg-[#07111f] p-5">
      <div className="canvas-wrapper flex justify-center">
      <div className="canvas-scale transition-all" style={{ width: canvasWidth * zoom, minHeight: canvasHeight * zoom }}>
      <div className="origin-top transition-transform" style={{ transform: `scale(${zoom})`, transformOrigin: "top center", width: canvasWidth }}>
        <div
          ref={setNodeRef}
          data-testid="diy-canvas-drop"
          className={`canvas-content relative mx-auto overflow-visible rounded-[28px] border bg-white/95 p-4 shadow-2xl transition ${isOver ? "border-neon shadow-neon" : "border-white/10"}`}
          style={{ width: canvasWidth, minHeight: canvasHeight }}
        >
          <SortableContext items={normalIds} strategy={verticalListSortingStrategy}>
            {blocks.length ? blocks.map((block) => (
              <EditableBlockWrapper
                key={block.id}
                block={block}
                selected={selectedId === block.id}
                locale={locale}
                zoom={zoom}
                isEditing={isEditing}
                onSelect={() => onSelect(block.id)}
                onDelete={() => onDelete(block.id)}
                onDuplicate={() => onDuplicate(block)}
                onChange={onChange}
              />
            )) : <div className="flex min-h-[420px] items-center justify-center rounded-3xl border border-dashed border-slate-300 text-slate-500">{t("builder.empty_hint")}</div>}
          </SortableContext>
        </div>
      </div>
      </div>
      </div>
    </div>
  );
}
