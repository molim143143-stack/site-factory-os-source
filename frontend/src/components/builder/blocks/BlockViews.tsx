import type { CSSProperties } from "react";
import type { PageBlock } from "../schema";

type Props = { block: PageBlock; locale: string };

function text(block: PageBlock, locale: string, key: string) {
  return block.translations?.[locale]?.[key] || block.translations?.en?.[key] || block.props?.[key] || "";
}

function asNumber(value: unknown, fallback: number) {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  const parsed = Number.parseFloat(String(value ?? ""));
  return Number.isFinite(parsed) ? parsed : fallback;
}

function metrics(block: PageBlock, baseW = 720, baseH = 260) {
  const width = asNumber(block.style.width ?? block.width, baseW);
  const height = asNumber(block.style.height ?? block.height, baseH);
  const scale = Number((block.scale ?? Math.max(0.55, Math.min(2.2, Math.min(width / baseW, height / baseH)))).toFixed(3));
  return { width, height, scale };
}

function shell(block: PageBlock, baseW = 720, baseH = 260): CSSProperties {
  const { scale } = metrics(block, baseW, baseH);
  return {
    width: "100%",
    height: "100%",
    minHeight: 0,
    boxSizing: "border-box",
    overflow: "hidden",
    background: block.style.background,
    color: block.style.color,
    border: block.style.borderColor ? `1px solid ${block.style.borderColor}` : undefined,
    borderRadius: block.style.borderRadius || `${Math.round(22 * scale)}px`,
    padding: block.style.padding || `${Math.round(24 * scale)}px`,
    gap: `${Math.round(16 * scale)}px`
  };
}

function buttonStyle(block: PageBlock, baseW = 720, baseH = 260): CSSProperties {
  const scale = metrics(block, baseW, baseH).scale;
  return {
    backgroundColor: block.style.buttonColor,
    padding: `${Math.round(12 * scale)}px ${Math.round(20 * scale)}px`,
    fontSize: font(16, block, baseW, baseH)
  };
}

function font(size: number, block: PageBlock, baseW = 720, baseH = 260) {
  return `${Math.round(size * metrics(block, baseW, baseH).scale)}px`;
}

function actionHref(block: PageBlock) {
  return block.action.type === "popup" ? `#${block.action.target}` : block.action.target || "#";
}

export function HeroBlock({ block, locale }: Props) {
  return (
    <section className="flex flex-col justify-center bg-[radial-gradient(circle_at_20%_20%,rgba(0,229,255,.28),transparent_32%),linear-gradient(135deg,#0b1224,#182047)] text-white" style={shell(block, 720, 360)}>
      <p className="font-black uppercase tracking-[0.32em] text-neon" style={{ fontSize: font(12, block, 720, 360) }}>{text(block, locale, "subtitle")}</p>
      <h1 className="mt-3 max-w-full font-black leading-tight" style={{ fontSize: font(48, block, 720, 360) }}>{text(block, locale, "title")}</h1>
      <p className="mt-3 max-w-full text-textWeak" style={{ fontSize: font(18, block, 720, 360), lineHeight: 1.45 }}>{text(block, locale, "body")}</p>
      <a className="mt-5 inline-flex w-max items-center justify-center rounded-xl bg-neon font-black text-void" style={buttonStyle(block, 720, 360)} href={actionHref(block)}>{text(block, locale, "label")}</a>
    </section>
  );
}

export function NavigationBlock({ block, locale }: Props) {
  const scale = metrics(block, 1040, 76).scale;
  const items = (text(block, locale, "subtitle") || "Home · Features · Content · Contact").split(/[·|,]/).map((item: string) => item.trim()).filter(Boolean);
  return (
    <header className="flex h-full w-full items-center justify-between bg-white text-slate-950 shadow-sm" style={shell(block, 1040, 76)}>
      <div className="min-w-0">
        <p className="truncate font-black" style={{ fontSize: font(20, block, 1040, 76) }}>{text(block, locale, "title")}</p>
      </div>
      <nav className="hidden min-w-0 flex-1 justify-center gap-4 px-4 md:flex" style={{ fontSize: font(13, block, 1040, 76) }}>
        {items.slice(0, 5).map((item: string) => <a key={item} className="whitespace-nowrap font-bold text-slate-500" href="#">{item}</a>)}
      </nav>
      <a className="inline-flex shrink-0 rounded-xl font-black text-void" style={buttonStyle(block, 1040, 76)} href={actionHref(block)}>{text(block, locale, "label")}</a>
    </header>
  );
}

