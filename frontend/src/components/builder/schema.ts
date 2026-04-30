export type ViewportMode = "desktop" | "mobile";
export type PositionMode = "normal" | "absolute" | "fixed" | "sticky";
export type ActionType = "none" | "external_url" | "product" | "article" | "popup" | "whatsapp" | "telegram";

export type BlockAction = {
  type: ActionType;
  target: string;
  open_mode: "same_tab" | "new_tab";
  tracking_id?: string;
};

export type PageBlock = {
  id: string;
  type: string;
  enabled: boolean;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  scale?: number;
  props: Record<string, any>;
  style: {
    width?: number | string;
    height?: number | string;
    margin?: string;
    padding?: string;
    background?: string;
    color?: string;
    buttonColor?: string;
    borderColor?: string;
    borderRadius?: string;
    fontSize?: string;
  };
  layout: {
    mode: PositionMode;
    x?: number;
    y?: number;
    zIndex?: number;
    anchor?: "top-left" | "top-right" | "bottom-left" | "bottom-right" | "center";
  };
  action: BlockAction;
  translations: Record<string, Record<string, string>>;
  responsive?: {
    desktop?: Partial<PageBlock>;
    mobile?: Partial<PageBlock>;
  };
};

export type PageSchema = {
  pageId: string;
  siteId: string;
  path: string;
  locale: string;
  viewport: ViewportMode;
  templateId?: string;
  template_type?: "static_template" | "builder_template" | string;
  mode?: "static_template" | "builder_template" | string;
  static_template?: {
    normalized_path?: string;
    entry?: string;
    preview?: string;
    asset_root?: string;
  };
  blocks: PageBlock[];
  translations: Record<string, Record<string, string>>;
};

export function blockKey(type: string) {
  return type.replace(/([a-z0-9])([A-Z])/g, "$1_$2").replace(/[\s-]+/g, "_").toLowerCase();
}
