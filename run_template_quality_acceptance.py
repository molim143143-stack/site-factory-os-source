import difflib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "template_library" / "meta" / "templates.index.json"
REPORT = ROOT / "template_library_quality_report.json"
REPORT_COPY = ROOT / "reports" / "template_library_quality_report.json"
MIN_HTML_BYTES = 8 * 1024
MIN_CSS_BYTES = 5 * 1024
MIN_BLOCKS = 5
MIN_STARS = 100
MAX_SIMILARITY = 0.92


BAD_TEST_TEXT = [
    "Site Factory Neon Landing",
    "AI website factory control deck",
    "testing template",
    "fake template",
    "Landing Page / Explore",
]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore") if path.exists() else ""


def compact_html(text: str) -> str:
    text = re.sub(r"<script\b.*?</script>", "", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", "", text, flags=re.I | re.S)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:50000]


def record_check(checks: list[dict[str, Any]], name: str, ok: bool, evidence: Any) -> None:
    checks.append({"check": name, "status": "PASS" if ok else "FAIL", "evidence": evidence})


def template_report(item: dict[str, Any]) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    normalized = ROOT / item.get("normalized_path", "")
    raw = ROOT / item.get("local_raw_path", "")
    index_html = normalized / "index.html"
    preview_html = normalized / "preview.html"
    template_json = normalized / "template.json"
    page_schema = normalized / "page.schema.json"
    html_text = safe_text(index_html)
    css_text = "\n".join(safe_text(path) for path in (normalized / "assets" / "site").rglob("*.css")) if (normalized / "assets" / "site").exists() else safe_text(normalized / "style.css")
    schema = read_json(page_schema) if page_schema.exists() else {}
    blocks = schema.get("blocks", [])
    structure = item.get("checks", {})

    record_check(checks, "real_github_repo_url", item.get("repo_url", "").startswith("https://github.com/"), item.get("repo_url", ""))
    record_check(checks, "repo_metadata_present", all(item.get(key) for key in ["repo_name", "framework", "category", "last_commit", "source_path", "local_raw_path", "normalized_path"]), {key: item.get(key) for key in ["repo_name", "framework", "category", "last_commit", "source_path", "local_raw_path", "normalized_path"]})
    record_check(checks, "stars_or_approved", int(item.get("stars") or 0) >= MIN_STARS or bool(item.get("approved")), {"stars": item.get("stars"), "approved": item.get("approved")})
    record_check(checks, "license_present", item.get("license") not in {"", None, "unknown", "NOASSERTION"}, item.get("license"))
    record_check(checks, "raw_path_exists", raw.exists(), str(raw))
    record_check(checks, "normalized_files_exist", all(path.exists() for path in [index_html, preview_html, template_json, page_schema]), [str(index_html), str(preview_html), str(template_json), str(page_schema)])
    record_check(checks, "preview_exists", preview_html.exists() or (normalized / "preview.config.json").exists(), str(preview_html))
    record_check(checks, "template_type_valid", item.get("template_type") in {"static_template", "builder_template"}, item.get("template_type"))
    record_check(checks, "html_length", len(html_text.encode("utf-8")) >= MIN_HTML_BYTES, {"length": len(html_text.encode("utf-8")), "minimum": MIN_HTML_BYTES})
    record_check(checks, "css_length", len(css_text.encode("utf-8")) >= MIN_CSS_BYTES, {"length": len(css_text.encode("utf-8")), "minimum": MIN_CSS_BYTES})
    record_check(checks, "blocks_count", len(blocks) >= MIN_BLOCKS, {"blocks": len(blocks), "minimum": MIN_BLOCKS})
    record_check(checks, "has_header_hero_features_cta_footer", all(structure.get(name) for name in ["header", "hero", "features", "cta", "footer"]), {name: structure.get(name) for name in ["header", "hero", "features", "cta", "footer"]})
    record_check(checks, "full_html_document", all(token in html_text.lower() for token in ["<html", "<body", "</html>"]), {"has_html": "<html" in html_text.lower(), "has_body": "<body" in html_text.lower()})
    record_check(checks, "no_example_or_test_domain", not re.search(r"example\.com|github-real-[\w-]+\.example\.com", html_text, flags=re.I), "example.com scan")
    record_check(checks, "no_fake_seed_text", not any(text.lower() in html_text.lower() for text in BAD_TEST_TEXT), BAD_TEST_TEXT)

    status = "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL"
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "repo_url": item.get("repo_url"),
        "repo_name": item.get("repo_name"),
        "stars": item.get("stars"),
        "license": item.get("license"),
        "framework": item.get("framework"),
        "category": item.get("category"),
        "last_commit": item.get("last_commit"),
        "source_path": item.get("source_path"),
        "local_raw_path": item.get("local_raw_path"),
        "normalized_path": item.get("normalized_path"),
        "template_type": item.get("template_type"),
        "status": status,
        "checks": checks,
        "html_signature": compact_html(html_text),
    }


def main() -> None:
    if not INDEX.exists():
        raise SystemExit(f"missing template index: {INDEX}")
    items = read_json(INDEX).get("templates", [])
    reports = [template_report(item) for item in items]
    category_counts: dict[str, int] = {}
    for item in reports:
        category_counts[item["category"]] = category_counts.get(item["category"], 0) + 1

    similarity_pairs: list[dict[str, Any]] = []
    for i, left in enumerate(reports):
        for right in reports[i + 1 :]:
            ratio = difflib.SequenceMatcher(None, left["html_signature"], right["html_signature"]).ratio()
            if ratio > MAX_SIMILARITY:
                similarity_pairs.append({"left": left["id"], "right": right["id"], "similarity": round(ratio, 4)})

    required_mix = {
        "landing_saas_agency": category_counts.get("landing", 0) + category_counts.get("saas", 0) + category_counts.get("agency", 0) >= 3,
        "blog": category_counts.get("blog", 0) >= 2,
        "portfolio": category_counts.get("portfolio", 0) >= 2,
        "docs": category_counts.get("docs", 0) >= 1,
        "ecommerce": category_counts.get("ecommerce", 0) >= 2,
        "total": len(reports) >= 10,
    }
    failed_templates = [item for item in reports if item["status"] != "PASS"]
    summary_status = "PASS" if not failed_templates and not similarity_pairs and all(required_mix.values()) else "FAIL"
    output = {
        "status": summary_status,
        "total_templates": len(reports),
        "passed_templates": len(reports) - len(failed_templates),
        "failed_templates": len(failed_templates),
        "category_counts": category_counts,
        "required_mix": required_mix,
        "similarity_threshold": MAX_SIMILARITY,
        "high_similarity_pairs": similarity_pairs,
        "templates": [{key: value for key, value in item.items() if key != "html_signature"} for item in reports],
    }
    REPORT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_COPY.parent.mkdir(parents=True, exist_ok=True)
    REPORT_COPY.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": summary_status, "report": str(REPORT), "total_templates": len(reports), "failed_templates": len(failed_templates), "high_similarity_pairs": len(similarity_pairs)}, ensure_ascii=False, indent=2))
    if summary_status != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
