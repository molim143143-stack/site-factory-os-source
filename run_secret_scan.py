import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"
TOKEN_RE = re.compile("|".join([r"gh" + r"p_", r"github" + r"_pat_", r"Authorization:\s*token", r"CLOUDFLARE" + r"_API" + r"_TOKEN\s*="]), re.I)
EXCLUDED_PARTS = {
    ".env",
    "reports",
    "storage",
    "generated_sites",
    "node_modules",
    "venv",
    "__pycache__",
    "dist",
    "logs",
    ".git",
}


def excluded(path: Path) -> bool:
    parts = set(path.relative_to(ROOT).parts)
    return bool(parts & EXCLUDED_PARTS) or path.suffix in {".db", ".pyc", ".zip"}


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    matches = []
    checked = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or excluded(path):
            continue
        if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".json", ".md", ".txt", ".css", ".html", ".yml", ".yaml"}:
            continue
        checked += 1
        try:
            for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if TOKEN_RE.search(line):
                    matches.append({"path": str(path), "line": lineno})
        except OSError:
            continue
    report = {
        "status": "PASS" if not matches else "FAIL",
        "checked_files": checked,
        "excluded": sorted(EXCLUDED_PARTS),
        "matches": matches,
        "package_exclusion_required": sorted(EXCLUDED_PARTS | {"*.db", "*.pyc", "*.zip"}),
    }
    (REPORTS / "secret_scan.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "matches": len(matches), "report": str(REPORTS / "secret_scan.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
