import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.env_loader import load_env_file

SOURCES = ROOT / "sources" / "templates.sources.json"
LEGACY_SOURCES = ROOT / "templates.sources.json"
META_DIR = ROOT / "meta"
RAW_DIR = ROOT / "raw"
INDEX = META_DIR / "templates.index.json"


def slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")


def repo_parts(repo_url: str) -> tuple[str, str]:
    parsed = urlparse(repo_url)
    parts = parsed.path.strip("/").replace(".git", "").split("/")
    if len(parts) < 2:
        raise ValueError(f"invalid GitHub repo URL: {repo_url}")
    return parts[-2], parts[-1]


def github_headers() -> dict[str, str]:
    load_env_file()
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_meta(repo_url: str) -> dict:
    owner, repo = repo_parts(repo_url)
    headers = github_headers()
    response = requests.get(f"https://api.github.com/repos/{owner}/{repo}", headers=headers, timeout=20)
    response.raise_for_status()
    data = response.json()
    branch = data.get("default_branch") or "main"
    commit_response = requests.get(f"https://api.github.com/repos/{owner}/{repo}/commits/{branch}", headers=headers, timeout=20)
    last_commit = ""
    if commit_response.ok:
        last_commit = commit_response.json().get("commit", {}).get("committer", {}).get("date", "")
    return {
        "repo_name": data.get("name") or repo,
        "stars": int(data.get("stargazers_count") or 0),
        "license": (data.get("license") or {}).get("spdx_id") or "unknown",
        "last_commit": last_commit,
        "default_branch": branch,
        "html_url": data.get("html_url") or repo_url,
    }


def inspect_license(path: Path, fallback: str) -> str:
    if fallback and fallback != "unknown":
        return fallback
    for name in ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"]:
        candidate = path / name
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8", errors="ignore")[:1600].lower()
            if "mit license" in text:
                return "MIT"
            if "apache license" in text:
                return "Apache-2.0"
            if "bsd" in text:
                return "BSD"
            return "present"
    return "unknown"


def load_sources() -> list[dict]:
    source_path = SOURCES if SOURCES.exists() else LEGACY_SOURCES
    return json.loads(source_path.read_text(encoding="utf-8"))


def main() -> None:
    META_DIR.mkdir(parents=True, exist_ok=True)
    sources = load_sources()
    all_meta: list[dict] = []
    for source in sources:
        repo_url = source["repo_url"]
        framework = source.get("framework", "html")
        category = source.get("category", "landing")
        repo_name = source.get("name") or repo_parts(repo_url)[1]
        template_id = f"{slug(framework)}_{slug(category)}_{slug(repo_name)}"
        target = RAW_DIR / framework / repo_name
        meta = {
            "id": template_id,
            "name": repo_name,
            "source": "github",
            "repo_url": repo_url,
            "repo_name": repo_name,
            "framework": framework,
            "category": category,
            "license": "unknown",
            "stars": 0,
            "approved": bool(source.get("approved", False)),
            "status": "raw_downloaded",
            "source_path": "",
            "local_raw_path": str(target.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "local_path": str(target.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "normalized_path": "",
            "entry": "",
            "last_commit": "",
            "supports_static_export": True,
            "can_use_in_builder": False,
            "template_type": "",
            "checks": {},
            "notes": "",
        }
        try:
            gh = github_meta(repo_url)
            meta.update({key: gh[key] for key in ["repo_name", "stars", "license", "last_commit"]})
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() and (target / ".git").exists():
                subprocess.run(["git", "-C", str(target), "pull", "--ff-only"], check=True, timeout=180, capture_output=True, text=True)
            elif not target.exists():
                subprocess.run(["git", "clone", "--depth", "1", repo_url, str(target)], check=True, timeout=240, capture_output=True, text=True)
            meta["license"] = inspect_license(target, meta["license"])
            meta["status"] = "raw_downloaded"
        except Exception as exc:
            meta["status"] = "download_failed"
            meta["error"] = exc.__class__.__name__
        (META_DIR / f"{template_id}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        all_meta.append(meta)
    INDEX.write_text(json.dumps({"templates": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"sources": len(sources), "raw_downloaded": len([item for item in all_meta if item["status"] == "raw_downloaded"]), "meta_dir": str(META_DIR)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
