# Deployment Guide

## What GitHub Pages Can And Cannot Do

GitHub Pages can host generated static websites from `generated_sites/{site_id}/dist/`.

GitHub Pages cannot run the Site Factory OS admin system because the admin system needs:

- FastAPI backend
- SQLite database
- background task/audit/error logic
- GitHub/Cloudflare/Telegram integrations

## Local Development

Backend:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

## Admin System Public Deployment Options

Use one of these for the full management system:

- VPS with Python + Node.js
- Docker on a cloud host
- Render
- Railway
- Fly.io
- Cloudflare Tunnel to a private machine

Minimum runtime needs:

- Python 3.11+
- Node.js 18+
- writable storage directory
- configured `.env`
- persistent SQLite volume or a managed database migration path

## Generated Site GitHub Pages Publishing

Generated site publishing is separate from source-repo backup.

Flow:

```text
DIY/CMS data -> template engine -> generated_sites/{site_id}/dist -> GitHub repository -> GitHub Pages URL
```

Default GitHub Pages URL:

```text
https://{GITHUB_OWNER}.github.io/{repo_name}/
```

Custom domains must be verified before they can be used for `public_url`, canonical URL, sitemap, hreflang, or CNAME.

## Project Source Repository Backup

Use:

```powershell
python publish_source_repo.py
```

This creates or updates a repository named `site-factory-os-source` by default.

Excluded from source publishing:

- `.env`
- reports
- storage
- generated_sites
- node_modules
- frontend/dist
- venv
- `__pycache__`
- SQLite databases
- logs
- zip/package artifacts
- `template_library/raw/html` cloned third-party repos

Included:

- backend source
- frontend source
- template library source, normalized templates, metadata, and docs
- scripts
- docs
- `.env.example`
- requirements/package manifests

## Token Safety

Never write tokens into source files, reports, logs, frontend code, or zip packages.

Use environment variables only:

```text
GITHUB_TOKEN
GITHUB_OWNER
CLOUDFLARE_API_TOKEN
```

Before publishing source, run:

```powershell
python run_secret_scan.py
```
