import { closestCenter, DndContext, type DragEndEvent, DragOverlay, type DragStartEvent, PointerSensor, useDraggable, useSensor, useSensors } from "@dnd-kit/core";
import { arrayMove } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { ArrowLeft, BadgeDollarSign, Bell, Box, ChevronDown, ChevronRight, CreditCard, Focus, Grid3X3, Image as ImageIcon, LayoutTemplate, Maximize, MessageCircle, Minus, Monitor, MousePointerClick, Navigation, Newspaper, PanelBottom, Plus, RotateCcw, Save, Search, Send, ShieldCheck, ShoppingBag, Smartphone, Sparkles, Star, Timer, TicketPercent, Type, UploadCloud, Video, X, type LucideIcon } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { api, errorText } from "../api/client";
import { useApiData } from "../api/useApiData";
import { fallbackTemplates } from "../data/templateLibrary";
import { blockRegistry, componentTypes } from "../components/builder/blockRegistry";
import { BuilderCanvas } from "../components/builder/Canvas";
import { InspectorPanel } from "../components/builder/InspectorPanel";
import { createBlock, normalizePageSchema } from "../components/builder/migratePageSchema";
import type { PageBlock, PageSchema, ViewportMode } from "../components/builder/schema";
import { blockKey } from "../components/builder/schema";
import { GlassCard } from "../components/GlassCard";
import { NeonButton } from "../components/NeonButton";
import { PortalModal } from "../components/floating/PortalMenu";
import { useI18n } from "../i18n";

type Props = { siteId: string; onToast: (message: string) => void; focusMode?: boolean; onFocusModeChange?: (value: boolean) => void };

const CATEGORY_ORDER = ["common", "basic", "marketing", "commerce", "content", "conversion", "navigation", "footer", "media", "trust"];

function isTextEditingTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false;
  return Boolean(target.closest("input,textarea,select,[contenteditable='true']"));
}

const iconMap: Record<string, LucideIcon> = {
  LayoutTemplate,
  Type,
  Image: ImageIcon,
  MousePointerClick,
  ShoppingBag,
  Newspaper,
  MessageCircle,
  Send,
  Timer,
  TicketPercent,
  ShieldCheck,
  Navigation,
  PanelBottom,
  Video,
  Grid3X3,
  Box,
  Sparkles,
  BadgeDollarSign,
  Bell,
  CreditCard,
  Star
};

