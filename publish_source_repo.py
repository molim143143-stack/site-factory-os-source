import argparse
import base64
import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests

from core.env_loader import load_env_file


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "source_repo_publish_report.json"
REPORT_COPY = ROOT / "reports" / "source_repo_publish_report.json"

EXCLUDED_PARTS = {
    ".git",
    ".env",
    "reports",
    "storage",
    "generated_sites",
    "node_modules",
    "dist",
    "venv",
    ".venv",
    "__pycache__",
    "logs",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

EXCLUDED_SUFFIXES = {
    ".db",
    ".sqlite",
    ".sqlite3",
    ".pyc",
    ".pyo",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".rar",
    ".log",
}

EXCLUDED_NAMES = {
    "source_repo_publish_report.json",
    "template_library_quality_report.json",
}

SOURCE_ALLOW_DIRS = {
    "api",
    "core",
    "frontend",
    "integrations",
    "sample_data",
    "templates",
    "template_library",
}

SOURCE_ALLOW_FILES = {
    ".env.example",
    ".gitignore",
    "README.md",
    "DEPLOYMENT.md",
    "TEMPLATE_LIBRARY_SPEC.md",
    "requirements.txt",
    "config.py",
    "main.py",
    "telegram_bot.py",
    "check_github_token.py",
    "publish_source_repo.py",
    "run_acceptance.py",
    "run_batch_publish_acceptance.py",
    "run_diy_editor_interaction_acceptance.py",
    "run_domain_isolation_acceptance.py",
    "run_f16_acceptance.py",
    "run_full_acceptance.py",
    "run_full_system_acceptance.py",
    "run_github_pages_real_acceptance.py",
    "run_p0_diy_buttons_deploy_seo_acceptance.py",
    "run_productization_v2_acceptance.py",
    "run_publish_dist_acceptance.py",
    "run_real_acceptance.py",
    "run_real_proof.py",
    "run_secret_scan.py",
    "run_seo_acceptance.py",
    "run_template_library_acceptance.py",
    "run_template_quality_acceptance.py",
    "run_web_interaction_acceptance.py",
    "SFS需求理解汇总.md",
    "Web总需求.md",
    "工程工单.md",
    "必须要遵守的条约.md",
    "需求补充.md",
    "项目需求.md",
    "验收标准.md",
    "error_code_dictionary.md",
}

TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".json",
    ".md",
    ".txt",
    ".css",
    ".html",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".example",
    ".gitignore",
}

SECRET_RE = re.compile(
    "|".join(
        [
            r"gh" + r"p_[A-Za-z0-9_]+",
            r"github" + r"_pat_[A-Za-z0-9_]+",
            r"Authorization:\s*token\s+[A-Za-z0-9_]+",
            r"CLOUDFLARE" + r"_API" + r"_TOKEN\s*=\s*\S+",
        ]
    ),
    re.I,
)


def rel(path: Path) -> Path:
    return path.relative_to(ROOT)


def rel_posix(path: Path) -> str:
    return rel(path).as_posix()


def is_under(path: Path, parts: tuple[str, ...]) -> bool:
    rel_parts = rel(path).parts
    return len(rel_parts) >= len(parts) and rel_parts[: len(parts)] == parts


def is_excluded(path: Path) -> bool:
    relative = rel(path)
    parts = set(relative.parts)
    if path.name in EXCLUDED_NAMES:
        return True
    if parts & EXCLUDED_PARTS:
        return True
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return True
    if is_under(path, ("template_library", "raw", "html")):
        return True
    if is_under(path, ("template_library", "raw", "static")):
        return True
    return False


def is_allowed(path: Path) -> bool:
    if is_excluded(path) or not path.is_file():
        return False
    relative = rel(path)
    top = relative.parts[0]
    return top in SOURCE_ALLOW_DIRS or relative.as_posix() in SOURCE_ALLOW_FILES


def collect_files() -> list[Path]:
    files = [path for path in ROOT.rglob("*") if is_allowed(path)]
    return sorted(files, key=lambda item: rel_posix(item).lower())


def text_for_scan(path: Path) -> str | None:
    if path.name in {".gitignore"} or path.suffix.lower() in TEXT_SUFFIXES:
        return path.read_text(encoding="utf-8", errors="ignore")
    return None


