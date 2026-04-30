import { Copy, Trash2 } from "lucide-react";
import { NeonButton } from "../NeonButton";
import { useI18n } from "../../i18n";
import type { ActionType, PageBlock, PositionMode } from "./schema";

type Props = {
  block?: PageBlock;
  locale: string;
  products: any[];
  articles: any[];
  onChange: (block: PageBlock) => void;
  onDelete: () => void;
  onDuplicate: () => void;
};

const actionTypes: ActionType[] = ["none", "external_url", "product", "article", "popup", "whatsapp", "telegram"];
const modes: PositionMode[] = ["normal", "absolute", "fixed", "sticky"];
const colorSwatches = ["#0A0F1C", "#111827", "#00E5FF", "#7C4DFF", "#00FF95", "#FFB300", "#FF3D71", "#E5F7FF", "#FFFFFF", "#000000"];
const anchorPresets = [
  { key: "top-left", x: 24, y: 24 },
  { key: "top-right", x: 996, y: 24 },
  { key: "bottom-left", x: 24, y: 772 },
  { key: "bottom-right", x: 996, y: 772 }
] as const;

function normalizeHex(value: string) {
  const trimmed = value.trim();
  return /^#[0-9a-fA-F]{6}$/.test(trimmed) ? trimmed : value;
}

function ColorControl({ label, value, testId, onChange }: { label: string; value: string; testId: string; onChange: (value: string) => void }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
      <span className="form-label">{label}</span>
      <div className="mt-2 flex items-center gap-2">
        <input data-testid={`${testId}-picker`} className="h-10 w-12 rounded-lg border border-white/10 bg-transparent p-1" type="color" value={/^#[0-9a-fA-F]{6}$/.test(value) ? value : "#00E5FF"} onChange={(event) => onChange(event.target.value)} />
        <input data-testid={`${testId}-hex`} className="form-input font-mono" value={value} placeholder="#00E5FF" onChange={(event) => onChange(normalizeHex(event.target.value))} />
      </div>
      <div className="mt-2 flex flex-wrap gap-1.5">
        {colorSwatches.map((color) => (
          <button key={color} type="button" data-testid={`${testId}-swatch-${color.replace("#", "")}`} className="h-6 w-6 rounded-md border border-white/15" style={{ backgroundColor: color }} onClick={() => onChange(color)} aria-label={`${label} ${color}`} />
        ))}
      </div>
    </div>
  );
}

