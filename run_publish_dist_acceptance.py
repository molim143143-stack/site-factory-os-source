import json
import os
import shutil
import sqlite3
import time
from pathlib import Path


os.environ.setdefault("GITHUB_MODE", "mock")
os.environ.setdefault("CLOUDFLARE_MODE", "mock")

from config import DB_PATH  # noqa: E402
from core.database import SessionLocal, init_db  # noqa: E402
from core.models import Page, SeoRecord, Site  # noqa: E402
from core.site_manager import SiteManager  # noqa: E402
from core.template_engine import TemplateEngine  # noqa: E402
from core.utils import new_id, now_iso, to_json  # noqa: E402


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"


def load_template() -> dict:
    path = ROOT / "template_library" / "normalized" / "landing" / "static_landing_startbootstrap_landing_page" / "page.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    backup = ""
    if DB_PATH.exists():
        backup_path = REPORTS / f"site_factory_os_before_publish_dist_{int(time.time())}.db"
        shutil.copy2(DB_PATH, backup_path)
        backup = str(backup_path)
        DB_PATH.unlink()
    init_db()
    db = SessionLocal()
    try:
        now = now_iso()
        stamp = str(int(time.time()))
        site = SiteManager().create_site(
            db,
            domain=f"publish-{stamp}.example.com",
            alias=f"Publish Dist {stamp}",
            site_type="landing",
            template_id="landing1",
            trace_id=new_id("trace"),
            request_id=f"publish_dist_{stamp}",
            task_id=new_id("task"),
        )
        layout = load_template()
        page = Page(page_id=new_id("page"), site_id=site.site_id, page_type="custom", slug="home", status="published", layout_json=to_json(layout), created_at=now, updated_at=now, published_at=now)
        db.add(page)
        db.add(SeoRecord(seo_id=new_id("seo"), site_id=site.site_id, entity_type="site", entity_id=site.site_id, language_code="en", title="Publish Dist SEO", description="Clean generated static output.", slug="/", created_at=now, updated_at=now))
        db.commit()
        files = TemplateEngine().render_site(db, site.site_id)
        dist = ROOT / "generated_sites" / site.site_id / "dist"
        index = dist / "index.html"
        sitemap = dist / "sitemap.xml"
        robots = dist / "robots.txt"
        style = dist / "style.css"
        all_text = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in dist.rglob("*") if path.is_file())
        index_text = index.read_text(encoding="utf-8", errors="ignore") if index.exists() else ""
        report = {
            "status": "PASS",
            "site_id": site.site_id,
            "dist": str(dist),
            "files": sorted([str(path.relative_to(dist)).replace("\\", "/") for path in dist.rglob("*") if path.is_file()]),
            "checks": {
                "required_files": all(path.exists() for path in [index, sitemap, robots, style]),
                "full_website_sections": all(token in index_text for token in ["sfs-topnav", "sfs-hero", "sfs-trust", "sfs-cta", "sfs-footer"]),
                "no_example_com": "example.com" not in all_text,
                "no_github_real_slug": "github-real-" not in all_text,
                "style_linked": 'href="/style.css"' in index_text or 'href="style.css"' in index_text,
                "not_ok_stub": index_text.strip().lower() not in {"ok", "<html>ok</html>"},
                "file_count": len(files),
            },
            "db_backup_before_clean_run": backup,
        }
        failed = [key for key, value in report["checks"].items() if value is False]
        report["failed"] = failed
        report["status"] = "PASS" if not failed else "FAIL"
        (REPORTS / "publish_dist_acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": report["status"], "failed": failed, "report": str(REPORTS / "publish_dist_acceptance.json")}, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    main()