function PaletteItem({ type }: { type: string }) {
  const { t } = useI18n();
  const entry = blockRegistry[type];
  const Icon = iconMap[entry.icon] || Sparkles;
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({ id: `palette:${type}`, data: { from: "palette", type } });
  return (
    <button
      ref={setNodeRef}
      style={{ transform: CSS.Translate.toString(transform), opacity: isDragging ? 0.45 : 1 }}
      {...listeners}
      {...attributes}
      data-testid={`block-library-${type}`}
      className="group w-full touch-none rounded-xl border border-white/10 bg-white/[0.04] p-3 text-left transition hover:border-neon/45 hover:bg-neon/10 hover:shadow-neon"
    >
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-neon/25 bg-[#07111f] text-neon transition group-hover:scale-105">
          <Icon size={18} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-black text-textMain">{t(entry.labelKey)}</span>
          <span className="mt-1 block line-clamp-2 text-xs leading-5 text-textWeak">{t(entry.descriptionKey)}</span>
          <span className="mt-2 flex flex-wrap items-center gap-2">
            <span className="rounded-full border border-purple/25 bg-purple/10 px-2 py-0.5 text-[10px] font-bold text-purple">{t(`builder.categories.${entry.category}`)}</span>
            <span className="text-[10px] font-bold text-neon/80">{t("builder.drag_hint")}</span>
          </span>
        </span>
      </div>
    </button>
  );
}

export function DIYBuilder({ siteId, onToast, focusMode = false, onFocusModeChange }: Props) {
  const { t, language } = useI18n();
  const [viewport, setViewport] = useState<ViewportMode>("desktop");
  const [locale, setLocale] = useState<string>(language);
  const [zoom, setZoom] = useState(1);
  const [interactionMode, setInteractionMode] = useState<"edit" | "preview">("edit");
  const [slug, setSlug] = useState("home");
  const [pageId, setPageId] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [activeType, setActiveType] = useState<string | null>(null);
  const [busy, setBusy] = useState("");
  const [componentQuery, setComponentQuery] = useState("");
  const [templateModal, setTemplateModal] = useState(false);
  const [pendingTemplate, setPendingTemplate] = useState<any | null>(null);
  const [collapsedCategories, setCollapsedCategories] = useState<Record<string, boolean>>({});
  const [schema, setSchema] = useState<PageSchema>(() => normalizePageSchema({}, siteId, "desktop", "en"));
  const [history, setHistory] = useState<PageBlock[][]>([]);
  const [future, setFuture] = useState<PageBlock[][]>([]);
  const clipboardRef = useRef<PageBlock | null>(null);
  const products = useApiData(() => api.products(siteId), { items: [] }, [siteId]);
  const articles = useApiData(() => api.articles(siteId), { items: [] }, [siteId]);
  const pages = useApiData(() => api.pages(siteId), { items: [] }, [siteId]);
  const templates = useApiData(api.templateLibrary, { items: [] }, []);
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));
  const blocks = schema.blocks;
  const selected = blocks.find((block) => block.id === selectedId);
  const blockIds = useMemo(() => blocks.map((item) => item.id), [blocks]);
  const categorizedComponents = useMemo(() => {
    const query = componentQuery.trim().toLowerCase();
    const matches = componentTypes.filter((type) => {
      const entry = blockRegistry[type];
      const haystack = [type, entry.category, t(entry.labelKey), t(entry.descriptionKey)].join(" ").toLowerCase();
      return !query || haystack.includes(query);
    });
    return CATEGORY_ORDER.map((category) => ({
      category,
      items: matches.filter((type) => blockRegistry[type].category === category)
    })).filter((group) => group.items.length > 0);
  }, [componentQuery, t]);
  const availableTemplates = useMemo(() => {
    const apiItems = Array.isArray(templates.data.items) ? templates.data.items : [];
    const source = apiItems.length ? apiItems : fallbackTemplates;
    return source.filter((template: any) => template.status === "available" && template.can_use_in_builder !== false && template.page_schema?.blocks?.length);
  }, [templates.data.items]);

  useEffect(() => {
    const row = pages.data.items.find((item: any) => ["home", "/", "", "index"].includes(item.slug)) || pages.data.items[0];
    if (!row || pageId) return;
    let parsed: any = {};
    try {
      parsed = JSON.parse(row.layout_json || "{}");
    } catch {
      parsed = {};
    }
    const next = normalizePageSchema({ ...parsed, page_id: row.page_id, slug: row.slug }, siteId, viewport, locale);
    setSchema(next);
    setSlug(row.slug || "home");
    setPageId(row.page_id || "");
    setSelectedId(next.blocks[0]?.id || "");
  }, [pages.data.items, pageId, siteId, viewport, locale]);

  useEffect(() => {
    setSchema((current) => ({ ...current, viewport, locale }));
  }, [viewport, locale]);

  useEffect(() => {
    if (!focusMode) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !selectedId && !isTextEditingTarget(event.target)) onFocusModeChange?.(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [focusMode, onFocusModeChange, selectedId]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (isTextEditingTarget(event.target)) return;
      const key = event.key.toLowerCase();
      const step = event.shiftKey ? 10 : 1;
      if ((event.ctrlKey || event.metaKey) && key === "c") {
        if (selected) clipboardRef.current = JSON.parse(JSON.stringify(selected));
        event.preventDefault();
        return;
      }
      if ((event.ctrlKey || event.metaKey) && key === "v") {
        pasteBlock();
        event.preventDefault();
        return;
      }
      if ((event.ctrlKey || event.metaKey) && key === "d") {
        if (selected) duplicateBlock(selected);
        event.preventDefault();
        return;
      }
      if ((event.ctrlKey || event.metaKey) && key === "z") {
        undo();
        event.preventDefault();
        return;
      }
      if ((event.ctrlKey || event.metaKey) && key === "y") {
        redo();
        event.preventDefault();
        return;
      }
      if (event.key === "Delete" || event.key === "Backspace") {
        if (selectedId) deleteBlock(selectedId);
        event.preventDefault();
        return;
      }
      if (event.key === "Escape") {
        setSelectedId("");
        event.preventDefault();
        return;
      }
      if (event.key === "ArrowLeft") {
        moveSelected(-step, 0);
        event.preventDefault();
      } else if (event.key === "ArrowRight") {
        moveSelected(step, 0);
        event.preventDefault();
      } else if (event.key === "ArrowUp") {
        moveSelected(0, -step);
        event.preventDefault();
      } else if (event.key === "ArrowDown") {
        moveSelected(0, step);
        event.preventDefault();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [blocks, selected, selectedId]);

  const commitBlocks = (nextBlocks: PageBlock[], options: { record?: boolean; beforeBlocks?: PageBlock[] } = {}) => {
    const shouldRecord = options.record !== false;
    setSchema((current) => {
      if (shouldRecord) {
        setHistory((items) => [...items.slice(-49), options.beforeBlocks || current.blocks]);
        setFuture([]);
      }
      return { ...current, blocks: nextBlocks };
    });
  };
  const updateBlocks = (nextBlocks: PageBlock[]) => commitBlocks(nextBlocks);
  const updateBlock = (next: PageBlock, options: { record?: boolean; before?: PageBlock } = {}) => {
    const shouldRecord = options.record !== false;
    setSchema((current) => {
      const beforeBlocks = options.before
        ? current.blocks.map((block) => block.id === options.before?.id ? options.before : block)
        : current.blocks;
      if (shouldRecord) {
        setHistory((items) => [...items.slice(-49), beforeBlocks]);
        setFuture([]);
      }
      return { ...current, blocks: current.blocks.map((block) => block.id === next.id ? next : block) };
    });
  };
  const deleteBlock = (id: string) => {
    const next = blocks.filter((block) => block.id !== id);
    updateBlocks(next);
    if (selectedId === id) setSelectedId("");
  };
  const cloneBlock = (block: PageBlock, offset = 24): PageBlock => ({
    ...block,
    id: `${block.type.toLowerCase()}_${Date.now()}_${Math.round(Math.random() * 10000)}`,
    x: (block.x ?? block.layout.x ?? 0) + offset,
    y: (block.y ?? block.layout.y ?? 0) + offset,
    width: block.width,
    height: block.height,
    scale: block.scale,
    translations: JSON.parse(JSON.stringify(block.translations)),
    props: { ...block.props },
    style: { ...block.style },
    layout: { ...block.layout, x: (block.layout.x ?? block.x ?? 0) + offset, y: (block.layout.y ?? block.y ?? 0) + offset },
    action: { ...block.action }
  });
  const duplicateBlock = (block: PageBlock) => {
    const clone = cloneBlock(block);
    const index = blocks.findIndex((item) => item.id === block.id);
    const next = [...blocks.slice(0, index + 1), clone, ...blocks.slice(index + 1)];
    updateBlocks(next);
    setSelectedId(clone.id);
  };
  const pasteBlock = () => {
    if (!clipboardRef.current) return;
    const clone = cloneBlock(clipboardRef.current, 32);
    updateBlocks([...blocks, clone]);
    setSelectedId(clone.id);
  };
  const moveSelected = (dx: number, dy: number) => {
    if (!selected) return;
    updateBlock({
      ...selected,
      x: (selected.x ?? selected.layout.x ?? 0) + dx,
      y: (selected.y ?? selected.layout.y ?? 0) + dy,
      layout: { ...selected.layout, mode: selected.layout.mode === "normal" ? "absolute" : selected.layout.mode, x: (selected.layout.x ?? selected.x ?? 0) + dx, y: (selected.layout.y ?? selected.y ?? 0) + dy }
    });
  };
  const undo = () => {
    setHistory((items) => {
      const previous = items[items.length - 1];
      if (!previous) return items;
      setFuture((redoItems) => [blocks, ...redoItems.slice(0, 49)]);
      setSchema((current) => ({ ...current, blocks: previous }));
      setSelectedId("");
      return items.slice(0, -1);
    });
  };
  const redo = () => {
    setFuture((items) => {
      const next = items[0];
      if (!next) return items;
      setHistory((undoItems) => [...undoItems.slice(-49), blocks]);
      setSchema((current) => ({ ...current, blocks: next }));
      setSelectedId("");
      return items.slice(1);
    });
  };
  const addPaletteBlockAt = (type: string, clientX: number, clientY: number) => {
    const canvas = document.querySelector('[data-testid="diy-canvas-drop"]') as HTMLElement | null;
    const canvasBox = canvas?.getBoundingClientRect();
    const block = createBlock(type);
    if (canvasBox) {
      block.layout = {
        ...block.layout,
        mode: block.layout.mode === "fixed" ? "fixed" : "absolute",
        x: Math.max(0, Math.round((clientX - canvasBox.left) / zoom - 120)),
        y: Math.max(0, Math.round((clientY - canvasBox.top) / zoom - 80))
      };
      block.x = block.layout.x;
      block.y = block.layout.y;
    }
    updateBlocks([...blocks, block]);
    setSelectedId(block.id);
  };
  const offsetTemplateBlocks = (templateBlocks: PageBlock[], currentBlocks: PageBlock[]) => {
    const maxBottom = Math.max(
      0,
      ...currentBlocks.map((block) => Number(block.y ?? block.layout.y ?? 0) + Number(block.height ?? block.style.height ?? 260))
    );
    return templateBlocks.map((block) => {
      if (block.layout.mode === "fixed") return block;
      const y = Number(block.y ?? block.layout.y ?? 0) + maxBottom + 80;
      return { ...block, y, layout: { ...block.layout, y } };
    });
  };
  const applyTemplate = (template: any, mode: "replace" | "append" = "replace") => {
    const next = normalizePageSchema(template.page_schema || { blocks: template.blocks || [] }, siteId, viewport, locale);
    setSchema((current) => {
      setHistory((items) => [...items.slice(-49), current.blocks]);
      setFuture([]);
      const templateBlocks = mode === "append" ? offsetTemplateBlocks(next.blocks, current.blocks) : next.blocks;
      setSelectedId(templateBlocks[0]?.id || "");
      return {
        ...current,
        templateId: mode === "replace" ? next.templateId : current.templateId,
        template_type: mode === "replace" ? next.template_type : current.template_type,
        mode: mode === "replace" ? next.mode : current.mode,
        static_template: mode === "replace" ? next.static_template : current.static_template,
        translations: mode === "replace" ? next.translations : current.translations,
        blocks: mode === "append" ? [...current.blocks, ...templateBlocks] : templateBlocks
      };
    });
    setZoom(viewport === "mobile" ? 1 : 0.5);
    setTemplateModal(false);
    setPendingTemplate(null);
    onToast(`TEMPLATE_APPLIED ${mode.toUpperCase()} ${template.id || template.name}`);
  };
  const requestApplyTemplate = (template: any) => {
    if (blocks.length > 0) {
      setTemplateModal(false);
      setPendingTemplate(template);
      return;
    }
    applyTemplate(template, "replace");
  };
  const onDragStart = (event: DragStartEvent) => {
    const data = event.active.data.current;
    setActiveType(data?.type || blocks.find((item) => item.id === event.active.id)?.type || null);
  };
  const onDragEnd = (event: DragEndEvent) => {
    setActiveType(null);
    const { active, over } = event;
    const data = active.data.current;
    if (data?.from === "palette") {
      const canvas = document.querySelector('[data-testid="diy-canvas-drop"]') as HTMLElement | null;
      const canvasBox = canvas?.getBoundingClientRect();
      const translated = active.rect.current.translated;
      const initial = active.rect.current.initial;
      const delta = event.delta || { x: 0, y: 0 };
      const centerX = translated ? translated.left + translated.width / 2 : initial ? initial.left + initial.width / 2 + delta.x : 0;
      const centerY = translated ? translated.top + translated.height / 2 : initial ? initial.top + initial.height / 2 + delta.y : 0;
      const isInsideCanvas = Boolean(canvasBox && centerX >= canvasBox.left && centerX <= canvasBox.right && centerY >= canvasBox.top && centerY <= canvasBox.bottom);
      if (!isInsideCanvas && over?.id !== "canvas-drop") return;
      addPaletteBlockAt(data.type, centerX, centerY);
      return;
    }
    if (!over) return;
    if (active.id !== over.id && blockIds.includes(String(active.id)) && blockIds.includes(String(over.id))) {
      updateBlocks(arrayMove(blocks, blocks.findIndex((item) => item.id === active.id), blocks.findIndex((item) => item.id === over.id)));
    }
  };

  const layout = {
    schemaVersion: 2,
    pageId,
    siteId,
    path: slug,
    locale,
    viewport,
    templateId: schema.templateId,
    template_type: schema.template_type,
    mode: schema.mode,
    static_template: schema.static_template,
    translations: schema.translations,
    blocks
  };

  const save = async () => {
    setBusy("save");
    try {
      const payload = { request_id: `web_page_save_${Date.now()}`, slug, page_type: "custom", layout };
      const response = pageId ? await api.updatePage(pageId, payload) : await api.createPage(siteId, payload);
      setPageId(response.page.page_id);
      onToast("DIY_SAVE OK");
    } catch (error) {
      onToast(errorText(error));
    } finally {
      setBusy("");
    }
  };
  const publish = async () => {
    setBusy("publish");
    try {
      const saved = pageId ? await api.updatePage(pageId, { request_id: `web_page_save_${Date.now()}`, slug, page_type: "custom", layout }) : await api.createPage(siteId, { request_id: `web_page_save_${Date.now()}`, slug, page_type: "custom", layout });
      const id = pageId || saved.page.page_id;
      setPageId(id);
      await api.publishPage(id, { request_id: `web_page_publish_${Date.now()}` });
      onToast("DIY_PUBLISH OK");
    } catch (error) {
      onToast(errorText(error));
    } finally {
      setBusy("");
    }
  };
  const rollback = async () => {
    if (!pageId) return onToast("errors.DEPLOY_PAGE_NOT_READY");
    setBusy("rollback");
    try {
      await api.rollbackPage(pageId, { request_id: `web_page_rollback_${Date.now()}` });
      onToast("builder.rollback");
    } catch (error) {
      onToast(errorText(error));
    } finally {
      setBusy("");
    }
  };

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragStart={onDragStart} onDragEnd={onDragEnd}>
      <div className="space-y-4">
        {focusMode && (
          <GlassCard className="p-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <NeonButton tone="ghost" onClick={() => onFocusModeChange?.(false)} data-testid="builder-focus-back"><ArrowLeft size={16} />{t("builder.back")}</NeonButton>
              <div className="font-black text-textMain">{t("builder.title")}</div>
              <NeonButton tone="danger" onClick={() => onFocusModeChange?.(false)} data-testid="builder-focus-close"><X size={16} />{t("builder.exit_focus")}</NeonButton>
            </div>
          </GlassCard>
        )}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="page-kicker">{t("builder.kicker")}</p>
            <h1 className="page-title">{t("builder.title")}</h1>
          </div>
          <div className="flex flex-wrap gap-2">
            <input className="form-input max-w-40" data-testid="diy-slug" value={slug} onChange={(event) => setSlug(event.target.value)} placeholder={t("builder.page_slug")} />
            <select className="form-select" value={locale} onChange={(event) => setLocale(event.target.value)} aria-label={t("builder.locale")}><option>en</option><option>zh-CN</option><option>es</option><option>vi</option></select>
            <NeonButton tone={viewport === "mobile" ? "primary" : "ghost"} onClick={() => setViewport("mobile")}><Smartphone size={15} />{t("builder.preview_mobile")}</NeonButton>
            <NeonButton tone={viewport === "desktop" ? "primary" : "ghost"} onClick={() => setViewport("desktop")}><Monitor size={15} />{t("builder.preview_pc")}</NeonButton>
            <NeonButton onClick={save} disabled={busy === "save"} data-testid="diy-save-button"><Save size={15} />{busy === "save" ? t("common.loading") : t("builder.save")}</NeonButton>
            <NeonButton tone="success" onClick={publish} disabled={busy === "publish"} data-testid="diy-publish-button"><UploadCloud size={15} />{busy === "publish" ? t("common.loading") : t("builder.publish")}</NeonButton>
            <NeonButton tone="warning" onClick={rollback} disabled={busy === "rollback"}><RotateCcw size={15} />{busy === "rollback" ? t("common.loading") : t("builder.rollback")}</NeonButton>
          </div>
        </div>
        <GlassCard className="p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap gap-2">
              <NeonButton tone="ghost" onClick={() => setZoom((value) => Math.max(0.5, Number((value - 0.25).toFixed(2))))}><Minus size={15} /></NeonButton>
              {[0.5, 1, 1.25, 1.5].map((value) => <NeonButton key={value} tone={zoom === value ? "primary" : "ghost"} onClick={() => setZoom(value)}>{Math.round(value * 100)}%</NeonButton>)}
              <NeonButton tone="ghost" onClick={() => setZoom((value) => Math.min(1.5, Number((value + 0.25).toFixed(2))))}><Plus size={15} /></NeonButton>
              <NeonButton tone="purple" onClick={() => setZoom(viewport === "mobile" ? 1 : 0.75)}><Maximize size={15} />{t("builder.fit")}</NeonButton>
            </div>
            <NeonButton tone={focusMode ? "danger" : "success"} onClick={() => onFocusModeChange?.(!focusMode)}>
              {focusMode ? <X size={15} /> : <Focus size={15} />}
              {focusMode ? t("builder.exit_focus") : t("builder.focus_mode")}
            </NeonButton>
            <NeonButton tone={interactionMode === "preview" ? "success" : "ghost"} onClick={() => setInteractionMode((value) => value === "edit" ? "preview" : "edit")} data-testid="diy-interaction-mode">
              {interactionMode === "edit" ? t("builder.edit_mode") : t("builder.preview_mode")}
            </NeonButton>
          </div>
        </GlassCard>
        <div className={`grid gap-4 ${focusMode ? "min-h-[calc(100vh-170px)] xl:grid-cols-[280px_1fr_380px]" : "min-h-[740px] xl:grid-cols-[250px_1fr_360px]"}`}>
          <GlassCard className="p-4">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="font-bold text-textMain">{t("builder.components")}</h2>
              <span className="rounded-full border border-neon/20 px-2 py-1 text-[10px] font-bold text-neon">{componentTypes.length}</span>
            </div>
            <NeonButton className="mb-3 w-full justify-center" tone="purple" data-testid="choose-template-button" onClick={() => setTemplateModal(true)}>
              <LayoutTemplate size={15} />{t("builder.choose_template")}
            </NeonButton>
            <label className="mb-3 flex items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-textWeak focus-within:border-neon/40">
              <Search size={15} className="text-neon" />
              <input
                className="w-full bg-transparent text-sm text-textMain outline-none placeholder:text-textWeak"
                value={componentQuery}
                onChange={(event) => setComponentQuery(event.target.value)}
                placeholder={t("builder.search_components")}
                aria-label={t("builder.search_components")}
              />
            </label>
            <div className="max-h-[650px] space-y-3 overflow-auto pr-1">
              {categorizedComponents.map((group) => {
                const collapsed = collapsedCategories[group.category];
                return (
                  <section key={group.category} className="rounded-xl border border-white/10 bg-black/10 p-2">
                    <button
                      type="button"
                      className="flex w-full items-center justify-between rounded-lg px-2 py-2 text-left text-xs font-black uppercase tracking-[0.18em] text-textWeak hover:bg-white/5 hover:text-textMain"
                      onClick={() => setCollapsedCategories((current) => ({ ...current, [group.category]: !current[group.category] }))}
                    >
                      <span>{t(`builder.categories.${group.category}`)} · {group.items.length}</span>
                      {collapsed ? <ChevronRight size={15} /> : <ChevronDown size={15} />}
                    </button>
                    {!collapsed && (
                      <div className="mt-2 space-y-2">
                        {group.items.map((type) => <PaletteItem key={type} type={type} />)}
                      </div>
                    )}
                  </section>
                );
              })}
              {categorizedComponents.length === 0 && <div className="rounded-xl border border-white/10 bg-white/5 p-4 text-sm text-textWeak">{t("builder.no_components")}</div>}
            </div>
          </GlassCard>
          <GlassCard className="p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-bold text-textMain">{t("builder.canvas")}</h2>
              <span className="rounded-full border border-neon/20 px-3 py-1 text-xs text-neon">{t(language)} · {viewport}</span>
            </div>
            <BuilderCanvas blocks={blocks} selectedId={selectedId} locale={locale} viewport={viewport} zoom={zoom} isEditing={interactionMode === "edit"} onSelect={setSelectedId} onChange={updateBlock} onDelete={deleteBlock} onDuplicate={duplicateBlock} />
          </GlassCard>
          <GlassCard className="p-4">
            <h2 className="mb-4 font-bold text-textMain">{t("builder.properties")}</h2>
            <InspectorPanel block={selected} locale={locale} products={products.data.items} articles={articles.data.items} onChange={updateBlock} onDelete={() => selected && deleteBlock(selected.id)} onDuplicate={() => selected && duplicateBlock(selected)} />
          </GlassCard>
        </div>
      </div>
      <PortalModal open={templateModal} onClose={() => setTemplateModal(false)}>
        <h2 className="text-xl font-black text-textMain">{t("builder.template_library")}</h2>
        <div className="mt-4 max-h-[60vh] space-y-3 overflow-auto">
          {availableTemplates.map((template: any) => (
            <div key={template.id || template.name} className="rounded-2xl border border-white/10 bg-white/5 p-3">
              {template.preview_image_url && (
                <img
                  src={`${(import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000/api/v1").replace(/\/api\/v1$/, "")}${template.preview_image_url}`}
                  alt={template.name}
                  className="mb-3 h-36 w-full rounded-xl border border-white/10 object-cover"
                  data-testid={`template-preview-${template.id}`}
                />
              )}
              <p className="font-black text-textMain">{template.name}</p>
              <p className="mt-1 text-xs text-textWeak">{template.category} · {template.template_type || "static_template"} · {template.status}</p>
              <p className="mt-1 text-xs text-textWeak">{template.repo_name || template.repo_url}</p>
              <p className="mt-1 text-xs text-textWeak">★ {template.stars ?? 0} · {template.license || "license"} · {template.framework}</p>
              <NeonButton className="mt-3" data-testid={`apply-template-${template.id}`} onClick={() => requestApplyTemplate(template)}>{t("builder.apply_template")}</NeonButton>
            </div>
          ))}
          {availableTemplates.length === 0 && <p className="text-sm text-textWeak">{templates.loading ? t("common.loading") : t("builder.no_components")}</p>}
        </div>
      </PortalModal>
      <PortalModal open={Boolean(pendingTemplate)} onClose={() => setPendingTemplate(null)}>
        <h2 className="text-xl font-black text-textMain">{t("builder.apply_template_confirm")}</h2>
        <p className="mt-3 text-sm leading-6 text-textWeak">{t("builder.apply_template_warning")}</p>
        <div className="mt-5 rounded-2xl border border-neon/20 bg-neon/5 p-3">
          <p className="font-black text-textMain">{pendingTemplate?.name}</p>
          <p className="mt-1 text-xs text-textWeak">{pendingTemplate?.framework} · {pendingTemplate?.category} · {pendingTemplate?.page_schema?.blocks?.length || 0} {t("builder.template_blocks")}</p>
        </div>
        <div className="mt-5 flex flex-wrap gap-3">
          <NeonButton data-testid="template-overwrite-button" onClick={() => pendingTemplate && applyTemplate(pendingTemplate, "replace")}>
            {t("builder.overwrite_page")}
          </NeonButton>
          <NeonButton tone="purple" data-testid="template-append-button" onClick={() => pendingTemplate && applyTemplate(pendingTemplate, "append")}>
            {t("builder.append_page")}
          </NeonButton>
          <NeonButton tone="ghost" data-testid="template-cancel-button" onClick={() => setPendingTemplate(null)}>
            {t("common.cancel")}
          </NeonButton>
        </div>
      </PortalModal>
      <DragOverlay>{activeType ? <div className="rounded-xl border border-neon bg-[#111827] px-4 py-3 text-neon shadow-neon">{t(blockRegistry[activeType]?.labelKey || `builder.blocks.${blockKey(activeType)}`)}</div> : null}</DragOverlay>
    </DndContext>
  );
}
