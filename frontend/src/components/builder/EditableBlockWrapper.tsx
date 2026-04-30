import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { CSSProperties, PointerEvent as ReactPointerEvent } from "react";
import type { PageBlock } from "./schema";
import { BlockRenderer } from "./BlockRenderer";

type Props = {
  block: PageBlock;
  selected: boolean;
  locale: string;
  zoom: number;
  isEditing: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onDuplicate: () => void;
  onChange: (block: PageBlock, options?: { record?: boolean; before?: PageBlock }) => void;
};

function isInteractiveTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false;
  return Boolean(target.closest("button,a,input,textarea,select,[contenteditable='true'],[data-builder-control='true']"));
}

export function EditableBlockWrapper({ block, selected, locale, zoom, isEditing, onSelect, onChange }: Props) {
  const sortable = useSortable({ id: block.id, disabled: block.layout.mode !== "normal" });
  const numericWidth = typeof block.style.width === "number" ? block.style.width : Number.parseFloat(String(block.style.width || block.width || 640)) || 640;
  const numericHeight = typeof block.style.height === "number" ? block.style.height : Number.parseFloat(String(block.style.height || block.height || 260)) || 260;
  const blockScale = Number((block.scale ?? Math.max(0.55, Math.min(2, Math.min(numericWidth / 720, numericHeight / 260)))).toFixed(3));
  const normalTransform = block.layout.mode === "normal" ? CSS.Transform.toString(sortable.transform) : undefined;
  const freeStyle = block.layout.mode === "absolute" || block.layout.mode === "fixed"
    ? { position: "absolute", left: block.layout.x || 0, top: block.layout.y || 0, zIndex: block.layout.zIndex || 2 }
    : block.layout.mode === "sticky"
      ? { position: "sticky", top: block.layout.y || 0, zIndex: block.layout.zIndex || 2 }
      : {};

  const startMove = (event: ReactPointerEvent) => {
    if (!isEditing) return;
    if (block.layout.mode === "normal") return;
    if (event.button !== 0) return;
    if (isInteractiveTarget(event.target) && !selected) return;
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture?.(event.pointerId);
    onSelect();
    const startX = event.clientX;
    const startY = event.clientY;
    const originX = block.layout.x || 0;
    const originY = block.layout.y || 0;
    let latest = block;
    const move = (pointer: PointerEvent) => {
      const nextX = originX + (pointer.clientX - startX) / zoom;
      const nextY = originY + (pointer.clientY - startY) / zoom;
      latest = { ...block, x: nextX, y: nextY, layout: { ...block.layout, x: nextX, y: nextY } };
      onChange(latest, { record: false });
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      onChange(latest, { record: true, before: block });
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  const startResize = (event: ReactPointerEvent, direction: string) => {
    event.preventDefault();
    event.stopPropagation();
    const startX = event.clientX;
    const startY = event.clientY;
    const originW = numericWidth;
    const originH = numericHeight;
    const originX = block.layout.x || 0;
    const originY = block.layout.y || 0;
    let latest = block;
    const move = (pointer: PointerEvent) => {
      const dx = (pointer.clientX - startX) / zoom;
      const dy = (pointer.clientY - startY) / zoom;
      const left = direction.includes("w");
      const right = direction.includes("e");
      const top = direction.includes("n");
      const bottom = direction.includes("s");
      const nextWidth = Math.max(180, originW + (right ? dx : 0) - (left ? dx : 0));
      const nextHeight = Math.max(90, originH + (bottom ? dy : 0) - (top ? dy : 0));
      const nextX = left && block.layout.mode !== "normal" ? originX + dx : block.layout.x;
      const nextY = top && block.layout.mode !== "normal" ? originY + dy : block.layout.y;
      const nextScale = Number(Math.max(0.55, Math.min(2.2, Math.min(nextWidth / 720, nextHeight / 260))).toFixed(3));
      const next = {
        ...block,
        x: nextX,
        y: nextY,
        width: nextWidth,
        height: nextHeight,
        scale: nextScale,
        style: { ...block.style, width: nextWidth, height: nextHeight },
        layout: {
          ...block.layout,
          x: nextX,
          y: nextY
        }
      };
      onChange(next, { record: false });
      latest = next;
    };
    const up = () => {
      window.removeEventListener("pointermove", move);
      window.removeEventListener("pointerup", up);
      onChange(latest, { record: true, before: block });
    };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", up);
  };

  if (!block.enabled) return null;

  return (
    <div
      ref={sortable.setNodeRef}
      style={{
        transform: normalTransform,
        transition: sortable.transition,
        width: numericWidth,
        height: numericHeight,
        margin: block.style.margin,
        padding: block.style.padding,
        background: block.style.background,
        color: block.style.color,
        borderRadius: block.style.borderRadius,
        fontSize: block.style.fontSize,
        overflow: "visible",
        ["--builder-block-w" as any]: `${numericWidth}px`,
        ["--builder-block-h" as any]: `${numericHeight}px`,
        ["--builder-block-scale" as any]: String(blockScale),
        ...freeStyle
      } as CSSProperties}
      className={`group ${block.layout.mode === "normal" ? "relative mb-4" : ""} ${selected ? "ring-2 ring-neon ring-offset-2 ring-offset-[#0A0F1C]" : "hover:ring-1 hover:ring-neon/35"}`}
      data-testid={`canvas-block-${block.type}`}
      data-block-id={block.id}
      data-selected={selected ? "true" : "false"}
      onPointerDown={startMove}
      onClickCapture={(event) => {
        const target = event.target as HTMLElement | null;
        const actionable = target?.closest("a,button[data-href],[data-href]");
        if (actionable && isEditing) {
          event.preventDefault();
          event.stopPropagation();
          onSelect();
        }
      }}
      onClick={(event) => {
        event.stopPropagation();
        onSelect();
      }}
    >
      <div className="h-full w-full overflow-hidden" style={{ borderRadius: block.style.borderRadius }}>
        <BlockRenderer block={block} locale={locale} />
      </div>
      {selected && (
        <>
          {[
            ["nw", "-left-2 -top-2 cursor-nwse-resize"],
            ["n", "left-1/2 -top-2 -translate-x-1/2 cursor-ns-resize"],
            ["ne", "-right-2 -top-2 cursor-nesw-resize"],
            ["e", "-right-2 top-1/2 -translate-y-1/2 cursor-ew-resize"],
            ["se", "-bottom-2 -right-2 cursor-nwse-resize"],
            ["s", "left-1/2 -bottom-2 -translate-x-1/2 cursor-ns-resize"],
            ["sw", "-bottom-2 -left-2 cursor-nesw-resize"],
            ["w", "-left-2 top-1/2 -translate-y-1/2 cursor-ew-resize"]
          ].map(([dir, cls]) => (
            <button key={dir} data-builder-control="true" className={`absolute z-30 h-4 w-4 rounded-full border border-void bg-neon shadow-neon ${cls}`} onPointerDown={(event) => startResize(event, dir)} aria-label={`Resize ${dir}`} />
          ))}
        </>
      )}
    </div>
  );
}
