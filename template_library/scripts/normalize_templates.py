import hashlib
import html
import json
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
META_DIR = ROOT / "meta"
NORMALIZED = ROOT / "normalized"
PREVIEWS = ROOT / "previews"
INDEX = META_DIR / "templates.index.json"
SOURCES = ROOT / "sources" / "templates.sources.json"

WEB_EXTENSIONS = {".html", ".htm", ".css", ".js", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".ico", ".webp", ".woff", ".woff2", ".ttf", ".eot", ".map"}
BLOCK_TAGS = ["header", "nav", "section", "main", "article", "aside", "footer"]
MEANINGFUL_DIV_CLASS = re.compile(
    r'class=["\'][^"\']*(masthead|hero|feature|service|portfolio|showcase|card|post-preview|product|pricing|resume-section|about|contact|cta|call-to-action|page-section|content-section|navbar|footer|docs|documentation|accordion)[^"\']*["\']',
    flags=re.I,
)


def clean_text(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = html.unescape(re.sub(r"\s+", " ", text)).strip()
    return text[:140]


def find_entry(raw: Path) -> tuple[Path, Path]:
    candidates = [
        raw / "dist" / "index.html",
        raw / "docs" / "index.html",
        raw / "site" / "index.html",
        raw / "index.html",
    ]
    html_path = next((path for path in candidates if path.exists()), None)
    if not html_path:
        html_path = next(raw.rglob("index.html"), None)
    if not html_path:
        raise FileNotFoundError("index.html not found")
    return html_path.parent, html_path


def copy_static_tree(source_root: Path, target_root: Path) -> None:
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True, exist_ok=True)
    for path in source_root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in WEB_EXTENSIONS:
            continue
        rel = path.relative_to(source_root)
        if any(part.startswith(".git") or part == "node_modules" for part in rel.parts):
            continue
        dest = target_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)


def rewrite_asset_paths(markup: str) -> str:
    def repl(match: re.Match) -> str:
        attr = match.group(1)
        quote = match.group(2)
        value = match.group(3)
        lower = value.lower()
        if lower.startswith(("http://", "https://", "data:", "mailto:", "tel:", "#", "{{")):
            return match.group(0)
        if value.startswith("//"):
            return match.group(0)
        clean = value.lstrip("/")
        return f'{attr}={quote}assets/site/{clean}{quote}'

    return re.sub(r'\b(src|href)=([\"\'])(?!assets/site/)([^\"\']+)\2', repl, markup)


def sanitize_publish_markup(markup: str) -> str:
    return re.sub(r"example\.com", "yourdomain.com", markup, flags=re.I)


def extract_blocks(markup: str) -> list[dict]:
    matches: list[tuple[int, str, str]] = []
    for tag in BLOCK_TAGS:
        for match in re.finditer(rf"<{tag}\b[^>]*>(.*?)</{tag}>", markup, flags=re.I | re.S):
            matches.append((match.start(), tag, match.group(0)))
    for match in re.finditer(r"<div\b[^>]*>.*?</div>", markup, flags=re.I | re.S):
        raw = match.group(0)
        if MEANINGFUL_DIV_CLASS.search(raw):
            matches.append((match.start(), "div", raw))

    blocks: list[dict] = []
    seen: set[str] = set()
    for _, tag, raw in sorted(matches, key=lambda item: item[0]):
            raw_hash = hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]
            if raw_hash in seen:
                continue
            seen.add(raw_hash)
            inner = re.sub(rf"^<{tag}\b[^>]*>|</{tag}>$", "", raw, flags=re.I | re.S)
            text = clean_text(inner)
            css_class = re.search(r'class=["\']([^"\']+)["\']', raw, flags=re.I)
            block_type = {
                "header": "TopNav",
                "nav": "TopNav",
                "main": "ImageText",
                "article": "ArticleList",
                "aside": "TrustBadge",
                "footer": "Footer",
                "div": "ImageText",
                "section": "ImageText",
            }.get(tag, "ImageText")
            lower = raw.lower()
            if tag in {"header", "nav"}:
                block_type = "TopNav"
            elif tag == "footer" or "footer" in lower or "copyright" in lower:
                block_type = "Footer"
            elif any(token in lower for token in ["cta", "call-to-action", "signup", "contact", "btn ", "btn-", "add to cart", "view options", "view details", "continue reading", "download now", "learn more"]):
                block_type = "CTASection"
            elif any(token in lower for token in ["feature", "service", "portfolio", "showcase", "product", "card", "post-preview", "resume-section", "accordion", "docs", "documentation"]):
                block_type = "TrustBadge"
            elif "masthead" in lower or "hero" in lower or "<h1" in lower:
                block_type = "Hero"
            blocks.append(
                {
                    "type": block_type,
                    "selector": tag,
                    "className": css_class.group(1) if css_class else "",
                    "text": text,
                    "content_hash": raw_hash,
                }
            )
            if len(blocks) >= 40:
                return blocks
    return blocks