export function TextBlock({ block, locale }: Props) {
  return <section className="bg-white text-slate-900" style={shell(block)}><h2 className="font-black" style={{ fontSize: font(30, block) }}>{text(block, locale, "title")}</h2><p className="mt-3 text-slate-600" style={{ fontSize: font(16, block), lineHeight: 1.55 }}>{text(block, locale, "body")}</p></section>;
}

export function ImageBlock({ block, locale }: Props) {
  const captionH = Math.max(34, Math.round(44 * metrics(block).scale));
  return <figure className="bg-slate-950" style={{ ...shell(block), padding: 0 }}><img className="w-full object-cover" style={{ height: `calc(100% - ${captionH}px)` }} src={block.props.imageUrl || "https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1200"} alt={text(block, locale, "title")} /><figcaption className="text-textWeak" style={{ height: captionH, padding: `${Math.round(10 * metrics(block).scale)}px ${Math.round(16 * metrics(block).scale)}px`, fontSize: font(14, block) }}>{text(block, locale, "title")}</figcaption></figure>;
}

export function ButtonBlock({ block, locale }: Props) {
  return <section className="flex items-center justify-center text-center" style={shell(block)}><a className="inline-flex items-center justify-center rounded-xl bg-plasma font-black text-white shadow-plasma" style={{ ...buttonStyle(block), minWidth: Math.round(120 * metrics(block).scale), minHeight: Math.round(44 * metrics(block).scale) }} href={actionHref(block)}>{text(block, locale, "label")}</a></section>;
}

export function PricingTableBlock({ block, locale }: Props) {
  const plans = block.props.plans || ["Trial", "Pro", "Enterprise"];
  const scale = metrics(block).scale;
  return <section className="bg-[#101827]" style={shell(block)}><h2 className="font-black text-textMain" style={{ fontSize: font(30, block) }}>{text(block, locale, "title")}</h2><div className="mt-4 grid h-[calc(100%-56px)] grid-cols-3" style={{ gap: Math.round(14 * scale) }}>{plans.map((plan: string, index: number) => <div key={plan} className="overflow-hidden rounded-2xl border border-neon/20 bg-white/5" style={{ padding: Math.round(18 * scale) }}><p className="font-black text-neon" style={{ fontSize: font(16, block) }}>{plan}</p><p className="mt-2 font-black text-textMain" style={{ fontSize: font(28, block) }}>${index === 0 ? 0 : index === 1 ? 99 : 499}</p><p className="mt-2 text-textWeak" style={{ fontSize: font(13, block) }}>{text(block, locale, "body")}</p></div>)}</div></section>;
}

export function ProductCardBlock({ block, locale }: Props) {
  const scale = metrics(block).scale;
  return <section className="grid bg-white text-slate-900" style={{ ...shell(block), gridTemplateColumns: "34% 1fr" }}><img className="h-full w-full rounded-2xl object-cover" src={block.props.imageUrl || "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=800"} alt={text(block, locale, "title")} /><div className="min-w-0"><p className="font-black uppercase text-plasma" style={{ fontSize: font(12, block) }}>{text(block, locale, "subtitle")}</p><h2 className="mt-2 font-black" style={{ fontSize: font(30, block), lineHeight: 1.05 }}>{text(block, locale, "title")}</h2><p className="mt-2 text-slate-600" style={{ fontSize: font(14, block), lineHeight: 1.45 }}>{text(block, locale, "body")}</p><a className="mt-3 inline-flex rounded-xl bg-slate-950 font-black text-white" style={{ ...buttonStyle(block), padding: `${Math.round(10 * scale)}px ${Math.round(18 * scale)}px`, fontSize: font(14, block) }} href={actionHref(block)}>{text(block, locale, "label")}</a></div></section>;
}

export function ArticleCardBlock({ block, locale }: Props) {
  return <article className="border border-white/10 bg-[#111827]" style={shell(block)}><p className="font-black uppercase tracking-[0.24em] text-neon" style={{ fontSize: font(12, block) }}>{text(block, locale, "subtitle")}</p><h2 className="mt-3 font-black text-textMain" style={{ fontSize: font(30, block), lineHeight: 1.1 }}>{text(block, locale, "title")}</h2><p className="mt-3 text-textWeak" style={{ fontSize: font(15, block), lineHeight: 1.5 }}>{text(block, locale, "body")}</p><a className="mt-4 inline-flex text-neon" style={{ fontSize: font(15, block) }} href={actionHref(block)}>{text(block, locale, "label")}</a></article>;
}

