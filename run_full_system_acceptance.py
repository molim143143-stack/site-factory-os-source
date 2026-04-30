import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"


def run(name: str, command: list[str], report_file: str) -> dict:
    print(f"[Full Acceptance] {name}", flush=True)
    proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=180)
    report_path = REPORTS / report_file
    data = {}
    if report_path.exists():
        data = json.loads(report_path.read_text(encoding="utf-8"))
    else:
        data = {"status": "FAIL", "failed": ["missing_report"]}
    return {
        "status": data.get("status", "FAIL"),
        "report": str(report_path),
        "stdout_tail": proc.stdout[-1500:],
        "stderr_tail": proc.stderr[-1500:],
        "returncode": proc.returncode,
        "failed": data.get("failed") or data.get("failed_items") or [],
    }


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    checks = {
        "template_library": run("template library", [sys.executable, "run_template_library_acceptance.py"], "template_library_acceptance.json"),
        "publish_dist": run("publish dist", [sys.executable, "run_publish_dist_acceptance.py"], "publish_dist_acceptance.json"),
        "seo": run("seo", [sys.executable, "run_seo_acceptance.py"], "seo_acceptance.json"),
        "github_deploy": run("github real deploy", [sys.executable, "run_github_pages_real_acceptance.py"], "github_pages_real_acceptance.json"),
        "domain_isolation": run("domain isolation", [sys.executable, "run_domain_isolation_acceptance.py"], "domain_isolation_acceptance.json"),
        "batch_publish": run("batch publish", [sys.executable, "run_batch_publish_acceptance.py"], "batch_publish_acceptance.json"),
        "secret_scan": run("secret scan", [sys.executable, "run_secret_scan.py"], "secret_scan.json"),
    }
    checks["diy_builder"] = checks["template_library"]
    checks["domain_modes"] = checks["domain_isolation"]
    checks["cloudflare_dns"] = {
        "status": "PARTIAL",
        "report": "",
        "failed": ["real_cloudflare_token_not_verified", "zone_ownership_api_not_enforced"],
    }
    checks["ui_callback"] = {
        "status": "PARTIAL",
        "report": str(ROOT / "frontend" / "src" / "pages" / "Sites.tsx"),
        "failed": ["full_playwright_ui_callback_audit_not_rerun"],
    }
    checks["telegram_notify"] = {
        "status": "FAIL",
        "report": str(ROOT / "telegram_bot.py"),
        "failed": ["deploy_completion_notification_not_wired"],
    }
    failed_modules = {name: item for name, item in checks.items() if item.get("status") not in {"PASS"}}
    report = {
        "status": "PASS" if not failed_modules else "PARTIAL_FAIL",
        "modules": checks,
        "failed_modules": failed_modules,
        "hard_failures_checked": {
            "dist_example_com": "covered by publish_dist and seo",
            "github_io_redirect_to_example": "covered by github_deploy URL probe and report",
            "token_leak": "covered by secret_scan",
            "template_single_block": "covered by template_library",
        },
    }
    (REPORTS / "final_full_system_acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "failed_modules": list(failed_modules), "report": str(REPORTS / "final_full_system_acceptance.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
