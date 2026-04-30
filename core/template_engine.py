import html
import json
import shutil
from pathlib import Path

from sqlalchemy.orm import Session

from config import BASE_DIR, GENERATED_DIR
from core.models import Article, ArticleTranslation, I18nLanguage, Page, Payment, Product, ProductTranslation, SeoRecord, Site
from core.public_url import resolve_public_url
from core.utils import slugify


ALL_LANGUAGES = ["en", "zh-CN", "es", "pt", "ur-Latn", "hi", "de", "vi", "ja"]


class TemplateEngine:
    def template_dir(self, site: Site) -> Path:
        name = site.template_id or "landing1"
        path = BASE_DIR / "templates" / name
        return path if path.exists() else BASE_DIR / "templates" / "landing1"

    def render_site(self, db: Session, site_id: str) -> dict[str, str]:
        site = db.get(Site, site_id)
        if not site:
            return {}
        out = GENERATED_DIR / site_id / "dist"
        if out.exists():
            shutil.rmtree(out)
        out.mkdir(parents=True, exist_ok=True)
        tpl = self.template_dir(site)
        shutil.copyfile(tpl / "style.css", out / "style.css")
        self._append_builder_css(out / "style.css")

        pages: dict[str, str] = {}
        files: dict[str, str] = {}
        files[str((out / "style.css").resolve())] = (out / "style.css").read_text(encoding="utf-8")
        languages = self._languages(db, site)
        public_url = resolve_public_url(db, site).rstrip("/") + "/"
        home_page = (
            db.query(Page)
            .filter(Page.site_id == site_id, Page.status == "published", Page.slug.in_(["/", "", "home", "index"]))
            .first()
        )

        for language in languages:
            prefix = "" if language == (site.default_language or "en") else f"{self._url_lang(language)}/"
            if home_page:
                title = self._translated(home_page, language, "title") or site.alias
                description = self._translated(home_page, language, "subtitle") or site.description or site.alias
                index_html = self._document(
                    site,
                    language,
                    self._seo_meta(db, site, language, "/", f"{public_url}{prefix}", public_url, title, description),
                    self._render_blocks(home_page, language),
                )
            else:
                index_html = self._render(
                    tpl / "index.html",
                    {
                        "language": language,
                        "seo_meta": self._seo_meta(db, site, language, "/", f"{public_url}{prefix}", public_url),
                        "site_type": site.site_type,
                        "title": html.escape(site.alias),
                        "description": html.escape(site.description or f"{site.alias} powered by Site Factory OS"),
                        "cta_url": "/products/",
                        "cta_text": "Shop Now",
                    },
                )
            self._write(out / prefix / "index.html", index_html)
            pages[f"/{prefix}"] = index_html
            files[str((out / prefix / "index.html").resolve())] = index_html

        for page in db.query(Page).filter(Page.site_id == site_id, Page.status == "published").all():
            if home_page and page.page_id == home_page.page_id:
                continue
            slug = (page.slug or "page").strip("/").replace(".html", "") or "page"
            for language in languages:
                prefix = "" if language == (site.default_language or "en") else f"{self._url_lang(language)}/"
                rel_path = f"pages/{slug}/index.html"
                title = self._translated(page, language, "title") or slug.replace("-", " ").title()
                description = self._translated(page, language, "subtitle") or site.description or site.alias
                body = self._document(
                    site,
                    language,
                    self._seo_meta(db, site, language, f"/pages/{slug}/", f"{public_url}{prefix}pages/{slug}/", public_url, title, description),
                    self._render_blocks(page, language),
                )
                self._write(out / prefix / rel_path, body)
                pages[f"/{prefix}{rel_path}"] = body
                files[str((out / prefix / rel_path).resolve())] = body

        for article in db.query(Article).filter(Article.site_id == site_id).all():
            for trans in db.query(ArticleTranslation).filter(ArticleTranslation.article_id == article.article_id).all():
                for language in languages:
                    prefix = "" if language == (site.default_language or "en") else f"{self._url_lang(language)}/"
                    path = f"articles/{trans.slug}.html"
                    body = self._render(
                        tpl / "article.html",
                        {
                            "language": language,
                            "seo_meta": self._seo_meta(db, site, language, f"/{path}", f"{public_url}{prefix}{path}", public_url, trans.seo_title or trans.title, trans.seo_description),
                            "title": html.escape(trans.title),
                            "content": html.escape(trans.content).replace("\n", "<br>"),
                        },
                    )
                    self._write(out / prefix / path, body)
                    pages[f"/{prefix}{path}"] = body
                    files[str((out / prefix / path).resolve())] = body

        for product in db.query(Product).filter(Product.site_id == site_id).all():
            payment = db.get(Payment, product.payment_id) if product.payment_id else None
            for trans in db.query(ProductTranslation).filter(ProductTranslation.product_id == product.product_id).all():
                for language in languages:
                    prefix = "" if language == (site.default_language or "en") else f"{self._url_lang(language)}/"
                    path = f"products/{trans.slug}.html"
                    body = self._render(
                        tpl / "product.html",
                        {
                            "language": language,
                            "seo_meta": self._seo_meta(db, site, language, f"/{path}", f"{public_url}{prefix}{path}", public_url, trans.seo_title or trans.name, trans.seo_description),
                            "name": html.escape(trans.name),
                            "description": html.escape(trans.description or ""),
                            "price": str(product.price),
                            "currency": product.currency,
                            "payment_button": f'<a class="button" href="{html.escape(payment.payment_url)}">Buy Now</a>' if payment else "",
                        },
                    )
                    self._write(out / prefix / path, body)
                    pages[f"/{prefix}{path}"] = body
                    files[str((out / prefix / path).resolve())] = body

        if (site.default_language or "en") in languages:
            language_prefixes = tuple(f"/{self._url_lang(code)}/" for code in languages if code != (site.default_language or "en"))
            for page_path, body in list(pages.items()):
                if page_path.startswith(language_prefixes):
                    continue
                en_path = "/en/" if page_path == "/" else f"/en{page_path}"
                rel_path = "en/index.html" if en_path == "/en/" else en_path.strip("/")
                if en_path.endswith("/") and en_path != "/en/":
                    rel_path = f"{rel_path}/index.html"
                self._write(out / rel_path, body)
                pages[en_path] = body
                files[str((out / rel_path).resolve())] = body
        sitemap_body = self._sitemap(public_url, pages.keys())
        robots_body = f"User-agent: *\nAllow: /\nSitemap: {public_url}sitemap.xml\n"
        self._write(out / "sitemap.xml", sitemap_body)
        self._write(out / "robots.txt", robots_body)
        files[str((out / "sitemap.xml").resolve())] = sitemap_body
        files[str((out / "robots.txt").resolve())] = robots_body
        return files

    def _languages(self, db: Session, site: Site) -> list[str]:
        rows = db.query(I18nLanguage).filter(I18nLanguage.site_id == site.site_id, I18nLanguage.enabled == 1).all()
        codes = [row.language_code for row in rows] or [site.default_language or "en"]
        return [code for code in ALL_LANGUAGES if code in set(codes)]

    def _url_lang(self, language: str) -> str:
        return "zh" if language == "zh-CN" else language

    def _seo_slug(self, db: Session, site: Site, language: str) -> str:
        record = db.query(SeoRecord).filter(SeoRecord.site_id == site.site_id, SeoRecord.language_code == language).first()
        slug = (record.slug if record else "") or ""
        if not slug:
            return "/"
        return slug if slug.startswith("/") else f"/{slug}"

    def _render(self, template_path: Path, context: dict[str, str]) -> str:
        text = template_path.read_text(encoding="utf-8")
        for key, value in context.items():
            text = text.replace("{{ " + key + " }}", value)
        return text

    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _append_builder_css(self, path: Path) -> None:
        path.write_text(
            path.read_text(encoding="utf-8")
            + """
.sfs-hero,.sfs-text,.sfs-block{padding:calc(64px * var(--sfs-scale,1)) calc(24px * var(--sfs-scale,1));max-width:1120px;margin:auto}
body{position:relative;min-height:2200px;background:#f8fafc}
.sfs-builder-block{box-sizing:border-box;overflow:hidden}
.sfs-builder-block h1{font-size:calc(44px * var(--sfs-scale,1));line-height:1.05}
.sfs-builder-block h2{font-size:calc(30px * var(--sfs-scale,1));line-height:1.12}
.sfs-builder-block p,.sfs-builder-block input{font-size:calc(16px * var(--sfs-scale,1));line-height:1.45}
.sfs-button,.sfs-floating-button{display:inline-flex;align-items:center;justify-content:center;padding:calc(12px * var(--sfs-scale,1)) calc(18px * var(--sfs-scale,1));border-radius:calc(14px * var(--sfs-scale,1));background:var(--sfs-button-color,#00E5FF);color:#07111f;text-decoration:none;font-weight:800;font-size:calc(16px * var(--sfs-scale,1));min-height:calc(42px * var(--sfs-scale,1))}
.sfs-floating-button{position:fixed;z-index:20;box-shadow:0 0 28px rgba(0,229,255,.5)}
.sfs-pricing-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px;margin-top:24px}
.sfs-price-card{border:1px solid rgba(0,229,255,.25);border-radius:20px;padding:24px;background:rgba(17,24,39,.8)}
.sfs-product-card{display:grid;grid-template-columns:220px 1fr;gap:24px;align-items:center}
.sfs-product-card img,.sfs-image img{width:100%;max-width:100%;height:100%;object-fit:cover;border-radius:calc(18px * var(--sfs-scale,1))}
.sfs-topnav{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:18px 28px;border-radius:24px;box-shadow:0 16px 44px rgba(15,23,42,.12)}
.sfs-topnav strong{font-size:20px}.sfs-topnav nav{display:flex;gap:18px;flex-wrap:wrap}.sfs-topnav nav span{font-size:13px;font-weight:800;color:#64748b}
.sfs-cta{display:flex;flex-direction:column;justify-content:center;border-radius:28px;background:#111827;color:#E5F7FF}
.sfs-footer{display:flex;flex-direction:column;justify-content:space-between;gap:18px;padding:28px;border-radius:24px;background:#07111f;color:#E5F7FF}
.sfs-footer nav{display:flex;gap:14px;flex-wrap:wrap}.sfs-footer nav span{color:#00E5FF;font-weight:800}
.sfs-coupon{background:#7C4DFF;color:#fff;text-align:center;padding:22px;border-radius:18px;font-weight:900}
.sfs-trust{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;text-align:center}
.sfs-float-bar{position:fixed;left:0;right:0;bottom:0;z-index:19;background:#111827;padding:12px;text-align:center}
.sfs-popup{position:fixed;inset:0;display:none;place-items:center;background:rgba(0,0,0,.62);z-index:30}
.sfs-popup:target,.sfs-popup-delay{display:grid}
.sfs-popup-card{max-width:520px;border:1px solid rgba(0,229,255,.35);border-radius:20px;background:#111827;padding:28px;color:#E5F7FF;box-shadow:0 0 42px rgba(0,229,255,.22)}
.sfs-announcement{background:#7C4DFF;color:white;text-align:center;padding:10px;font-weight:800}
.sfs-divider{border:0;border-top:1px solid rgba(255,255,255,.18)}
.sfs-spacer{height:48px}
""",
            encoding="utf-8",
        )

    def _document(self, site: Site, language: str, seo_meta: str, body: str) -> str:
        return f'<!doctype html><html lang="{html.escape(language)}"><head>{seo_meta}<link rel="stylesheet" href="/style.css"></head><body>{body}</body></html>'

    def _layout(self, page: Page | None) -> dict:
        if not page:
            return {"blocks": []}
        try:
            return json.loads(page.layout_json or "{}")
        except json.JSONDecodeError:
            return {"blocks": []}

    def _translated(self, page: Page | None, language: str, key: str) -> str:
        layout = self._layout(page)
        value = layout.get("translations", {}).get(language, {}).get(key) or layout.get("translations", {}).get("en", {}).get(key)
        if value:
            return str(value)
        for block in layout.get("blocks", []):
            value = block.get("translations", {}).get(language, {}).get(key) or block.get("translations", {}).get("en", {}).get(key)
            if value:
                return str(value)
        return ""

    def _block_text(self, block: dict, language: str, key: str, default: str = "") -> str:
        value = (
            block.get("translations", {}).get(language, {}).get(key)
            or block.get("translations", {}).get("en", {}).get(key)
            or block.get("content", {}).get(key)
            or block.get("props", {}).get(key)
            or default
        )
        return html.escape(str(value))

    def _block_style(self, block: dict) -> str:
        style = block.get("style") or {}
        layout = block.get("layout") or {}
        css = []
        width_value = block.get("width", style.get("width"))
        height_value = block.get("height", style.get("height"))
        scale = block.get("scale")
        try:
            numeric_width = float(width_value)
            numeric_height = float(height_value)
            if scale in (None, ""):
                scale = max(0.55, min(2.2, min(numeric_width / 720, numeric_height / 260)))
        except (TypeError, ValueError):
            pass
        if scale not in (None, ""):
            try:
                css.append(f"--sfs-scale:{float(scale):.3f}")
            except (TypeError, ValueError):
                pass
        mapping = {
            "width": "width",
            "height": "height",
            "margin": "margin",
            "padding": "padding",
            "background": "background",
            "color": "color",
            "borderColor": "border-color",
            "borderRadius": "border-radius",
            "fontSize": "font-size",
        }
        for key, css_key in mapping.items():
            value = block.get(key) if key in {"width", "height"} and block.get(key) not in (None, "") else style.get(key)
            if value not in (None, ""):
                unit = "px" if isinstance(value, (int, float)) and key in {"width", "height", "fontSize", "borderRadius"} else ""
                css.append(f"{css_key}:{html.escape(str(value))}{unit}")
        if style.get("borderColor"):
            css.append(f"border:1px solid {html.escape(str(style['borderColor']))}")
        if style.get("buttonColor"):
            css.append(f"--sfs-button-color:{html.escape(str(style['buttonColor']))}")
        mode = layout.get("mode")
        if mode in {"absolute", "fixed", "sticky"}:
            css.append(f"position:{html.escape(str(mode))}")
            anchor = layout.get("anchor")
            x_value = int(layout.get("x") or 0)
            y_value = int(layout.get("y") or 0)
            width_px = 0
            height_px = 0
            try:
                width_px = int(float(width_value or style.get("width") or 0))
                height_px = int(float(height_value or style.get("height") or 0))
            except (TypeError, ValueError):
                pass
            if mode == "fixed" and anchor in {"top-right", "bottom-right", "bottom-left"}:
                if "right" in anchor:
                    css.append(f"right:{max(0, 1200 - x_value - width_px)}px")
                else:
                    css.append(f"left:{x_value}px")
                if "bottom" in anchor:
                    css.append(f"bottom:{max(0, 860 - y_value - height_px)}px")
                else:
                    css.append(f"top:{y_value}px")
            else:
                if layout.get("x") is not None:
                    css.append(f"left:{x_value}px")
                if layout.get("y") is not None:
                    css.append(f"top:{y_value}px")
            if layout.get("zIndex") is not None:
                css.append(f"z-index:{int(layout.get('zIndex') or 1)}")
        return f' style="{";".join(css)}"' if css else ""

    def _action_attrs(self, action: dict | None) -> str:
        action = action or {"type": "none"}
        action_type = action.get("type", "none")
        tracking = html.escape(str(action.get("tracking_id", "")))
        open_mode = action.get("open_mode", "same_tab")
        target = "_blank" if open_mode == "new_tab" else "_self"
        action_target = str(action.get("target") or action.get("url") or "#")
        if action_type == "external_url":
            return f'href="{html.escape(action_target)}" target="{target}" data-action="external_url" data-tracking-id="{tracking}"'
        if action_type in {"popup", "open_popup"}:
            popup_id = html.escape(str(action.get("popup_id") or action.get("target") or ""))
            return f'href="#{popup_id}" data-action="popup" data-popup-id="{popup_id}" data-tracking-id="{tracking}"'
        if action_type == "product":
            slug = slugify(action_target)
            return f'href="/products/{html.escape(slug)}.html" target="{target}" data-action="product" data-target="{html.escape(action_target)}" data-tracking-id="{tracking}"'
        if action_type == "article":
            slug = slugify(action_target)
            return f'href="/articles/{html.escape(slug)}.html" target="{target}" data-action="article" data-target="{html.escape(action_target)}" data-tracking-id="{tracking}"'
        if action_type in {"payment", "whatsapp", "telegram", "email", "phone"}:
            return f'href="{html.escape(action_target)}" target="{target}" data-action="{html.escape(action_type)}" data-tracking-id="{tracking}"'
        return f'href="#" data-action="none" data-tracking-id="{tracking}"'

    def _render_blocks(self, page: Page | None, language: str) -> str:
        layout = self._layout(page)
        rendered: list[str] = []
        popups: list[str] = []
        for block in layout.get("blocks", []):
            if block.get("enabled", True) is False:
                continue
            block_type = block.get("type", "Text")
            block_id = html.escape(str(block.get("id", slugify(block_type))))
            title = self._block_text(block, language, "title", block_type)
            text = self._block_text(block, language, "body", self._block_text(block, language, "text", self._block_text(block, language, "subtitle", "")))
            subtitle = self._block_text(block, language, "subtitle", "")
            label = self._block_text(block, language, "label", title)
            action = block.get("action") or block.get("props", {}).get("action")
            style_attr = self._block_style(block)
            if block_type == "TopNav":
                items = [html.escape(item.strip()) for item in (subtitle or "Home · Features · Content · Contact").replace("|", "·").split("·") if item.strip()]
                nav = "".join([f"<span>{item}</span>" for item in items[:5]])
                rendered.append(f'<header id="{block_id}" class="sfs-topnav sfs-builder-block"{style_attr}><strong>{title}</strong><nav>{nav}</nav><a class="sfs-button" {self._action_attrs(action)}>{label}</a></header>')
            elif block_type == "Hero":
                rendered.append(f'<section id="{block_id}" class="sfs-hero sfs-builder-block"{style_attr}><p>{subtitle}</p><h1>{title}</h1><p>{text}</p><a class="sfs-button" {self._action_attrs(action)}>{label}</a></section>')
            elif block_type in {"CTA", "CTASection"}:
                rendered.append(f'<section id="{block_id}" class="sfs-hero sfs-cta sfs-builder-block"{style_attr}><p>{subtitle}</p><h2>{title}</h2><p>{text}</p><a class="sfs-button" {self._action_attrs(action)}>{label}</a></section>')
            elif block_type in {"Text", "HtmlBlock", "CustomHtml"}:
                rendered.append(f'<section id="{block_id}" class="sfs-text sfs-builder-block"{style_attr}><h2>{title}</h2><p>{text}</p></section>')
            elif block_type == "Image":
                image_url = html.escape(str(block.get("props", {}).get("imageUrl", "")))
                rendered.append(f'<figure id="{block_id}" class="sfs-image sfs-builder-block"{style_attr}><img src="{image_url}" alt="{title}"><figcaption>{title}</figcaption></figure>')
            elif block_type in {"CTA", "Button", "LinkButton", "PaymentButton", "WhatsAppButton", "TelegramButton", "FloatingButton"}:
                css = "sfs-floating-button" if block_type == "FloatingButton" else "sfs-button"
                rendered.append(f'<a id="{block_id}" class="{css} sfs-builder-block" {self._action_attrs(action)}{style_attr}>{label}</a>')
            elif block_type == "PricingTable":
                plans = block.get("props", {}).get("plans") or ["Trial", "Pro", "Enterprise"]
                cards = "".join([f'<div class="sfs-price-card"><h3>{html.escape(str(plan))}</h3><p>{text}</p></div>' for plan in plans])
                rendered.append(f'<section id="{block_id}" class="sfs-block sfs-builder-block"{style_attr}><h2>{title}</h2><div class="sfs-pricing-grid">{cards}</div></section>')
            elif block_type in {"ProductCard", "ArticleCard", "ImageText"}:
                image_url = html.escape(str(block.get("props", {}).get("imageUrl", "")))
                image = f'<img src="{image_url}" alt="{title}">' if image_url else ""
                rendered.append(f'<section id="{block_id}" class="sfs-block sfs-product-card sfs-builder-block"{style_attr}>{image}<div><h2>{title}</h2><p>{text}</p><a class="sfs-button" {self._action_attrs(action)}>{label}</a></div></section>')
            elif block_type == "ArticleList":
                cards = "".join([f'<div class="sfs-price-card"><h3>{title} {i}</h3><p>{text}</p><a class="sfs-button" {self._action_attrs(action)}>{label}</a></div>' for i in range(1, 4)])
                rendered.append(f'<section id="{block_id}" class="sfs-block sfs-builder-block"{style_attr}><h2>{title}</h2><div class="sfs-pricing-grid">{cards}</div></section>')
            elif block_type == "CountdownTimer":
                rendered.append(f'<section id="{block_id}" class="sfs-block sfs-builder-block"{style_attr}><h2>{title}</h2><div class="sfs-pricing-grid"><b>12</b><b>08</b><b>44</b><b>19</b></div></section>')
            elif block_type == "FormBlock":
                rendered.append(f'<form id="{block_id}" class="sfs-block sfs-builder-block" action="/api/v1/forms/submit" method="post"{style_attr}><h2>{title}</h2><p>{text}</p><input name="email" placeholder="Email"><button class="sfs-button" type="submit">{label}</button></form>')
            elif block_type == "CouponBanner":
                rendered.append(f'<section id="{block_id}" class="sfs-coupon sfs-builder-block"{style_attr}>{title}</section>')
            elif block_type == "TrustBadge":
                badges = block.get("props", {}).get("badges") or [title, subtitle, label]
                rendered.append(f'<section id="{block_id}" class="sfs-trust sfs-builder-block"{style_attr}>{"".join([f"<div>{html.escape(str(badge))}</div>" for badge in badges[:6]])}</section>')
            elif block_type == "ContactFloatBar":
                rendered.append(f'<div id="{block_id}" class="sfs-float-bar"><a {self._action_attrs(action)}>{title}</a></div>')
            elif block_type == "PopupModal":
                popup_id = html.escape(str(block.get("props", {}).get("popup_id", block_id)))
                trigger = html.escape(str(block.get("props", {}).get("trigger", "button")))
                popups.append(f'<div id="{popup_id}" class="sfs-popup" data-trigger="{trigger}"><div class="sfs-popup-card"><h2>{title}</h2><p>{text}</p></div></div>')
            elif block_type == "AnnouncementBar":
                rendered.append(f'<div id="{block_id}" class="sfs-announcement">{title}</div>')
            elif block_type == "Divider":
                rendered.append(f'<hr id="{block_id}" class="sfs-divider">')
            elif block_type == "Spacer":
                rendered.append(f'<div id="{block_id}" class="sfs-spacer"></div>')
            elif block_type == "Footer":
                links = [html.escape(item.strip()) for item in (subtitle or "Privacy · Terms · Contact").replace("|", "·").split("·") if item.strip()]
                nav = "".join([f"<span>{item}</span>" for item in links[:5]])
                rendered.append(f'<footer id="{block_id}" class="sfs-footer sfs-builder-block"{style_attr}><div><h2>{title}</h2><p>{text}</p></div><nav>{nav}</nav></footer>')
            else:
                rendered.append(f'<section id="{block_id}" class="sfs-block sfs-{html.escape(block_type.lower())}"><h2>{title}</h2><p>{text}</p></section>')
        return "\n".join(rendered + popups) or "<main></main>"

    def _seo_meta(self, db: Session, site: Site, language: str, path: str, canonical: str, public_url: str, title: str | None = None, description: str | None = None) -> str:
        record = db.query(SeoRecord).filter(SeoRecord.site_id == site.site_id, SeoRecord.language_code == language).first()
        title = (record.title if record else None) or title or site.alias
        description = (record.description if record else None) or description or site.description or site.alias
        hrefs = []
        clean_path = path if path.startswith("/") else f"/{path}"
        enabled_languages = self._languages(db, site)
        if len(enabled_languages) > 1:
            for code in enabled_languages:
                prefix = "" if code == site.default_language else f"{self._url_lang(code)}/"
                hrefs.append(f'<link rel="alternate" hreflang="{code}" href="{public_url}{prefix}{clean_path.lstrip("/")}" />')
        hreflang = "\n".join(hrefs)
        return f"""<meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <meta name="description" content="{html.escape(description or '')}">
  <link rel="canonical" href="{canonical}">
  {hreflang}
  <meta property="og:title" content="{html.escape(title)}">
  <meta property="og:description" content="{html.escape(description or '')}">
  <meta property="og:url" content="{canonical}">"""

    def _sitemap(self, public_url: str, paths) -> str:
        urls = "\n".join([f"  <url><loc>{public_url}{str(path).lstrip('/')}</loc></url>" for path in paths])
        return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}\n</urlset>\n'
