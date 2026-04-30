import difflib
import json
import os
import re
import shutil
import struct
import subprocess
import time
from pathlib import Path
from typing import Any

import requests
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "template_library" / "meta" / "templates.index.json"
REPORT = ROOT / "template_library_quality_report.json"
REPORT_COPY = ROOT / "reports" / "template_library_quality_report.json"
API = "http://127.0.0.1:8000/api/v1"
WEB = "http://127.0.0.1:5173"

MIN_HTML_BYTES = 8 * 1024
MIN_CSS_BYTES = 5 * 1024
MIN_ASSETS = 3
MIN_BLOCKS = 5
MIN_STARS = 100
MIN_PREVIEW_BYTES = 20 * 1024
MIN_PREVIEW_WIDTH = 900
MIN_PREVIEW_HEIGHT = 600
MAX_HTML_STRUCTURE_SIMILARITY = 0.92
MAX_TEXT_SIMILARITY = 0.82
MAX_SECTION_SIMILARITY = 0.95

BAD_TEST_TEXT = [
    "Site Factory Neon Landing",
    "AI website factory control deck",
    "testing template",
    "fake template",
    "Landing Page / Explore",
]

ASSET_SUFFIXES = {".css", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".ico", ".js", ".woff", ".woff2", ".ttf"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def compact_structure(text: str) -> str:
    text = re.sub(r"<script\b.*?</script>", "", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", "", text, flags=re.I | re.S)
    tokens = re.findall(r"</?(header|nav|main|section|article|aside|footer|div|h1|h2|h3|p|a|img|form|button)\b[^>]*>", text, flags=re.I)
    return " ".join(token.lower() for token in tokens)[:50000]


def visible_text_signature(text: str) -> str:
    text = re.sub(r"<script\b.*?</script>", "", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", "", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text[:50000]


def section_types(schema: dict[str, Any], checks: dict[str, Any]) -> list[str]:
    detected = []
    if checks.get("header"):
        detected.append("Header")
    if checks.get("hero"):
        detected.append("Hero")
    if checks.get("features"):
        detected.append("Features")
    if any(block.get("type") in {"ImageText", "ArticleList", "ProductCard", "ArticleCard", "TrustBadge"} for block in schema.get("blocks", [])):
        detected.append("Content/Card")
    if checks.get("cta"):
        detected.append("CTA")
    if checks.get("footer"):
        detected.append("Footer")
    return detected


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return (0, 0)
    return struct.unpack(">II", data[16:24])


def asset_count(normalized: Path) -> int:
    asset_root = normalized / "assets" / "site"
    if not asset_root.exists():
        return 0
    return sum(1 for path in asset_root.rglob("*") if path.is_file() and path.suffix.lower() in ASSET_SUFFIXES)


def css_text(normalized: Path) -> str:
    asset_root = normalized / "assets" / "site"
    if asset_root.exists():
        return "\n".join(safe_text(path) for path in asset_root.rglob("*.css"))
    return safe_text(normalized / "style.css")


def generate_preview_png(normalized: Path) -> dict[str, Any]:
    preview_html = normalized / "preview.html"
    preview_png = normalized / "preview.png"
    evidence: dict[str, Any] = {"generated": False, "error": ""}
    if not preview_html.exists():
        evidence["error"] = "preview.html missing"
        return evidence
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100}, device_scale_factor=1)
            page.goto(preview_html.resolve().as_uri(), wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(500)
            body_text_len = page.locator("body").inner_text(timeout=5000)
            element_count = page.locator("body *").count()
            page.screenshot(path=str(preview_png), full_page=False)
            browser.close()
        evidence.update({"generated": True, "body_text_length": len(body_text_len), "element_count": element_count})
    except Exception as exc:
        evidence["error"] = f"{exc.__class__.__name__}: {exc}"
    return evidence


def template_report(item: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    structure_flags: list[str] = []
    normalized = ROOT / item.get("normalized_path", "")
    raw = ROOT / item.get("local_raw_path", "")
    index_html = normalized / "index.html"
    preview_html = normalized / "preview.html"
    preview_png = normalized / "preview.png"
    template_json = normalized / "template.json"
    page_schema = normalized / "page.schema.json"

    if not preview_png.exists() or preview_png.stat().st_size < MIN_PREVIEW_BYTES:
        generate_preview_png(normalized)

    html_text = safe_text(index_html)
    css = css_text(normalized)
    schema = read_json(page_schema) if page_schema.exists() else {}
    blocks = schema.get("blocks", [])
    checks = item.get("checks", {})
    assets = asset_count(normalized)
    preview_width, preview_height = png_dimensions(preview_png) if preview_png.exists() else (0, 0)
    sections = section_types(schema, checks)
    html_bytes = len(html_text.encode("utf-8"))
    css_bytes = len(css.encode("utf-8"))
    preview_bytes = preview_png.stat().st_size if preview_png.exists() else 0

    required_fields = ["id", "repo_url", "repo_name", "stars", "license", "last_commit", "framework", "category", "local_raw_path", "normalized_path", "source_path"]
    missing_fields = [field for field in required_fields if item.get(field) in {None, ""}]
    if missing_fields:
        errors.append(f"missing metadata: {', '.join(missing_fields)}")
    if not str(item.get("repo_url", "")).startswith("https://github.com/"):
        errors.append("not a real GitHub repo URL")
    if item.get("license") in {"", None, "unknown", "NOASSERTION"}:
        errors.append("missing or unknown license")
    if int(item.get("stars") or 0) < MIN_STARS and not item.get("approved"):
        errors.append(f"stars below threshold: {item.get('stars')}")
    if not raw.exists():
        errors.append("raw_path missing")
    if not normalized.exists():
        errors.append("normalized_path missing")
    if html_bytes < MIN_HTML_BYTES:
        errors.append(f"HTML below {MIN_HTML_BYTES} bytes")
    if css_bytes < MIN_CSS_BYTES:
        errors.append(f"CSS below {MIN_CSS_BYTES} bytes")
    if assets < MIN_ASSETS:
        errors.append(f"assets_count below {MIN_ASSETS}")
    if len(blocks) < MIN_BLOCKS:
        errors.append(f"blocks below {MIN_BLOCKS}")
    if not preview_html.exists():
        errors.append("preview.html missing")
    if not preview_png.exists():
        errors.append("preview.png missing")
    if preview_bytes < MIN_PREVIEW_BYTES:
        errors.append("preview.png too small or blank-like")
    if preview_width < MIN_PREVIEW_WIDTH or preview_height < MIN_PREVIEW_HEIGHT:
        errors.append("preview.png dimensions too small")
    if len(sections) < 5 or not all(name in sections for name in ["Header", "Hero", "Features", "CTA", "Footer"]):
        errors.append("missing required visual sections")
    if re.search(r"example\.com|github-real-[\w-]+\.example\.com", html_text, flags=re.I):
        errors.append("example.com/test domain pollution")
    if any(text.lower() in html_text.lower() for text in BAD_TEST_TEXT):
        errors.append("fake seed/test template text detected")
    if item.get("template_type") not in {"static_template", "builder_template"}:
        errors.append("invalid template_type")
    if item.get("template_type") == "static_template" and not schema.get("static_template"):
        errors.append("static_template metadata missing in page.schema.json")

    source_score = 0
    source_score += 25 if not missing_fields else max(0, 25 - len(missing_fields) * 4)
    source_score += 20 if str(item.get("repo_url", "")).startswith("https://github.com/") else 0
    source_score += 20 if item.get("license") not in {"", None, "unknown", "NOASSERTION"} else 0
    source_score += 20 if int(item.get("stars") or 0) >= MIN_STARS or item.get("approved") else 0
    source_score += 15 if raw.exists() and normalized.exists() else 0

    visual_score = 0
    visual_score += 15 if html_bytes >= MIN_HTML_BYTES else max(0, int(15 * html_bytes / MIN_HTML_BYTES))
    visual_score += 15 if css_bytes >= MIN_CSS_BYTES else max(0, int(15 * css_bytes / MIN_CSS_BYTES))
    visual_score += 15 if assets >= MIN_ASSETS else assets * 5
    visual_score += 25 if len(sections) >= 5 and all(name in sections for name in ["Header", "Hero", "Features", "CTA", "Footer"]) else len(sections) * 4
    visual_score += 20 if preview_png.exists() and preview_bytes >= MIN_PREVIEW_BYTES and preview_width >= MIN_PREVIEW_WIDTH and preview_height >= MIN_PREVIEW_HEIGHT else 0
    visual_score += 10 if len(blocks) >= MIN_BLOCKS else 0

    usability_score = 0
    usability_score += 25 if item.get("status") == "available" and item.get("can_use_in_builder") else 0
    usability_score += 20 if item.get("template_type") in {"static_template", "builder_template"} else 0
    usability_score += 20 if schema.get("blocks") and len(blocks) >= MIN_BLOCKS else 0
    usability_score += 15 if preview_html.exists() and preview_png.exists() else 0
    usability_score += 10 if not re.search(r"example\.com|github-real-[\w-]+\.example\.com", html_text, flags=re.I) else 0
    usability_score += 10 if not any(text.lower() in html_text.lower() for text in BAD_TEST_TEXT) else 0

    total_score = round(source_score * 0.32 + visual_score * 0.43 + usability_score * 0.25, 2)
    hard_fail = bool(errors)
    if hard_fail:
        status = "FAIL"
    elif total_score >= 90:
        status = "PASS"
    elif total_score >= 70:
        status = "PARTIAL_PASS"
    else:
        status = "FAIL"

    return {
        "template_id": item.get("id"),
        "name": item.get("name"),
        "repo_url": item.get("repo_url"),
        "repo_name": item.get("repo_name"),
        "stars": item.get("stars"),
        "license": item.get("license"),
        "last_commit": item.get("last_commit"),
        "framework": item.get("framework"),
        "category": item.get("category"),
        "raw_path": item.get("local_raw_path"),
        "normalized_path": item.get("normalized_path"),
        "source_path": item.get("source_path"),
        "template_type": item.get("template_type"),
        "html_bytes": html_bytes,
        "css_bytes": css_bytes,
        "assets_count": assets,
        "has_preview_html": preview_html.exists(),
        "has_preview_png": preview_png.exists(),
        "preview_png_bytes": preview_bytes,
        "preview_width": preview_width,
        "preview_height": preview_height,
        "sections_detected": sections,
        "structure_similarity_flags": structure_flags,
        "visual_score": min(100, visual_score),
        "source_score": min(100, source_score),
        "usability_score": min(100, usability_score),
        "total_score": total_score,
        "usable_in_ui": bool(item.get("status") == "available" and item.get("can_use_in_builder") and preview_png.exists()),
        "status": status,
        "errors": errors,
        "_html_signature": compact_structure(html_text),
        "_css_signature": re.sub(r"\s+", " ", css)[:50000],
        "_text_signature": visible_text_signature(html_text),
        "_section_signature": " ".join(sections),
    }


def stop_ports() -> None:
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-NetTCPConnection -LocalPort 8000,5173 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }",
        ],
        capture_output=True,
        text=True,
    )