export function InspectorPanel({ block, locale, products, articles, onChange, onDelete, onDuplicate }: Props) {
  const { t } = useI18n();
  if (!block) return <p className="text-sm text-textWeak">{t("builder.empty_hint")}</p>;
  const trans = block.translations[locale] || {};
  const update = (patch: Partial<PageBlock>) => onChange({ ...block, ...patch });
  const updateTranslation = (key: string, value: string) => update({ translations: { ...block.translations, [locale]: { ...trans, [key]: value } } });
  const updateStyle = (key: keyof PageBlock["style"], value: string) => {
    const parsed = ["width", "height"].includes(String(key)) ? Number.parseFloat(value) : Number.NaN;
    if (key === "width" && Number.isFinite(parsed)) {
      const height = Number.parseFloat(String(block.style.height || block.height || 260)) || 260;
      update({ width: parsed, scale: Number(Math.max(0.55, Math.min(2.2, Math.min(parsed / 720, height / 260))).toFixed(3)), style: { ...block.style, width: parsed } });
      return;
    }
    if (key === "height" && Number.isFinite(parsed)) {
      const width = Number.parseFloat(String(block.style.width || block.width || 720)) || 720;
      update({ height: parsed, scale: Number(Math.max(0.55, Math.min(2.2, Math.min(width / 720, parsed / 260))).toFixed(3)), style: { ...block.style, height: parsed } });
      return;
    }
    update({ style: { ...block.style, [key]: value } });
  };
  const updateLayout = (key: keyof PageBlock["layout"], value: any) => {
    update({ ...(key === "x" ? { x: value } : key === "y" ? { y: value } : {}), layout: { ...block.layout, [key]: value } });
  };
  const applyAnchor = (anchor: PageBlock["layout"]["anchor"], x: number, y: number) => {
    update({ x, y, layout: { ...block.layout, mode: "fixed", anchor, x, y, zIndex: block.layout.zIndex || 50 } });
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-textWeak">{t("builder.selected")}: <span className="text-neon">{block.type}</span></p>
      <section className="space-y-3">
        <h3 className="font-bold text-textMain">{t("builder.content")}</h3>
        <label className="block"><span className="form-label">{t("builder.title_field")}</span><input className="form-input" data-testid="diy-title-input" value={trans.title || ""} onChange={(event) => updateTranslation("title", event.target.value)} /></label>
        <label className="block"><span className="form-label">{t("builder.subtitle_field")}</span><input className="form-input" value={trans.subtitle || ""} onChange={(event) => updateTranslation("subtitle", event.target.value)} /></label>
        <label className="block"><span className="form-label">{t("builder.body_field")}</span><textarea className="form-input min-h-20" value={trans.body || ""} onChange={(event) => updateTranslation("body", event.target.value)} /></label>
        <label className="block"><span className="form-label">{t("builder.button_label")}</span><input className="form-input" value={trans.label || ""} onChange={(event) => updateTranslation("label", event.target.value)} /></label>
        <label className="block"><span className="form-label">{t("builder.image_url")}</span><input className="form-input" value={block.props.imageUrl || ""} onChange={(event) => update({ props: { ...block.props, imageUrl: event.target.value } })} /></label>
      </section>
      <section className="space-y-3">
        <h3 className="font-bold text-textMain">{t("builder.style")}</h3>
        <div className="grid grid-cols-2 gap-2">
          <div className="col-span-2 grid gap-2 md:grid-cols-2">
            <ColorControl label={t("builder.background")} value={String(block.style.background || "")} testId="diy-color-background" onChange={(value) => updateStyle("background", value)} />
            <ColorControl label={t("builder.text_color")} value={String(block.style.color || "")} testId="diy-color-text" onChange={(value) => updateStyle("color", value)} />
            <ColorControl label={t("builder.button_color")} value={String(block.style.buttonColor || "")} testId="diy-color-button" onChange={(value) => updateStyle("buttonColor", value)} />
            <ColorControl label={t("builder.border_color")} value={String(block.style.borderColor || "")} testId="diy-color-border" onChange={(value) => updateStyle("borderColor", value)} />
          </div>
          <label><span className="form-label">{t("builder.width")}</span><input className="form-input" data-testid="diy-style-width" value={block.style.width || ""} onChange={(event) => updateStyle("width", event.target.value)} /></label>
          <label><span className="form-label">{t("builder.height")}</span><input className="form-input" data-testid="diy-style-height" value={block.style.height || ""} onChange={(event) => updateStyle("height", event.target.value)} /></label>
          <label><span className="form-label">{t("builder.padding")}</span><input className="form-input" value={block.style.padding || ""} onChange={(event) => updateStyle("padding", event.target.value)} /></label>
          <label><span className="form-label">{t("builder.margin")}</span><input className="form-input" value={block.style.margin || ""} onChange={(event) => updateStyle("margin", event.target.value)} /></label>
          <label><span className="form-label">{t("builder.radius")}</span><input className="form-input" value={block.style.borderRadius || ""} onChange={(event) => updateStyle("borderRadius", event.target.value)} /></label>
        </div>
      </section>
      <section className="space-y-3">
        <h3 className="font-bold text-textMain">{t("builder.layout")}</h3>
        <label className="block"><span className="form-label">{t("builder.position_mode")}</span><select className="form-select w-full" value={block.layout.mode} onChange={(event) => updateLayout("mode", event.target.value as PositionMode)}>{modes.map((item) => <option key={item}>{item}</option>)}</select></label>
        <div>
          <span className="form-label">{t("builder.anchor")}</span>
          <div className="mt-2 grid grid-cols-2 gap-2">
            {anchorPresets.map((preset) => (
              <button
                key={preset.key}
                type="button"
                data-testid={`diy-anchor-${preset.key}`}
                className={`rounded-xl border px-3 py-2 text-xs font-bold transition ${block.layout.anchor === preset.key ? "border-neon bg-neon/10 text-neon" : "border-white/10 bg-white/5 text-textWeak hover:border-neon/35 hover:text-textMain"}`}
                onClick={() => applyAnchor(preset.key, preset.x, preset.y)}
              >
                {t(`builder.anchor_${preset.key.replace("-", "_")}`)}
              </button>
            ))}
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2">
          <label><span className="form-label">{t("builder.x")}</span><input className="form-input" data-testid="diy-layout-x" type="number" value={block.layout.x || 0} onChange={(event) => updateLayout("x", Number(event.target.value))} /></label>
          <label><span className="form-label">{t("builder.y")}</span><input className="form-input" data-testid="diy-layout-y" type="number" value={block.layout.y || 0} onChange={(event) => updateLayout("y", Number(event.target.value))} /></label>
          <label><span className="form-label">{t("builder.z_index")}</span><input className="form-input" type="number" value={block.layout.zIndex || 1} onChange={(event) => updateLayout("zIndex", Number(event.target.value))} /></label>
        </div>
      </section>
      <section className="space-y-3">
        <h3 className="font-bold text-textMain">{t("builder.action")}</h3>
        <label className="block"><span className="form-label">{t("builder.action_type")}</span><select className="form-select w-full" data-testid="diy-action-type" value={block.action.type} onChange={(event) => update({ action: { ...block.action, type: event.target.value as ActionType } })}>{actionTypes.map((item) => <option key={item}>{item}</option>)}</select></label>
        {block.action.type === "product" && <select className="form-select w-full" data-testid="diy-action-product" value={block.action.target} onChange={(event) => update({ action: { ...block.action, target: event.target.value } })}><option value="">{t("Product")}</option>{products.map((item: any) => <option key={item.product_id} value={item.product_id}>{item.product_id}</option>)}</select>}
        {block.action.type === "article" && <select className="form-select w-full" data-testid="diy-action-article" value={block.action.target} onChange={(event) => update({ action: { ...block.action, target: event.target.value } })}><option value="">{t("Article")}</option>{articles.map((item: any) => <option key={item.article_id} value={item.article_id}>{item.article_id}</option>)}</select>}
        {!["product", "article"].includes(block.action.type) && <label className="block"><span className="form-label">{t("builder.action_target")}</span><input className="form-input" data-testid="diy-action-target" value={block.action.target} onChange={(event) => update({ action: { ...block.action, target: event.target.value } })} /></label>}
        <label className="block"><span className="form-label">{t("builder.open_mode")}</span><select className="form-select w-full" value={block.action.open_mode} onChange={(event) => update({ action: { ...block.action, open_mode: event.target.value as "same_tab" | "new_tab" } })}><option value="same_tab">{t("builder.same_tab")}</option><option value="new_tab">{t("builder.new_tab")}</option></select></label>
      </section>
      <div className="grid grid-cols-2 gap-2">
        <NeonButton tone="purple" onClick={onDuplicate}><Copy size={14} />{t("builder.copy")}</NeonButton>
        <NeonButton tone="warning" onClick={() => update({ enabled: !block.enabled })}>{block.enabled ? t("builder.disable") : t("builder.enable")}</NeonButton>
        <NeonButton tone="danger" onClick={onDelete}><Trash2 size={14} />{t("builder.delete")}</NeonButton>
      </div>
    </div>
  );
}
