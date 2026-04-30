import json
import os
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any

import requests

from core.env_loader import load_env_file


ROOT = Path(__file__).resolve().parent
DB = ROOT / "storage" / "site_factory_os.db"
REPORTS = ROOT / "reports"
API = "http://127.0.0.1:8000/api/v1"
PAGES_MAX_WAIT_SECONDS = 60
PAGES_CHECK_INTERVAL_SECONDS = 5


def log(message: str, **details: Any) -> None:
    if details:
        safe_details = " ".join(f"{key}={value}" for key, value in details.items())
        print(f"{message} {safe_details}", flush=True)
    else:
        print(message, flush=True)


def response_message(response: requests.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            if "message" in data:
                return str(data["message"])
            error = data.get("error")
            if isinstance(error, dict):
                return str(error.get("message") or error.get("error_code") or "")
    except ValueError:
        pass
    return response.reason or ""


def stop_ports() -> None:
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }",
        ],
        capture_output=True,
        text=True,
    )


def api(path: str, *, token: str = "", method: str = "GET", payload: dict | None = None, timeout: int = 10) -> requests.Response:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return requests.request(method, f"{API}{path}", json=payload, headers=headers, timeout=timeout)


def db_exec(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql, params)
        conn.commit()
        try:
            return [dict(row) for row in cur.fetchall()]
        except sqlite3.ProgrammingError:
            return []


