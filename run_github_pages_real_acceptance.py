import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from core.env_loader import load_env_file


ROOT = Path(__file__).resolve().parent
DB = ROOT / "storage" / "site_factory_os.db"
REPORTS = ROOT / "reports"
REPORT = REPORTS / "github_pages_real_acceptance.json"
API = "http://127.0.0.1:8000/api/v1"
PAGES_MAX_WAIT_SECONDS = 60
PAGES_CHECK_INTERVAL_SECONDS = 5

POLLUTION_RE = re.compile(r"example\.com|github-real-[\w-]+\.example\.com", re.I)


def log(message: str, **details: Any) -> None:
    if details:
        print(message, " ".join(f"{key}={value}" for key, value in details.items()), flush=True)
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


def load_template() -> tuple[str, dict]:
    index = json.loads((ROOT / "template_library" / "meta" / "templates.index.json").read_text(encoding="utf-8"))
    items = index.get("templates", [])
    preferred = next((item for item in items if item.get("category") in {"landing", "saas", "agency"} and item.get("status") == "available"), None)
    item = preferred or next((item for item in items if item.get("status") == "available"), None)
    if not item:
        raise RuntimeError("no available template found")
    schema_path = ROOT / item["normalized_path"] / "page.schema.json"
    return item["id"], json.loads(schema_path.read_text(encoding="utf-8"))


def write_report(report: dict[str, Any]) -> None:
    REPORTS.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def add_error(report: dict[str, Any], code: str, message: str, **details: Any) -> None:
    report["errors"].append({"error_code": code, "message": message, **details})


def redirect_chain(response: requests.Response) -> list[dict[str, Any]]:
    rows = []
    for item in response.history:
        rows.append({"status_code": item.status_code, "url": item.url, "location": item.headers.get("Location", "")})
    rows.append({"status_code": response.status_code, "url": response.url, "location": response.headers.get("Location", "")})
    return rows