def scan_files(files: list[Path]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for path in files:
        text = text_for_scan(path)
        if text is None:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            if SECRET_RE.search(line):
                matches.append({"path": rel_posix(path), "line": line_no})
    return matches


def git_blob_sha(content: bytes) -> str:
    header = f"blob {len(content)}\0".encode("utf-8")
    return hashlib.sha1(header + content).hexdigest()


def github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def github_message(response: requests.Response) -> str:
    try:
        data = response.json()
        if data.get("message"):
            return str(data["message"])
    except ValueError:
        pass
    return response.reason or "GitHub API request failed"


class SourcePublisher:
    def __init__(self, repo_name: str, prune: bool = True) -> None:
        load_env_file()
        self.token = os.getenv("GITHUB_TOKEN", "")
        self.owner = os.getenv("GITHUB_OWNER", "")
        self.branch = os.getenv("GITHUB_DEFAULT_BRANCH", "main")
        self.api_base = os.getenv("GITHUB_API_BASE", "https://api.github.com").rstrip("/")
        self.repo_name = repo_name
        self.prune = prune
        self.headers = github_headers(self.token) if self.token else {}
        self.report: dict[str, Any] = {
            "status": "FAIL",
            "repo_name": self.repo_name,
            "owner": self.owner,
            "repo_url": "",
            "branch": self.branch,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "token_redacted": True,
            "missing_env": [],
            "excluded": sorted(EXCLUDED_PARTS),
            "excluded_suffixes": sorted(EXCLUDED_SUFFIXES),
            "included_files": 0,
            "uploaded": 0,
            "updated": 0,
            "skipped_unchanged": 0,
            "deleted_remote": 0,
            "failed": [],
            "secret_scan": {"status": "NOT_RUN", "matches": []},
        }

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        response = requests.request(method, f"{self.api_base}{path}", headers=self.headers, timeout=kwargs.pop("timeout", 30), **kwargs)
        return response

    def require_env(self) -> bool:
        missing = [name for name, value in {"GITHUB_TOKEN": self.token, "GITHUB_OWNER": self.owner}.items() if not value]
        self.report["missing_env"] = missing
        return not missing

    def ensure_repo(self) -> bool:
        user = self.request("GET", "/user")
        if user.status_code != 200:
            self.report["failed"].append({"step": "GET /user", "status_code": user.status_code, "github_message": github_message(user)})
            return False
        login = user.json().get("login", "")
        self.report["authenticated_login"] = login

        existing = self.request("GET", f"/repos/{self.owner}/{self.repo_name}")
        if existing.status_code == 200:
            self.report["repo_url"] = existing.json().get("html_url", "")
            self.report["repo_created"] = False
            return True
        if existing.status_code != 404:
            self.report["failed"].append({"step": "GET /repos/{owner}/{repo}", "status_code": existing.status_code, "github_message": github_message(existing)})
            return False

        endpoint = "/user/repos" if self.owner == login else f"/orgs/{self.owner}/repos"
        create = self.request(
            "POST",
            endpoint,
            json={"name": self.repo_name, "private": os.getenv("SOURCE_REPO_PRIVATE", "0") == "1", "auto_init": True},
        )
        if create.status_code not in {200, 201, 422}:
            self.report["failed"].append({"step": "create source repo", "status_code": create.status_code, "github_message": github_message(create)})
            return False
        if create.status_code == 422:
            after = self.request("GET", f"/repos/{self.owner}/{self.repo_name}")
            if after.status_code != 200:
                self.report["failed"].append({"step": "read source repo after 422", "status_code": after.status_code, "github_message": github_message(after)})
                return False
            self.report["repo_url"] = after.json().get("html_url", "")
            self.report["repo_created"] = False
        else:
            self.report["repo_url"] = create.json().get("html_url", "")
            self.report["repo_created"] = True
        return True

    def remote_tree(self) -> dict[str, str]:
        response = self.request("GET", f"/repos/{self.owner}/{self.repo_name}/git/trees/{self.branch}", params={"recursive": "1"})
        if response.status_code != 200:
            return {}
        tree = response.json().get("tree", [])
        return {item["path"]: item["sha"] for item in tree if item.get("type") == "blob"}

    def put_file(self, path: Path, remote_sha: str | None) -> bool:
        content = path.read_bytes()
        remote_path = rel_posix(path)
        local_sha = git_blob_sha(content)
        if remote_sha == local_sha:
            self.report["skipped_unchanged"] += 1
            return True
        payload: dict[str, Any] = {
            "message": f"Update {remote_path}",
            "content": base64.b64encode(content).decode("ascii"),
            "branch": self.branch,
        }
        if remote_sha:
            payload["sha"] = remote_sha
        response = self.request("PUT", f"/repos/{self.owner}/{self.repo_name}/contents/{remote_path}", json=payload, timeout=60)
        if response.status_code not in {200, 201}:
            self.report["failed"].append({"step": "upload", "path": remote_path, "status_code": response.status_code, "github_message": github_message(response)})
            return False
        if response.status_code == 201:
            self.report["uploaded"] += 1
        else:
            self.report["updated"] += 1
        return True

    def delete_remote_file(self, remote_path: str, sha: str) -> bool:
        payload = {"message": f"Remove excluded {remote_path}", "sha": sha, "branch": self.branch}
        response = self.request("DELETE", f"/repos/{self.owner}/{self.repo_name}/contents/{remote_path}", json=payload, timeout=60)
        if response.status_code not in {200, 204}:
            self.report["failed"].append({"step": "delete_remote_excluded", "path": remote_path, "status_code": response.status_code, "github_message": github_message(response)})
            return False
        self.report["deleted_remote"] += 1
        return True

    def publish(self) -> dict[str, Any]:
        if not self.require_env():
            self.report["summary"] = "Missing GitHub environment variables."
            return self.report
        files = collect_files()
        self.report["included_files"] = len(files)
        self.report["sample_files"] = [rel_posix(path) for path in files[:30]]
        matches = scan_files(files)
        self.report["secret_scan"] = {"status": "PASS" if not matches else "FAIL", "matches": matches}
        if matches:
            self.report["summary"] = "Secret scan failed before upload."
            return self.report
        if not self.ensure_repo():
            self.report["summary"] = "GitHub repository setup failed."
            return self.report
        remote = self.remote_tree()
        desired_paths = {rel_posix(path) for path in files}
        if self.prune:
            for remote_path, sha in sorted(remote.items()):
                if remote_path not in desired_paths:
                    self.delete_remote_file(remote_path, sha)
        remote = self.remote_tree()
        for path in files:
            self.put_file(path, remote.get(rel_posix(path)))
        self.report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.report["status"] = "PASS" if not self.report["failed"] else "FAIL"
        self.report["summary"] = "Source repository published." if self.report["status"] == "PASS" else "Source repository publish completed with failures."
        return self.report


def write_report(report: dict[str, Any]) -> None:
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    REPORT_COPY.parent.mkdir(parents=True, exist_ok=True)
    REPORT_COPY.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish Site Factory OS source code to a GitHub source repository without exposing secrets.")
    parser.add_argument("--repo", default=os.getenv("SOURCE_REPO_NAME", "site-factory-os-source"))
    parser.add_argument("--no-prune", action="store_true", help="Do not delete remote files that are excluded locally.")
    parser.add_argument("--dry-run", action="store_true", help="Only collect and scan files; do not call GitHub.")
    args = parser.parse_args()

    if args.dry_run:
        load_env_file()
        files = collect_files()
        matches = scan_files(files)
        report = {
            "status": "PASS" if not matches else "FAIL",
            "repo_name": args.repo,
            "dry_run": True,
            "included_files": len(files),
            "sample_files": [rel_posix(path) for path in files[:50]],
            "secret_scan": {"status": "PASS" if not matches else "FAIL", "matches": matches},
            "excluded": sorted(EXCLUDED_PARTS),
            "excluded_suffixes": sorted(EXCLUDED_SUFFIXES),
        }
        write_report(report)
        print(json.dumps({"status": report["status"], "dry_run": True, "included_files": len(files), "report": str(REPORT)}, ensure_ascii=False, indent=2))
        raise SystemExit(0 if report["status"] == "PASS" else 1)

    publisher = SourcePublisher(args.repo, prune=not args.no_prune)
    report = publisher.publish()
    write_report(report)
    print(
        json.dumps(
            {
                "status": report["status"],
                "repo": report.get("repo_name"),
                "repo_url": report.get("repo_url"),
                "included_files": report.get("included_files"),
                "uploaded": report.get("uploaded"),
                "updated": report.get("updated"),
                "skipped_unchanged": report.get("skipped_unchanged"),
                "deleted_remote": report.get("deleted_remote"),
                "failed": len(report.get("failed", [])),
                "report": str(REPORT),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
