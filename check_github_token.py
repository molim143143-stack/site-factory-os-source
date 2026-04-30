import argparse
import base64
import json
import os
import time
from pathlib import Path
from typing import Any

import requests

from core.env_loader import load_env_file


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "reports"


def github_message(response: requests.Response) -> str:
    try:
        data = response.json()
        message = data.get("message")
        if message:
            return str(message)
    except ValueError:
        pass
    return response.reason or "GitHub API request failed"


def permission_hint(step: str, status_code: int, message: str) -> str:
    lowered = message.lower()
    if status_code == 401:
        return "401 Unauthorized: token 无效、过期、被撤销，或没有被 GitHub 接受。"
    if step == "create_repo":
        if status_code in {403, 404}:
            return "缺少创建仓库权限。经典 PAT 需要 repo 或 public_repo；细粒度 PAT 需要 Repository administration/read-write 或组织授权。"
        if "resource not accessible" in lowered:
            return "token 无法访问创建仓库资源，请检查 repo/administration 权限和 owner 组织授权。"
    if step == "write_contents":
        if status_code in {403, 404} or "resource not accessible" in lowered:
            return "缺少 contents 写入权限。细粒度 PAT 需要 Contents: Read and write。"
    if step == "enable_pages":
        if status_code in {403, 404} or "resource not accessible" in lowered:
            return "缺少 GitHub Pages/Administration 权限，或该 owner/repo 不允许当前 token 启用 Pages。"
    return "请根据 GitHub message 检查 token scope、owner、仓库权限和组织 SSO 授权。"


def record_step(results: list[dict[str, Any]], name: str, response: requests.Response, ok_codes: set[int]) -> bool:
    message = github_message(response)
    ok = response.status_code in ok_codes
    item: dict[str, Any] = {
        "step": name,
        "api": response.request.method + " " + response.request.path_url.split("?")[0],
        "status_code": response.status_code,
        "github_message": message,
        "status": "PASS" if ok else "FAIL",
    }
    if not ok:
        item["hint"] = permission_hint(name, response.status_code, message)
    results.append(item)
    return ok


def main() -> None:
    parser = argparse.ArgumentParser(description="Check GitHub token permissions without printing secrets.")
    parser.add_argument("--ignore-dotenv", action="store_true", help="Do not load root .env; useful for missing-token acceptance.")
    parser.add_argument("--repo-name", default="", help="Optional test repo name. Defaults to sfs-token-check-<timestamp>.")
    args = parser.parse_args()

    if not args.ignore_dotenv:
        load_env_file()

    REPORTS.mkdir(exist_ok=True)
    token = os.getenv("GITHUB_TOKEN", "")
    owner = os.getenv("GITHUB_OWNER", "")
    branch = os.getenv("GITHUB_DEFAULT_BRANCH", "main")
    prefix = os.getenv("GITHUB_REPO_PREFIX", "sfs-")
    api_base = os.getenv("GITHUB_API_BASE", "https://api.github.com").rstrip("/")
    repo_name = args.repo_name or f"{prefix}token-check-{int(time.time())}"
    report: dict[str, Any] = {
        "status": "FAIL",
        "missing_env": [name for name, value in {"GITHUB_TOKEN": token, "GITHUB_OWNER": owner}.items() if not value],
        "owner": owner,
        "repo": repo_name,
        "created_repo_url": "",
        "pages_url": "",
        "steps": [],
        "token_redacted": True,
    }

    if report["missing_env"]:
        report["summary"] = "缺少 GitHub 环境变量。"
        (REPORTS / "github_token_check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"status": "FAIL", "missing_env": report["missing_env"], "report": str(REPORTS / "github_token_check.json")}, ensure_ascii=False, indent=2))
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        user_response = requests.get(f"{api_base}/user", headers=headers, timeout=30)
        if not record_step(report["steps"], "user", user_response, {200}):
            report["summary"] = permission_hint("user", user_response.status_code, github_message(user_response))
            raise RuntimeError(report["summary"])
        login = user_response.json().get("login", "")
        report["authenticated_login"] = login
        report["x_oauth_scopes"] = user_response.headers.get("X-OAuth-Scopes", "")

        create_url = f"{api_base}/user/repos" if owner == login else f"{api_base}/orgs/{owner}/repos"
        create_response = requests.post(
            create_url,
            headers=headers,
            json={"name": repo_name, "private": False, "auto_init": True},
            timeout=30,
        )
        create_ok = record_step(report["steps"], "create_repo", create_response, {200, 201, 422})
        if not create_ok:
            report["summary"] = permission_hint("create_repo", create_response.status_code, github_message(create_response))
            raise RuntimeError(report["summary"])
        if create_response.status_code in {200, 201}:
            report["created_repo_url"] = create_response.json().get("html_url", "")
        else:
            report["created_repo_url"] = f"https://github.com/{owner}/{repo_name}"

        content = "<!doctype html><html><head><title>Site Factory GitHub Token Check</title></head><body>ok</body></html>"
        content_response = requests.put(
            f"{api_base}/repos/{owner}/{repo_name}/contents/index.html",
            headers=headers,
            json={
                "message": "Site Factory token check",
                "branch": branch,
                "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
            },
            timeout=30,
        )
        if not record_step(report["steps"], "write_contents", content_response, {200, 201}):
            report["summary"] = permission_hint("write_contents", content_response.status_code, github_message(content_response))
            raise RuntimeError(report["summary"])

        pages_response = requests.post(
            f"{api_base}/repos/{owner}/{repo_name}/pages",
            headers=headers,
            json={"source": {"branch": branch, "path": "/"}},
            timeout=30,
        )
        if not record_step(report["steps"], "enable_pages", pages_response, {200, 201, 204, 409, 422}):
            report["summary"] = permission_hint("enable_pages", pages_response.status_code, github_message(pages_response))
            raise RuntimeError(report["summary"])

        status_response = requests.get(f"{api_base}/repos/{owner}/{repo_name}/pages", headers=headers, timeout=30)
        if record_step(report["steps"], "pages_status", status_response, {200, 404}):
            if status_response.status_code == 200:
                report["pages_url"] = status_response.json().get("html_url", f"https://{owner}.github.io/{repo_name}/")
            else:
                report["pages_url"] = f"https://{owner}.github.io/{repo_name}/"

        report["status"] = "PASS" if all(step["status"] == "PASS" for step in report["steps"]) else "FAIL"
        report["summary"] = "GitHub token 权限检查通过。" if report["status"] == "PASS" else "GitHub token 权限检查未通过。"
    except requests.RequestException as exc:
        report["summary"] = f"GitHub API 网络请求失败：{exc.__class__.__name__}"
    except RuntimeError:
        pass

    (REPORTS / "github_token_check.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "repo": report["repo"], "pages_url": report["pages_url"], "report": str(REPORTS / "github_token_check.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
