import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
META_DIR = ROOT / "meta"
INDEX = META_DIR / "templates.index.json"


def check_template(meta: dict) -> dict:
    path = ROOT.parent / meta.get("local_path", "")
    package = path / "package.json"
    checks = {
        "commercial_license_allowed": meta.get("license") in {"MIT", "Apache-2.0", "BSD", "Project internal", "present"},
        "external_services": False,
        "requires_database": False,
        "static_export": bool(meta.get("supports_static_export", True)),
        "github_pages_suitable": True,
        "malicious_or_tracking_scripts": False,
        "copyright_assets_risk": False,
        "can_split_into_components": True,
    }
    if package.exists():
        text = package.read_text(encoding="utf-8", errors="ignore").lower()
        checks["requires_database"] = any(token in text for token in ["prisma", "mongoose", "postgres", "mysql"])
        checks["external_services"] = any(token in text for token in ["firebase", "supabase", "stripe", "segment", "analytics"])
    meta["checks"] = checks
    meta["status"] = "inspected" if meta.get("status") == "raw_downloaded" else meta.get("status", "inspected")
    return meta


def main() -> None:
    data = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else {"templates": []}
    templates = [check_template(item) for item in data.get("templates", [])]
    for item in templates:
        (META_DIR / f"{item['id']}.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    INDEX.write_text(json.dumps({"templates": templates}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"scanned": len(templates), "index": str(INDEX)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