def load_template() -> dict:
    path = ROOT / "template_library" / "normalized" / "landing" / "static_landing_startbootstrap_landing_page" / "page.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    started_at = time.time()
    load_env_file()
    REPORTS.mkdir(exist_ok=True)
    required = ["GITHUB_TOKEN", "GITHUB_OWNER"]
    missing = [name for name in required if not os.getenv(name)]
    report: dict[str, Any] = {
        "status": "FAIL",
        "github_mode": os.getenv("GITHUB_MODE", "mock"),
        "required_env": ["GITHUB_TOKEN", "GITHUB_OWNER", "GITHUB_DEFAULT_BRANCH", "GITHUB_REPO_PREFIX", "GITHUB_VISIBILITY", "GITHUB_API_BASE"],
        "missing_env": missing,
        "github_pages_url": "",
        "api_evidence": [],
        "seo_files_generated": [],
        "deploy_logs": "",
        "url_probe": None,
        "failed_items": [],
    }
    report["execution_log"] = []

    def step(message: str, **details: Any) -> None:
        report["execution_log"].append({"time": round(time.time() - started_at, 2), "message": message, **details})
        log(message, **details)

    step("[Start] GitHub Pages real acceptance")
    if os.getenv("GITHUB_MODE") != "real":
        report["failed_items"].append({"feature": "github_real_mode", "error": "GITHUB_MODE must be real"})
        (REPORTS / "github_pages_real_acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "FAIL", "reason": "GITHUB_MODE must be real", "report": str(REPORTS / "github_pages_real_acceptance.json")}, ensure_ascii=False, indent=2), flush=True)
        return
    if missing:
        report["failed_items"].append({"feature": "github_env", "error": "missing required env", "missing_env": missing})
        (REPORTS / "github_pages_real_acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "FAIL", "reason": "missing env", "missing_env": missing, "report": str(REPORTS / "github_pages_real_acceptance.json")}, ensure_ascii=False, indent=2), flush=True)
        return

    backup = ""
    proc: subprocess.Popen | None = None
    try:
        step("[Setup] Stop existing API server on port 8000")
        stop_ports()
        if DB.exists():
            backup_path = REPORTS / f"site_factory_os_before_github_real_{int(time.time())}.db"
            shutil.copy2(DB, backup_path)
            backup = str(backup_path)
            DB.unlink()
            step("[Setup] Backed up and reset SQLite DB", backup=backup)
        env = os.environ.copy()
        step("[Setup] Starting FastAPI server")
        proc = subprocess.Popen(["python", "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
        for attempt in range(40):
            try:
                response = api("/system/health", timeout=3)
                if response.status_code == 200:
                    step("[Setup] API server is healthy", attempt=attempt + 1)
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("API server did not start")

        stamp = str(int(time.time()))
        step("[Auth] Login as test super admin")
        login_response = api("/auth/login", method="POST", payload={"username": "candy2000", "password": "candy2000"}, timeout=10)
        report["api_evidence"].append({"api": "POST /auth/login", "status_code": login_response.status_code})
        step("[Auth] Login response", status_code=login_response.status_code)
        login_response.raise_for_status()
        login = login_response.json()
        token = login["token"]
        domain = f"github-real-{stamp}.example.com"
        site_payload = {"request_id": f"real_site_{stamp}", "alias": f"GitHub Real {stamp}", "domain": domain, "site_type": "landing", "template_id": "landing1"}
        step("[Site] Create site", domain=domain)
        site_response = api("/sites", token=token, method="POST", payload=site_payload, timeout=60)
        report["api_evidence"].append({"api": "POST /sites", "status_code": site_response.status_code})
        step("[Site] Create site response", status_code=site_response.status_code, github_message=response_message(site_response))
        site_response.raise_for_status()
        site_id = site_response.json()["site"]["site_id"]
        db_exec("UPDATE domains SET status='ns_verified', ssl_status='active' WHERE site_id=?", (site_id,))
        step("[DNS] Marked test domain ready in local SQLite", site_id=site_id)

        layout = load_template()
        step("[Page] Create DIY page from normalized template")
        page_response = api("/sites/%s/pages" % site_id, token=token, method="POST", payload={"request_id": f"real_page_{stamp}", "slug": "home", "page_type": "custom", "layout": layout}, timeout=10)
        report["api_evidence"].append({"api": "POST /sites/{site_id}/pages", "status_code": page_response.status_code})
        step("[Page] Create page response", status_code=page_response.status_code, github_message=response_message(page_response))
        page_response.raise_for_status()
        page_id = page_response.json()["page"]["page_id"]
        step("[Page] Publish page to local dist")
        publish_response = api(f"/pages/{page_id}/publish", token=token, method="POST", payload={"request_id": f"real_publish_{stamp}"}, timeout=30)
        report["api_evidence"].append({"api": "POST /pages/{page_id}/publish", "status_code": publish_response.status_code})
        step("[Page] Publish response", status_code=publish_response.status_code, github_message=response_message(publish_response))
        publish_response.raise_for_status()

        seo_title = f"GitHub Pages SEO {stamp}"
        seo_desc = "Real GitHub Pages deployment with SEO meta, hreflang, sitemap, and robots."
        step("[SEO] Save SEO title, description, and slug")
        seo_response = api(f"/sites/{site_id}/seo", token=token, method="PATCH", payload={"request_id": f"real_seo_{stamp}", "language_code": "en", "title": seo_title, "description": seo_desc, "slug": "/"}, timeout=10)
        report["api_evidence"].append({"api": "PATCH /sites/{site_id}/seo", "status_code": seo_response.status_code})
        step("[SEO] Save SEO response", status_code=seo_response.status_code, github_message=response_message(seo_response))
        seo_response.raise_for_status()
        step("[GitHub] Deploy start: create repo, push contents, enable Pages", site_id=site_id)
        deploy_response = api("/deploy/github", token=token, method="POST", payload={"request_id": f"real_deploy_{stamp}", "site_id": site_id}, timeout=45)
        report["api_evidence"].append({"api": "POST /deploy/github", "status_code": deploy_response.status_code})
        step("[GitHub] Deploy response", status_code=deploy_response.status_code, github_message=response_message(deploy_response))
        deploy_response.raise_for_status()
        deploy_body = deploy_response.json()
        deployment = deploy_body.get("deployment", {})
        repo_name = deployment.get("repo_name", "")
        report["backend_live_url"] = deploy_body.get("github_pages_url") or deployment.get("live_url", "")
        default_pages_url = f"https://{os.getenv('GITHUB_OWNER')}.github.io/{repo_name}/" if repo_name else ""
        report["github_pages_url"] = default_pages_url or report["backend_live_url"]
        step("[GitHub] Repo created or reused", repo=repo_name or "<unknown>")
        step("[GitHub] Contents pushed", commit_id=deployment.get("commit_id", "<unknown>"))
        step("[GitHub] Pages enabled", backend_url=report["backend_live_url"] or "<empty>")
        step("[GitHub] Pages URL selected for probe", url=report["github_pages_url"] or "<empty>")
        logs_response = api(f"/deploy/logs/{site_id}", token=token, timeout=10)
        report["api_evidence"].append({"api": "GET /deploy/logs/{site_id}", "status_code": logs_response.status_code})
        step("[GitHub] Deploy logs response", status_code=logs_response.status_code, github_message=response_message(logs_response))
        report["deploy_logs"] = json.dumps(logs_response.json(), ensure_ascii=False)[:4000] if logs_response.ok else logs_response.text[:1000]

        dist = ROOT / "generated_sites" / site_id / "dist"
        files = [dist / "index.html", dist / "sitemap.xml", dist / "robots.txt"]
        report["seo_files_generated"] = [str(path) for path in files if path.exists()]
        index_text = (dist / "index.html").read_text(encoding="utf-8") if (dist / "index.html").exists() else ""
        sitemap_text = (dist / "sitemap.xml").read_text(encoding="utf-8") if (dist / "sitemap.xml").exists() else ""
        forbidden_domain = f"github-real-{stamp}.example.com"
        seo_ok = (
            all(token_text in index_text for token_text in ["<title>", seo_title, seo_desc, "rel=\"canonical\"", "og:title", "og:description"])
            and forbidden_domain not in index_text
            and forbidden_domain not in sitemap_text
            and "example.com" not in sitemap_text
        )
        if not seo_ok:
            report["failed_items"].append({"feature": "seo_output", "error": "SEO tags or slug missing from generated files"})
            step("[SEO] Generated SEO files check failed")
        else:
            step("[SEO] Generated SEO files check passed", files=len(report["seo_files_generated"]))

        url_ok = False
        if report["github_pages_url"]:
            remaining_budget = PAGES_MAX_WAIT_SECONDS
            max_attempts = max(1, int(remaining_budget // PAGES_CHECK_INTERVAL_SECONDS) or 1)
            step("[Pages Check] budget", remaining_seconds=round(remaining_budget, 2), max_attempts=max_attempts)
            for attempt in range(max_attempts):
                step("[Pages Check] attempt", attempt=attempt + 1, max_attempts=max_attempts, url=report["github_pages_url"])
                try:
                    probe = requests.get(report["github_pages_url"], timeout=10)
                    report["url_probe"] = {"status_code": probe.status_code, "url": report["github_pages_url"]}
                    step("[Pages Check] response", status_code=probe.status_code, github_message=response_message(probe))
                    if probe.status_code == 200 and ("Site Factory" in probe.text or seo_title in probe.text or "Generate more leads" in probe.text):
                        url_ok = True
                        step("[Pages Check] Pages is live", url=report["github_pages_url"])
                        break
                except requests.RequestException as exc:
                    report["url_probe"] = {"error": exc.__class__.__name__, "url": report["github_pages_url"]}
                    step("[Pages Check] request failed", error=exc.__class__.__name__)
                if attempt < max_attempts - 1:
                    time.sleep(PAGES_CHECK_INTERVAL_SECONDS)
        else:
            step("[Pages Check] skipped because Pages URL is empty")
        if not url_ok:
            report["failed_items"].append({"feature": "github_pages_url_probe", "error": f"GitHub Pages URL did not return expected page within {PAGES_MAX_WAIT_SECONDS}s", "url": report["github_pages_url"], "last_probe": report["url_probe"]})

        report["db_backup_before_clean_run"] = backup
        report["duration_seconds"] = round(time.time() - started_at, 2)
        report["status"] = "PASS" if not report["failed_items"] else "FAIL"
        (REPORTS / "github_pages_real_acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": report["status"], "github_pages_url": report["github_pages_url"], "failed": len(report["failed_items"]), "failed_items": report["failed_items"], "duration_seconds": report["duration_seconds"], "report": str(REPORTS / "github_pages_real_acceptance.json")}, ensure_ascii=False, indent=2), flush=True)
    except Exception as exc:
        report["db_backup_before_clean_run"] = backup
        report["duration_seconds"] = round(time.time() - started_at, 2)
        try:
            report["latest_task_errors"] = db_exec("SELECT task_type, status, error_code, error_message, result_json FROM tasks ORDER BY created_at DESC LIMIT 5")
        except Exception:
            report["latest_task_errors"] = []
        safe_error: dict[str, Any] = {"feature": "github_real_acceptance", "error": exc.__class__.__name__}
        if report.get("latest_task_errors"):
            latest = report["latest_task_errors"][0]
            safe_error["error_code"] = latest.get("error_code")
            safe_error["message"] = latest.get("error_message")
            try:
                safe_error["github_api_error"] = json.loads(latest.get("result_json") or "{}")
            except json.JSONDecodeError:
                safe_error["github_api_error"] = {}
        report["failed_items"].append(safe_error)
        (REPORTS / "github_pages_real_acceptance.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "FAIL", "error": safe_error, "duration_seconds": report["duration_seconds"], "github_pages_url": report["github_pages_url"], "report": str(REPORTS / "github_pages_real_acceptance.json")}, ensure_ascii=False, indent=2), flush=True)
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        stop_ports()


if __name__ == "__main__":
    main()