export function CountdownTimerBlock({ block, locale }: Props) {
  return <section className="bg-warning/10 text-center" style={shell(block)}><h2 className="font-black text-warning" style={{ fontSize: font(24, block) }}>{text(block, locale, "title")}</h2><div className="mt-4 grid grid-cols-4" style={{ gap: Math.round(12 * metrics(block).scale) }}>{["12", "08", "44", "19"].map((v, i) => <div key={i} className="rounded-xl bg-white/10 font-black text-textMain" style={{ padding: Math.round(12 * metrics(block).scale), fontSize: font(24, block) }}>{v}</div>)}</div></section>;
}

export function FormBlock({ block, locale }: Props) {
  const scale = metrics(block).scale;
  return <form className="bg-white text-slate-900" style={shell(block)}><h2 className="font-black" style={{ fontSize: font(24, block) }}>{text(block, locale, "title")}</h2><input className="mt-4 w-full rounded-xl border" style={{ padding: Math.round(12 * scale), fontSize: font(15, block) }} placeholder={block.props.placeholder || "email"} /><button type="button" className="mt-3 rounded-xl bg-neon font-black text-void" style={{ ...buttonStyle(block), fontSize: font(15, block) }} onClick={(event) => event.preventDefault()}>{text(block, locale, "label")}</button></form>;
}

export function CouponBannerBlock({ block, locale }: Props) {
  return <section className="flex items-center justify-center bg-plasma text-center font-black text-white" style={{ ...shell(block), fontSize: font(20, block) }}>{text(block, locale, "title")}</section>;
}

export function TrustBadgeBlock({ block, locale }: Props) {
  const badges = block.props.badges || [text(block, locale, "title"), text(block, locale, "subtitle"), text(block, locale, "label")];
  return <section className="grid grid-cols-3 bg-white/5 text-center text-textMain" style={shell(block)}>{badges.map((item: string) => <div key={item} className="flex items-center justify-center rounded-xl border border-neon/20" style={{ padding: Math.round(14 * metrics(block).scale), fontSize: font(14, block) }}>{item}</div>)}</section>;
}

export function FooterBlock({ block, locale }: Props) {
  const links = (text(block, locale, "subtitle") || "Privacy · Terms · Contact").split(/[·|,]/).map((item: string) => item.trim()).filter(Boolean);
  return (
    <footer className="flex h-full w-full flex-col justify-between bg-[#07111F] text-textMain" style={shell(block, 1040, 190)}>
      <div className="flex items-start justify-between gap-5">
        <div className="min-w-0">
          <h2 className="truncate font-black" style={{ fontSize: font(26, block, 1040, 190) }}>{text(block, locale, "title")}</h2>
          <p className="mt-2 max-w-[620px] text-textWeak" style={{ fontSize: font(14, block, 1040, 190), lineHeight: 1.45 }}>{text(block, locale, "body")}</p>
        </div>
        <div className="flex shrink-0 flex-wrap justify-end gap-3" style={{ fontSize: font(13, block, 1040, 190) }}>
          {links.slice(0, 4).map((link: string) => <a key={link} className="font-bold text-neon" href="#">{link}</a>)}
        </div>
      </div>
      <div className="border-t border-white/10 pt-3 text-xs text-textWeak">Site Factory OS</div>
    </footer>
  );
}

export function FloatingButtonBlock({ block, locale }: Props) {
  return <a className="flex h-full w-full items-center justify-center rounded-full bg-neon font-black text-void shadow-neon" style={{ backgroundColor: block.style.buttonColor, fontSize: font(16, block, 180, 64), padding: `${Math.round(10 * metrics(block, 180, 64).scale)}px ${Math.round(18 * metrics(block, 180, 64).scale)}px` }} href={actionHref(block)}>{text(block, locale, "label")}</a>;
}

export function PopupModalBlock({ block, locale }: Props) {
  return <div id={block.props.popup_id || block.action.target || block.id} className="border border-neon/30 bg-[#111827] shadow-neon" style={shell(block)}><p className="uppercase tracking-[0.28em] text-neon" style={{ fontSize: font(11, block) }}>{text(block, locale, "subtitle")}</p><h2 className="mt-3 font-black text-textMain" style={{ fontSize: font(24, block) }}>{text(block, locale, "title")}</h2><p className="mt-3 text-textWeak" style={{ fontSize: font(15, block), lineHeight: 1.45 }}>{text(block, locale, "body")}</p></div>;
}