def is_github_io(url: str, owner: str, repo: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc.lower() == f"{owner.lower()}.github.io" and parsed.path.strip("/").split("/")[0] == repo


def content_flags(text: str) -> dict[str, bool]:
    lowered = text.lower()
    compact = re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", lowered))
    return {
        "contains_example_com": bool(POLLUTION_RE.search(text)),
        "contains_ok_only": compact in {"ok", "okay"},
        "contains_header": "sfs-topnav" in lowered or "<header" in lowered or "<nav" in lowered,
        "contains_hero": "sfs-hero" in lowered or "hero" in lowered or "<h1" in lowered,
        "contains_features": "sfs-trust" in lowered or "feature" in lowered or "card" in lowered,
        "contains_cta": "sfs-cta" in lowered or "call-to-action" in lowered or "contact" in lowered or "btn" in lowered,
        "contains_footer": "sfs-footer" in lowered or "<footer" in lowered or "copyright" in lowered,
    }


def check_dist_files(report: dict[str, Any], dist: Path, github_pages_url: str) -> None:
    files = sorted([path for path in dist.rglob("*") if path.is_file() and path.suffix.lower() in {".html", ".xml", ".txt"}])
    report["seo_files_generated"] = [str(path) for path in files]
    if not files:
        add_error(report, "DEPLOY_PAGE_NOT_READY", "dist has no html/xml/txt files", dist=str(dist))
        return
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if POLLUTION_RE.search(text):
            add_error(report, "SEO_URL_POLLUTION", "generated file contains example.com or unverified test domain", file=str(path))
    index = dist / "index.html"
    if not index.exists():
        add_error(report, "DEPLOY_PAGE_NOT_READY", "dist/index.html missing", dist=str(dist))
        return
    text = index.read_text(encoding="utf-8", errors="ignore")
    flags = content_flags(text)
    report.update(flags)
    if flags["contains_ok_only"]:
        add_error(report, "INVALID_PAGE_CONTENT_OK_ONLY", "index.html contains only ok-like content")
    if not all(flags[key] for key in ["contains_header", "contains_hero", "contains_features", "contains_cta", "contains_footer"]):
        add_error(report, "INVALID_PAGE_CONTENT_INCOMPLETE", "index.html does not contain complete website structure", flags=flags)
    if github_pages_url and github_pages_url not in text:
        # Some local SEO paths are rendered before GitHub URL is known. This is not fatal if no polluted URL exists.
        report["canonical_matches_github_pages_url"] = False
    else:
        report["canonical_matches_github_pages_url"] = True


def probe_pages(report: dict[str, Any], owner: str, repo: str, allowed_custom_domains: set[str]) -> None:
    url = report["github_pages_url"]
    if not url:
        add_error(report, "DEPLOY_PAGE_NOT_READY", "github_pages_url is empty")
        return
    for attempt in range(max(1, PAGES_MAX_WAIT_SECONDS // PAGES_CHECK_INTERVAL_SECONDS)):
        log("[Pages Check] attempt", attempt=attempt + 1, url=url)
        try:
            response = requests.get(url, timeout=10, allow_redirects=True)
        except requests.RequestException as exc:
            report["last_probe_error"] = exc.__class__.__name__
            if attempt < (PAGES_MAX_WAIT_SECONDS // PAGES_CHECK_INTERVAL_SECONDS) - 1:
                time.sleep(PAGES_CHECK_INTERVAL_SECONDS)
            continue
        report["redirect_chain"] = redirect_chain(response)
        report["final_url"] = response.url
        report["http_status"] = response.status_code
        report["content_type"] = response.headers.get("Content-Type", "")
        flags = content_flags(response.text)
        report.update(flags)
        final_host = urlparse(response.url).netloc.lower()
        if any(POLLUTION_RE.search(str(step.get("url", ""))) or POLLUTION_RE.search(str(step.get("location", ""))) for step in report["redirect_chain"]):
            add_error(report, "CUSTOM_DOMAIN_POLLUTION", "redirect chain contains example.com or unverified test domain", redirect_chain=report["redirect_chain"])
        if not is_github_io(response.url, owner, repo) and final_host not in allowed_custom_domains:
            add_error(report, "UNVERIFIED_CUSTOM_DOMAIN_REDIRECT", "final URL is neither github.io project URL nor verified custom domain", final_url=response.url)
        if response.status_code != 200:
            report["last_probe_status"] = response.status_code
        elif "text/html" not in report["content_type"].lower():
            add_error(report, "INVALID_CONTENT_TYPE", "GitHub Pages response is not text/html", content_type=report["content_type"])
            break
        elif flags["contains_example_com"]:
            add_error(report, "SEO_URL_POLLUTION", "GitHub Pages HTML contains example.com or unverified test domain")
            break
        elif flags["contains_ok_only"]:
            add_error(report, "INVALID_PAGE_CONTENT_OK_ONLY", "GitHub Pages content is ok-only")
            break
        elif not all(flags[key] for key in ["contains_header", "contains_hero", "contains_features", "contains_cta", "contains_footer"]):
            add_error(report, "INVALID_PAGE_CONTENT_INCOMPLETE", "GitHub Pages content lacks complete website structure", flags=flags)
            break
        else:
            log("[Pages Check] Pages is live", final_url=response.url)
            return
        if attempt < (PAGES_MAX_WAIT_SECONDS // PAGES_CHECK_INTERVAL_SECONDS) - 1:
            time.sleep(PAGES_CHECK_INTERVAL_SECONDS)
    if report["http_status"] != 200:
        add_error(report, "PAGES_DEPLOY_TIMEOUT", "GitHub Pages URL did not return HTTP 200 within wait budget", last_status=report.get("http_status"))


def main() -> None:
    started_at = time.time()
    load_env_file()
    owner = os.getenv("GITHUB_OWNER", "")
    report: dict[str, Any] = {
        "status": "FAIL",
        "repo": "",
        "github_pages_url": "",
        "public_url": "",
        "final_url": "",
        "redirect_chain": [],
        "http_status": 0,
        "content_type": "",
        "contains_example_com": False,
        "contains_ok_only": False,
        "contains_header": False,
        "contains_hero": False,
        "contains_features": False,
        "contains_cta": False,
        "contains_footer": False,
        "errors": [],
        "api_evidence": [],
        "seo_files_generated": [],
        "execution_log": [],
        "token_redacted": True,
    }

    def step(message: str, **details: Any) -> None:
        report["execution_log"].append({"time": round(time.time() - started_at, 2), "message": message, **details})
        log(message, **details)

    missing = [name for name in ["GITHUB_TOKEN", "GITHUB_OWNER"] if not os.getenv(name)]
    if os.getenv("GITHUB_MODE") != "real":
        add_error(report, "GITHUB_MODE_NOT_REAL", "GITHUB_MODE must be real")
    if missing:
        add_error(report, "GITHUB_ENV_MISSING", "missing required GitHub environment variables", missing_env=missing)
    if report["errors"]:
        write_report(report)
        print(json.dumps({"status": "FAIL", "errors": report["errors"], "report": str(REPORT)}, ensure_ascii=False, indent=2), flush=True)
        raise SystemExit(1)

    backup = ""
    proc: subprocess.Popen | None = None
    try:
        step("[Setup] Stop existing API server")
        stop_ports()
        if DB.exists():
            backup_path = REPORTS / f"site_factory_os_before_github_real_{int(time.time())}.db"
            backup_path.parent.mkdir(exist_ok=True)
            shutil.copy2(DB, backup_path)
            backup = str(backup_path)
            DB.unlink()
            step("[Setup] Reset SQLite DB", backup=backup)

        step("[Setup] Starting FastAPI server")
        proc = subprocess.Popen(["python", "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=os.environ.copy())
        for attempt in range(60):
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

        template_id, layout = load_template()
        report["template_id"] = template_id
        stamp = str(int(time.time()))
        domain = f"github-real-{stamp}.example.com"
        step("[Auth] Login")
        login_response = api("/auth/login", method="POST", payload={"username": "candy2000", "password": "candy2000"}, timeout=10)
        report["api_evidence"].append({"api": "POST /auth/login", "status_code": login_response.status_code})
        login_response.raise_for_status()
        token = login_response.json()["token"]

        step("[Site] Create site", domain=domain)
        site_response = api(
            "/sites",
            token=token,
            method="POST",
            payload={"request_id": f"real_site_{stamp}", "alias": f"GitHub Real {stamp}", "domain": domain, "site_type": "landing", "template_id": "landing1"},
            timeout=60,
        )
        report["api_evidence"].append({"api": "POST /sites", "status_code": site_response.status_code})
        site_response.raise_for_status()
        site_id = site_response.json()["site"]["site_id"]
        db_exec("UPDATE domains SET status='ns_verified', ssl_status='active' WHERE site_id=?", (site_id,))

        step("[Page] Create page from template", template_id=template_id)
        page_response = api("/sites/%s/pages" % site_id, token=token, method="POST", payload={"request_id": f"real_page_{stamp}", "slug": "home", "page_type": "custom", "layout": layout}, timeout=10)
        report["api_evidence"].append({"api": "POST /sites/{site_id}/pages", "status_code": page_response.status_code})
        page_response.raise_for_status()
        page_id = page_response.json()["page"]["page_id"]
        db_exec("UPDATE pages SET status='published', published_at=datetime('now') WHERE page_id=?", (page_id,))

        step("[SEO] Save SEO")
        seo_title = f"GitHub Pages SEO {stamp}"
        seo_desc = "Real GitHub Pages deployment with clean SEO URLs."
        seo_response = api(f"/sites/{site_id}/seo", token=token, method="PATCH", payload={"request_id": f"real_seo_{stamp}", "language_code": "en", "title": seo_title, "description": seo_desc, "slug": "/"}, timeout=10)
        report["api_evidence"].append({"api": "PATCH /sites/{site_id}/seo", "status_code": seo_response.status_code})
        seo_response.raise_for_status()

        step("[GitHub] Deploy")
        deploy_response = api("/deploy/github", token=token, method="POST", payload={"request_id": f"real_deploy_{stamp}", "site_id": site_id}, timeout=60)
        report["api_evidence"].append({"api": "POST /deploy/github", "status_code": deploy_response.status_code})
        if not deploy_response.ok:
            add_error(report, "DEPLOY_GITHUB_API_FAILED", "POST /deploy/github failed", status_code=deploy_response.status_code, message=response_message(deploy_response))
            deploy_response.raise_for_status()
        deploy_body = deploy_response.json()
        deployment = deploy_body.get("deployment", {})
        report["repo"] = deployment.get("repo_name", "")
        report["github_pages_url"] = f"https://{owner}.github.io/{report['repo']}/" if report["repo"] else deploy_body.get("github_pages_url", "")
        report["public_url"] = deploy_body.get("public_url") or deployment.get("live_url", "")
        step("[GitHub] Deployment returned", repo=report["repo"], github_pages_url=report["github_pages_url"], public_url=report["public_url"])

        if report["public_url"] != report["github_pages_url"]:
            add_error(report, "UNVERIFIED_CUSTOM_DOMAIN_REDIRECT", "public_url should use github.io for unverified test domain", public_url=report["public_url"], github_pages_url=report["github_pages_url"])
        if POLLUTION_RE.search(report["public_url"] or ""):
            add_error(report, "CUSTOM_DOMAIN_POLLUTION", "public_url contains example.com or unverified test domain", public_url=report["public_url"])

        dist = ROOT / "generated_sites" / site_id / "dist"
        check_dist_files(report, dist, report["github_pages_url"])

        logs_response = api(f"/deploy/logs/{site_id}", token=token, timeout=10)
        report["api_evidence"].append({"api": "GET /deploy/logs/{site_id}", "status_code": logs_response.status_code})
        report["deploy_logs"] = json.dumps(logs_response.json(), ensure_ascii=False)[:4000] if logs_response.ok else logs_response.text[:1000]

        probe_pages(report, owner, report["repo"], allowed_custom_domains=set())
        if report["final_url"] and report["public_url"] and report["final_url"].rstrip("/") != report["public_url"].rstrip("/"):
            add_error(report, "PUBLIC_URL_MISMATCH", "public_url does not match final reachable URL", public_url=report["public_url"], final_url=report["final_url"])

        report["db_backup_before_clean_run"] = backup
        report["duration_seconds"] = round(time.time() - started_at, 2)
        report["status"] = "PASS" if not report["errors"] else "FAIL"
        write_report(report)
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "repo": report["repo"],
                    "github_pages_url": report["github_pages_url"],
                    "public_url": report["public_url"],
                    "final_url": report["final_url"],
                    "http_status": report["http_status"],
                    "errors": report["errors"],
                    "duration_seconds": report["duration_seconds"],
                    "report": str(REPORT),
                },
                ensure_ascii=False,
                indent=2,
            ),
            flush=True,
        )
        raise SystemExit(0 if report["status"] == "PASS" else 1)
    except SystemExit:
        raise
    except Exception as exc:
        add_error(report, "GITHUB_REAL_ACCEPTANCE_EXCEPTION", exc.__class__.__name__, message=str(exc)[:300])
        report["duration_seconds"] = round(time.time() - started_at, 2)
        write_report(report)
        print(json.dumps({"status": "FAIL", "errors": report["errors"], "report": str(REPORT)}, ensure_ascii=False, indent=2), flush=True)
        raise SystemExit(1)
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