def classify_sections(markup: str, blocks: list[dict]) -> dict[str, bool]:
    lower = markup.lower()
    types = {block["type"] for block in blocks}
    return {
        "header": "TopNav" in types or "<nav" in lower or "<header" in lower,
        "hero": "Hero" in types or "masthead" in lower or "<h1" in lower,
        "features": "TrustBadge" in types or any(token in lower for token in ["features", "services", "portfolio", "showcase", "product", "card", "post-preview", "resume-section", "accordion", "docs", "documentation"]),
        "cta": "CTASection" in types or any(token in lower for token in ["call-to-action", "sign up", "signup", "contact", "download", "buy now", "shop now", "get started", "add to cart", "view options", "view details", "continue reading", "btn ", "btn-"]),
        "footer": "Footer" in types or "<footer" in lower or "copyright" in lower or "social-icons" in lower,
    }


def summarize_text(text: str, fallback: str) -> tuple[str, str, str]:
    clean = re.sub(r"\s+", " ", text or "").strip()
    if not clean:
        return fallback, "", "Open"
    sentences = re.split(r"(?<=[.!?])\s+", clean)
    title = sentences[0][:78] or fallback
    body = " ".join(sentences[1:4])[:260] if len(sentences) > 1 else clean[:220]
    label = "Open"
    for candidate in ["Get Started", "Learn More", "View Details", "Contact", "Buy Now", "Read More", "Download"]:
        if candidate.lower() in clean.lower():
            label = candidate
            break
    return title, body, label


def builder_blocks(blocks: list[dict], category: str) -> list[dict]:
    heights = {
        "TopNav": 78,
        "Hero": 430,
        "TrustBadge": 210,
        "ArticleList": 330,
        "ImageText": 320,
        "CTASection": 280,
        "Footer": 190,
    }
    backgrounds = {
        "TopNav": "#FFFFFF",
        "Hero": "#F8FAFC",
        "TrustBadge": "#FFFFFF",
        "ArticleList": "#FFFFFF",
        "ImageText": "#FFFFFF",
        "CTASection": "#111827",
        "Footer": "#07111F",
    }
    colors = {
        "CTASection": "#E5F7FF",
        "Footer": "#E5F7FF",
    }
    result: list[dict] = []
    y = 32
    seen_required: set[str] = set()
    for index, block in enumerate(blocks):
        block_type = block.get("type") or "ImageText"
        if block_type in {"TopNav", "Hero", "CTASection", "Footer"} and block_type in seen_required:
            block_type = "ImageText"
        seen_required.add(block_type)
        height = heights.get(block_type, 280)
        title, body, label = summarize_text(block.get("text", ""), block_type)
        result.append(
            {
                "id": f"{block_type.lower()}_{index + 1}_{block.get('content_hash', '')}",
                "type": block_type,
                "enabled": True,
                "x": 48,
                "y": y,
                "width": 1104,
                "height": height,
                "scale": 1,
                "layout": {"mode": "absolute", "x": 48, "y": y, "zIndex": 2 + index},
                "style": {
                    "width": 1104,
                    "height": height,
                    "margin": "0",
                    "padding": "28px",
                    "background": backgrounds.get(block_type, "#FFFFFF"),
                    "color": colors.get(block_type, "#0F172A"),
                    "buttonColor": "#2563EB" if category not in {"agency", "saas"} else "#F97316",
                    "borderColor": "#E2E8F0",
                    "borderRadius": 18,
                },
                "props": {"sourceSelector": block.get("selector"), "sourceClass": block.get("className"), "sourceHash": block.get("content_hash")},
                "action": {
                    "type": "external_url" if block_type in {"TopNav", "Hero", "CTASection"} else "none",
                    "target": "#contact" if block_type in {"TopNav", "Hero", "CTASection"} else "",
                    "open_mode": "same_tab",
                    "tracking_id": f"template_{category}_{block_type.lower()}",
                },
                "translations": {
                    "en": {
                        "title": title,
                        "subtitle": category.title(),
                        "body": body,
                        "label": label,
                    }
                },
                "source": block,
            }
        )
        y += height + 42
    return result


def combined_css_length(asset_root: Path) -> int:
    return sum(len(path.read_text(encoding="utf-8", errors="ignore")) for path in asset_root.rglob("*.css"))


def first_css(asset_root: Path) -> str:
    css = next(asset_root.rglob("*.css"), None)
    return css.read_text(encoding="utf-8", errors="ignore") if css else ""


