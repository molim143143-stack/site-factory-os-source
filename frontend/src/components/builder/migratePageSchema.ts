import { blockRegistry } from "./blockRegistry";
import type { PageBlock, PageSchema, PositionMode, ViewportMode } from "./schema";

export function createBlock(type: string): PageBlock {
  const entry = blockRegistry[type] || blockRegistry.Text;
  const id = `${type.toLowerCase()}_${Date.now()}_${Math.round(Math.random() * 10000)}`;
  const x = 48 + Math.round(Math.random() * 140);
  const y = 48 + Math.round(Math.random() * 180);
  const width = type === "FloatingButton" || type === "WhatsAppButton" || type === "TelegramButton" ? 180 : 720;
  const height = type === "FloatingButton" || type === "WhatsAppButton" || type === "TelegramButton" ? 64 : type === "Hero" ? 360 : 240;
  const mode: PositionMode = entry.defaultLayout.mode === "fixed" ? "fixed" : "absolute";
  const layout: PageBlock["layout"] = { ...entry.defaultLayout, mode, x: entry.defaultLayout.x ?? x, y: entry.defaultLayout.y ?? y, zIndex: entry.defaultLayout.zIndex ?? 2 };
  return {
    id,
    type,
    enabled: true,
    x: layout.x,
    y: layout.y,
    width,
    height,
    scale: 1,
    props: { ...entry.defaultProps },
    style: { width, height, ...entry.defaultStyle, margin: "0" },
    layout,
    action: { ...entry.defaultAction },
    translations: JSON.parse(JSON.stringify(entry.defaultTranslations))
  };
}

export function normalizeBlock(oldBlock: any): PageBlock {
  const migrated = createBlock(oldBlock?.type || "Text");
  const content = oldBlock?.content || {};
  const incomingLayout = { ...migrated.layout, ...(oldBlock?.layout || {}) };
  const visualMode: PositionMode = incomingLayout.mode === "normal" ? "absolute" : incomingLayout.mode;
  const visualLayout: PageBlock["layout"] = {
    ...incomingLayout,
    mode: visualMode,
    x: incomingLayout.x ?? 48,
    y: incomingLayout.y ?? 48,
    zIndex: incomingLayout.zIndex ?? 2
  };
  return {
    ...migrated,
    id: oldBlock?.id || migrated.id,
    enabled: oldBlock?.enabled !== false,
    x: oldBlock?.x ?? visualLayout.x,
    y: oldBlock?.y ?? visualLayout.y,
    width: oldBlock?.width ?? oldBlock?.style?.width ?? migrated.width,
    height: oldBlock?.height ?? oldBlock?.style?.height ?? migrated.height,
    scale: oldBlock?.scale ?? 1,
    props: {
      ...migrated.props,
      ...(oldBlock?.props || {}),
      title: oldBlock?.props?.title || oldBlock?.title || content.title || migrated.props.title,
      subtitle: oldBlock?.props?.subtitle || content.subtitle || migrated.props.subtitle,
      body: oldBlock?.props?.body || oldBlock?.text || content.text || oldBlock?.content || migrated.props.body,
      label: oldBlock?.props?.label || content.label || migrated.props.label
    },
    style: { ...migrated.style, ...(oldBlock?.style || {}), width: oldBlock?.width ?? oldBlock?.style?.width ?? migrated.style.width, height: oldBlock?.height ?? oldBlock?.style?.height ?? migrated.style.height },
    layout: visualLayout,
    action: { ...migrated.action, ...(oldBlock?.action || oldBlock?.props?.action || {}) },
    translations: oldBlock?.translations || migrated.translations,
    responsive: oldBlock?.responsive || {}
  };
}

export function normalizePageSchema(raw: any, siteId: string, viewport: ViewportMode, locale: string): PageSchema {
  const layout = raw?.blocks ? raw : raw?.layout || {};
  const blocks = Array.isArray(layout.blocks) ? layout.blocks.map(normalizeBlock) : [createBlock("Hero")];
  return {
    pageId: raw?.pageId || raw?.page_id || "",
    siteId,
    path: raw?.path || raw?.slug || "home",
    locale,
    viewport,
    templateId: layout.templateId || raw?.templateId || raw?.template_id || "",
    template_type: layout.template_type || raw?.template_type || "",
    mode: layout.mode || raw?.mode || "",
    static_template: layout.static_template || raw?.static_template || undefined,
    blocks,
    translations: layout.translations || {
      en: { title: "DIY Home", subtitle: "Built visually in Site Factory OS" },
      "zh-CN": { title: "DIY 首页", subtitle: "通过 Site Factory OS 可视化搭建" },
      es: { title: "Inicio DIY", subtitle: "Construido visualmente en Site Factory OS" },
      vi: { title: "Trang DIY", subtitle: "Được dựng trực quan trong Site Factory OS" }
    }
  };
}
