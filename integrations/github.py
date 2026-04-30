import base64
import os
from typing import Any

import requests

from core.errors import AppException


class GitHubIntegration:
    def __init__(self) -> None:
        self.mode = os.getenv("GITHUB_MODE", "mock")
        self.token = os.getenv("GITHUB_TOKEN", "")
        self.owner = os.getenv("GITHUB_OWNER", "")
        self.branch = os.getenv("GITHUB_DEFAULT_BRANCH", "main")
        self.prefix = os.getenv("GITHUB_REPO_PREFIX", "sfs-")
        self.visibility = os.getenv("GITHUB_VISIBILITY", "public")
        self.api_base = os.getenv("GITHUB_API_BASE", "https://api.github.com")
        self._login: str | None = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}

    def _github_message(self, response: requests.Response) -> str:
        try:
            data = response.json()
            message = data.get("message")
            if message:
                return str(message)
        except ValueError:
            pass
        return response.reason or "GitHub API request failed"

    def _raise_api_error(self, error_code: str, message: str, response: requests.Response, api_name: str, **extra: Any) -> None:
        details = {
            "api": api_name,
            "status_code": response.status_code,
            "github_message": self._github_message(response),
            **extra,
        }
        raise AppException(error_code, message=message, details=details)

    def _require_real_config(self) -> None:
        missing = [name for name, value in {"GITHUB_TOKEN": self.token, "GITHUB_OWNER": self.owner}.items() if not value]
        if self.mode == "real" and missing:
            raise AppException("DEPLOY_REPO_CREATE_FAILED", message="GitHub real mode is missing required environment variables", details={"missing_env": missing})

    def startup_check(self) -> None:
        if self.mode != "real":
            return
        self._require_real_config()

    def _authenticated_login(self) -> str:
        if self._login:
            return self._login
        response = requests.get(f"{self.api_base}/user", headers=self._headers(), timeout=30)
        if response.status_code != 200:
            self._raise_api_error("DEPLOY_REPO_CREATE_FAILED", "GitHub token validation failed", response, "GET /user")
        self._login = str(response.json().get("login") or "")
        return self._login

    def create_repo(self, repo_name: str) -> dict[str, Any]:
        if self.mode != "real":
            return {"repo": repo_name, "mode": "mock", "created": True}
        self._require_real_config()
        try:
            login = self._authenticated_login()
            endpoint = f"{self.api_base}/user/repos" if self.owner == login else f"{self.api_base}/orgs/{self.owner}/repos"
            api_name = "POST /user/repos" if self.owner == login else "POST /orgs/{owner}/repos"
            response = requests.post(
                endpoint,
                headers=self._headers(),
                json={"name": repo_name, "private": self.visibility != "public", "auto_init": True},
                timeout=30,
            )
            if response.status_code == 422:
                return {"repo": repo_name, "already_exists": True}
            if response.status_code not in {200, 201}:
                self._raise_api_error("DEPLOY_REPO_CREATE_FAILED", "GitHub repository creation failed", response, api_name, repo=repo_name)
            return response.json()
        except requests.RequestException as exc:
            raise AppException("DEPLOY_REPO_CREATE_FAILED", message="GitHub repository creation failed", details={"repo": repo_name, "reason": exc.__class__.__name__}) from exc

    def put_file(self, repo: str, path: str, content: str, message: str) -> dict[str, Any]:
        if self.mode != "real":
            return {"commit_id": f"mock-{abs(hash((repo, path, content))) % 10_000_000}", "path": path, "mode": "mock"}
        self._require_real_config()
        try:
            url = f"{self.api_base}/repos/{self.owner}/{repo}/contents/{path}"
            sha = None
            current = requests.get(url, headers=self._headers(), params={"ref": self.branch}, timeout=30)
            if current.status_code == 200:
                sha = current.json().get("sha")
            payload = {"message": message, "content": base64.b64encode(content.encode("utf-8")).decode("ascii"), "branch": self.branch}
            if sha:
                payload["sha"] = sha
            response = requests.put(url, headers=self._headers(), json=payload, timeout=30)
            if response.status_code not in {200, 201}:
                self._raise_api_error("DEPLOY_COMMIT_FAILED", "GitHub file commit failed", response, "PUT /repos/{owner}/{repo}/contents/{path}", repo=repo, path=path)
            return response.json()
        except requests.RequestException as exc:
            raise AppException("DEPLOY_COMMIT_FAILED", message="GitHub file commit failed", details={"repo": repo, "path": path, "reason": exc.__class__.__name__}) from exc

    def enable_pages(self, repo: str) -> dict[str, Any]:
        if self.mode != "real":
            return {"repo": repo, "pages": "enabled", "mode": "mock"}
        self._require_real_config()
        try:
            response = requests.post(
                f"{self.api_base}/repos/{self.owner}/{repo}/pages",
                headers=self._headers(),
                json={"source": {"branch": self.branch, "path": os.getenv("GITHUB_PAGES_SOURCE_PATH", "/")}},
                timeout=30,
            )
            if response.status_code in {201, 204, 409, 422}:
                return {"repo": repo, "status_code": response.status_code}
            if response.status_code not in {200, 201, 204}:
                self._raise_api_error("DEPLOY_PUSH_FAILED", "GitHub Pages enable failed", response, "POST /repos/{owner}/{repo}/pages", repo=repo)
            return response.json()
        except requests.RequestException as exc:
            raise AppException("DEPLOY_PUSH_FAILED", message="GitHub Pages enable failed", details={"repo": repo, "reason": exc.__class__.__name__}) from exc

    def pages_status(self, repo: str) -> dict[str, Any]:
        if self.mode != "real":
            return {"repo": repo, "status": "built", "mode": "mock"}
        self._require_real_config()
        try:
            response = requests.get(f"{self.api_base}/repos/{self.owner}/{repo}/pages", headers=self._headers(), timeout=30)
            if response.status_code == 404:
                return {"repo": repo, "status": "pending", "html_url": f"https://{self.owner}.github.io/{repo}/"}
            if response.status_code != 200:
                self._raise_api_error("DEPLOY_FAILED", "GitHub Pages status check failed", response, "GET /repos/{owner}/{repo}/pages", repo=repo)
            data = response.json()
            data.setdefault("html_url", f"https://{self.owner}.github.io/{repo}/")
            return data
        except requests.RequestException as exc:
            raise AppException("DEPLOY_FAILED", message="GitHub Pages status check failed", details={"repo": repo, "reason": exc.__class__.__name__}) from exc

    def rollback(self, repo: str, previous_commit_id: str) -> dict[str, Any]:
        if self.mode != "real":
            return {"repo": repo, "rollback_to": previous_commit_id, "mode": "mock"}
        return {"repo": repo, "rollback_to": previous_commit_id, "note": "Use git revert workflow or Contents API restore from snapshot"}