def ui_acceptance(expected_ids: list[str]) -> dict[str, Any]:
    npm = shutil.which("npm.cmd") or shutil.which("npm") or "npm"
    env = os.environ.copy()
    env["GITHUB_MODE"] = "mock"
    env["CLOUDFLARE_MODE"] = "mock"
    processes: list[subprocess.Popen] = []
    evidence: dict[str, Any] = {
        "status": "FAIL",
        "api_templates_count": 0,
        "modal_template_cards": 0,
        "preview_images_visible": 0,
        "available_ids_missing_from_api": [],
        "available_ids_missing_from_ui": [],
        "applied_blocks_count": 0,
        "applied_sections": {},
        "errors": [],
    }
    try:
        stop_ports()
        processes = [
            subprocess.Popen(["python", "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env),
            subprocess.Popen([npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"], cwd=ROOT / "frontend", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env),
        ]
        for _ in range(120):
            try:
                if requests.get(f"{API}/system/health", timeout=2).status_code == 200 and requests.get(WEB, timeout=2).status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            evidence["errors"].append("servers did not start")
            return evidence

        api_items = requests.get(f"{API}/builder/templates", timeout=10).json().get("items", [])
        api_ids = {item.get("id") for item in api_items}
        evidence["api_templates_count"] = len(api_items)
        evidence["available_ids_missing_from_api"] = [item for item in expected_ids if item not in api_ids]

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1440, "height": 1100})
            page.goto(WEB, wait_until="domcontentloaded", timeout=30000)
            page.get_by_test_id("login-submit").click()
            page.wait_for_timeout(4700)
            page.locator("aside").get_by_role("button", name=re.compile("DIY|建站|Builder", re.I)).click()
            page.wait_for_timeout(800)
            page.get_by_test_id("choose-template-button").click()
            page.wait_for_timeout(1200)
            evidence["modal_template_cards"] = page.locator('[data-testid^="apply-template-"]').count()
            evidence["preview_images_visible"] = page.locator('[data-testid^="template-preview-"]').count()
            ui_ids = set(page.locator('[data-testid^="apply-template-"]').evaluate_all("(els) => els.map((el) => el.getAttribute('data-testid').replace('apply-template-', ''))"))
            evidence["available_ids_missing_from_ui"] = [item for item in expected_ids if item not in ui_ids]
            if expected_ids:
                first_id = expected_ids[0]
                page.get_by_test_id(f"apply-template-{first_id}").click()
                page.get_by_test_id("template-overwrite-button").click()
                page.wait_for_timeout(1000)
                evidence["applied_blocks_count"] = page.locator('[data-testid^="canvas-block-"]').count()
                evidence["applied_sections"] = {
                    "header": page.get_by_test_id("canvas-block-TopNav").count(),
                    "hero": page.get_by_test_id("canvas-block-Hero").count(),
                    "features": page.get_by_test_id("canvas-block-TrustBadge").count(),
                    "cta": page.get_by_test_id("canvas-block-CTASection").count(),
                    "footer": page.get_by_test_id("canvas-block-Footer").count(),
                }
            browser.close()
        if (
            evidence["api_templates_count"] >= len(expected_ids)
            and evidence["modal_template_cards"] >= len(expected_ids)
            and evidence["preview_images_visible"] >= len(expected_ids)
            and not evidence["available_ids_missing_from_api"]
            and not evidence["available_ids_missing_from_ui"]
            and evidence["applied_blocks_count"] >= 5
            and all(value >= 1 for value in evidence["applied_sections"].values())
        ):
            evidence["status"] = "PASS"
    except Exception as exc:
        evidence["errors"].append(f"{exc.__class__.__name__}: {exc}")
    finally:
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        stop_ports()
    return evidence


def main() -> None:
    if not INDEX.exists():
        raise SystemExit(f"missing template index: {INDEX}")
    items = read_json(INDEX).get("templates", [])
    reports = [template_report(item) for item in items]

    category_counts: dict[str, int] = {}
    for item in reports:
        category_counts[item["category"]] = category_counts.get(item["category"], 0) + 1

    high_similarity_pairs: list[dict[str, Any]] = []
    for i, left in enumerate(reports):
        for right in reports[i + 1 :]:
            html_ratio = difflib.SequenceMatcher(None, left["_html_signature"], right["_html_signature"]).ratio()
            css_ratio = difflib.SequenceMatcher(None, left["_css_signature"], right["_css_signature"]).ratio()
            text_ratio = difflib.SequenceMatcher(None, left["_text_signature"], right["_text_signature"]).ratio()
            section_ratio = difflib.SequenceMatcher(None, left["_section_signature"], right["_section_signature"]).ratio()
            flags = []
            if html_ratio > MAX_HTML_STRUCTURE_SIMILARITY:
                flags.append("html_structure")
            if css_ratio > 0.985:
                flags.append("css")
            if text_ratio > MAX_TEXT_SIMILARITY:
                flags.append("text")
            if section_ratio > MAX_SECTION_SIMILARITY:
                flags.append("sections")
            if "html_structure" in flags and ("text" in flags or "sections" in flags):
                high_similarity_pairs.append(
                    {
                        "left": left["template_id"],
                        "right": right["template_id"],
                        "html_structure_similarity": round(html_ratio, 4),
                        "css_similarity": round(css_ratio, 4),
                        "text_similarity": round(text_ratio, 4),
                        "section_similarity": round(section_ratio, 4),
                        "flags": flags,
                    }
                )

    for pair in high_similarity_pairs:
        for item in reports:
            if item["template_id"] in {pair["left"], pair["right"]}:
                item["structure_similarity_flags"].append(pair)
                if "high similarity with another template" not in item["errors"]:
                    item["errors"].append("high similarity with another template")
                item["status"] = "FAIL"

    required_mix = {
        "landing_saas_agency": category_counts.get("landing", 0) + category_counts.get("saas", 0) + category_counts.get("agency", 0) >= 3,
        "blog": category_counts.get("blog", 0) >= 2,
        "portfolio": category_counts.get("portfolio", 0) >= 2,
        "docs": category_counts.get("docs", 0) >= 1,
        "ecommerce": category_counts.get("ecommerce", 0) >= 2,
        "total": len(reports) >= 10,
    }
    ui = ui_acceptance([item["template_id"] for item in reports if item["status"] in {"PASS", "PARTIAL_PASS"}])
    if ui["status"] != "PASS":
        for item in reports:
            item["usable_in_ui"] = False
            item["errors"].append("UI template library acceptance failed")
            item["status"] = "FAIL"

    cleaned = []
    for item in reports:
        cleaned.append({key: value for key, value in item.items() if not key.startswith("_")})
    pass_count = len([item for item in cleaned if item["status"] == "PASS"])
    partial_count = len([item for item in cleaned if item["status"] == "PARTIAL_PASS"])
    fail_count = len([item for item in cleaned if item["status"] == "FAIL"])
    average_score = round(sum(item["total_score"] for item in cleaned) / max(1, len(cleaned)), 2)
    if fail_count or high_similarity_pairs or not all(required_mix.values()) or ui["status"] != "PASS":
        summary_status = "FAIL"
    elif partial_count:
        summary_status = "PARTIAL_PASS"
    else:
        summary_status = "PASS"

    output = {
        "status": summary_status,
        "total_templates": len(cleaned),
        "passed_templates": pass_count,
        "partial_templates": partial_count,
        "failed_templates": fail_count,
        "average_score": average_score,
        "category_counts": category_counts,
        "required_mix": required_mix,
        "ui_acceptance": ui,
        "similarity_thresholds": {
            "html_structure": MAX_HTML_STRUCTURE_SIMILARITY,
            "text": MAX_TEXT_SIMILARITY,
            "sections": MAX_SECTION_SIMILARITY,
        },
        "high_similarity_pairs": high_similarity_pairs,
        "templates": cleaned,
    }
    REPORT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_COPY.parent.mkdir(parents=True, exist_ok=True)
    REPORT_COPY.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": summary_status,
                "report": str(REPORT),
                "total_templates": len(cleaned),
                "passed_templates": pass_count,
                "partial_templates": partial_count,
                "failed_templates": fail_count,
                "average_score": average_score,
                "ui_status": ui["status"],
                "high_similarity_pairs": len(high_similarity_pairs),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if summary_status == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