def write_preview_config(path: Path, template_id: str, title: str) -> None:
    path.write_text(
        json.dumps({"template_id": template_id, "type": "html_preview", "title": title, "entry": "preview.html"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def normalize_meta(meta_path: Path) -> dict | None:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("source") != "github" or not meta.get("repo_url"):
        return None
    if SOURCES.exists():
        active_repos = {item.get("repo_url") for item in json.loads(SOURCES.read_text(encoding="utf-8"))}
        if meta.get("repo_url") not in active_repos:
            return None
    if meta.get("status") not in {"raw_downloaded", "inspected", "normalized", "preview_generated", "available"}:
        return None
    raw = PROJECT_ROOT / meta["local_raw_path"]
    source_root, html_path = find_entry(raw)
    category = meta.get("category", "landing")
    target = NORMALIZED / category / meta["id"]
    asset_root = target / "assets" / "site"
    target.mkdir(parents=True, exist_ok=True)
    copy_static_tree(source_root, asset_root)
    source_html = html_path.read_text(encoding="utf-8", errors="ignore")
    normalized_html = sanitize_publish_markup(rewrite_asset_paths(source_html))
    (target / "index.html").write_text(normalized_html, encoding="utf-8")
    (target / "preview.html").write_text(normalized_html, encoding="utf-8")
    css_text = first_css(asset_root)
    if css_text:
        (target / "style.css").write_text(css_text, encoding="utf-8")
    extracted_blocks = extract_blocks(source_html)
    checks = classify_sections(source_html, extracted_blocks)
    blocks = builder_blocks(extracted_blocks, category)
    css_len = combined_css_length(asset_root)
    title_match = re.search(r"<title[^>]*>(.*?)</title>", source_html, flags=re.I | re.S)
    title = clean_text(title_match.group(1) if title_match else meta.get("name", meta["id"]))
    description = clean_text(re.search(r"<meta[^>]+name=[\"']description[\"'][^>]+content=[\"']([^\"']+)", source_html, flags=re.I).group(1)) if re.search(r"<meta[^>]+name=[\"']description[\"'][^>]+content=[\"']([^\"']+)", source_html, flags=re.I) else title
    page_schema = {
        "templateId": meta["id"],
        "type": "page_template",
        "template_type": "static_template",
        "mode": "static_template",
        "schemaVersion": 3,
        "static_template": {
            "normalized_path": str(target.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "entry": "index.html",
            "preview": "preview.html",
            "asset_root": "assets/site",
        },
        "blocks": blocks,
        "translations": {"en": {"title": title, "subtitle": meta.get("category", ""), "description": description}},
    }
    template_json = {
        "id": meta["id"],
        "name": meta.get("name", meta["id"]),
        "repo_url": meta.get("repo_url", ""),
        "repo_name": meta.get("repo_name", ""),
        "stars": meta.get("stars", 0),
        "license": meta.get("license", "unknown"),
        "framework": meta.get("framework", "html"),
        "category": category,
        "last_commit": meta.get("last_commit", ""),
        "source_path": str(html_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "local_raw_path": meta.get("local_raw_path", ""),
        "normalized_path": str(target.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "template_type": "static_template",
        "status": "available",
        "entry": "index.html",
        "preview": "preview.html",
        "preview_image": "preview.png",
        "checks": {**checks, "html_length": len(source_html), "css_length": css_len, "blocks": len(blocks)},
    }
    (target / "template.json").write_text(json.dumps(template_json, ensure_ascii=False, indent=2), encoding="utf-8")
    (target / "page.schema.json").write_text(json.dumps(page_schema, ensure_ascii=False, indent=2), encoding="utf-8")
    (target / "README.md").write_text(
        f"# {meta.get('name', meta['id'])}\n\nSource: {meta.get('repo_url')}\n\nLicense: {meta.get('license')}\n\nType: static_template. Original HTML/CSS/assets are preserved under `assets/site`.\n",
        encoding="utf-8",
    )
    write_preview_config(target / "preview.config.json", meta["id"], title)
    PREVIEWS.mkdir(parents=True, exist_ok=True)
    write_preview_config(PREVIEWS / f"{meta['id']}.json", meta["id"], title)
    meta.update(template_json)
    meta["status"] = "available"
    meta["can_use_in_builder"] = True
    meta["supports_static_export"] = True
    meta["page_schema"] = page_schema
    meta["checks"] = template_json["checks"]
    return meta


def main() -> None:
    available: list[dict] = []
    for meta_path in sorted(META_DIR.glob("*.json")):
        if meta_path.name == "templates.index.json":
            continue
        try:
            item = normalize_meta(meta_path)
            if not item:
                continue
            (META_DIR / f"{item['id']}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
            if item.get("status") == "available":
                available.append(item)
        except Exception as exc:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            if meta.get("source") == "github":
                meta["status"] = "normalize_failed"
                meta["error"] = f"{exc.__class__.__name__}: {exc}"
                meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    INDEX.write_text(json.dumps({"templates": available}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"available": len(available), "index": str(INDEX)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
