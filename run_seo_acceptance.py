import json
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"


def latest_dist() -> Path | None:
    roots = sorted((ROOT / "generated_sites").glob("*/dist"), key=lambda p: p.stat().st_mtime, reverse=True)
    return roots[0] if roots else None


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    dist = latest_dist()
    report = {"status": "FAIL", "dist": str(dist) if dist else "", "checks": {}, "failed": []}
    if not dist:
        report["failed"].append("missing_dist")
    else:
        index = dist / "index.html"
        sitemap = dist / "sitemap.xml"
        robots = dist / "robots.txt"
        all_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in dist.rglob("*") if path.is_file())
        index_text = index.read_text(encoding="utf-8", errors="ignore") if index.exists() else ""
        sitemap_text = sitemap.read_text(encoding="utf-8", errors="ignore") if sitemap.exists() else ""
        robots_text = robots.read_text(encoding="utf-8", errors="ignore") if robots.exists() else ""
        report["checks"] = {
            "title": "<title>" in index_text,
            "description": 'name="description"' in index_text,
            "canonical": 'rel="canonical"' in index_text,
            "open_graph": "og:title" in index_text and "og:description" in index_text and "og:url" in index_text,
            "sitemap_exists": sitemap.exists() and "<urlset" in sitemap_text,
            "robots_exists": robots.exists() and "Sitemap:" in robots_text,
            "no_example_com": "example.com" not in all_text,
            "no_github_real_slug": "github-real-" not in all_text,
            "sitemap_uses_github_pages": "github.io" in sitemap_text,
        }
        report["failed"] = [key for key, value in report["checks"].items() if not value]
    report["status"] = "PASS" if not report["failed"] else "FAIL"
    report["checked_at"] = int(time.time())
    (REPORTS / "seo_acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failed": report["failed"], "report": str(REPORTS / "seo_acceptance.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
