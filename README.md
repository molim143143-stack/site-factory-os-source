# Site Factory OS

Site Factory OS is a React + FastAPI + SQLite control system for building, managing, publishing, and auditing generated websites. It includes multi-site management, CMS, products, bulk import, DIY Builder, template library, i18n, SEO, tasks, errors, membership, GitHub Pages publishing for generated sites, and source-repo backup tooling.

## Three Different Deploy Concepts

1. Generated site publishing
   - Publishes one user-created website `dist/` to GitHub Pages.
   - This is for customer sites only.

2. Project source repository backup
   - Publishes this Site Factory OS source code to a GitHub repository such as `site-factory-os-source`.
   - This is for backup/collaboration, not for running the admin system.

3. Public admin deployment
   - The admin system is React + FastAPI + SQLite.
   - GitHub Pages cannot run the FastAPI backend or SQLite database.
   - Use a VPS, Docker, Render, Railway, Fly.io, Cloudflare Tunnel, or similar runtime for the admin system.

## Local Backend

```powershell
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Backend URLs:

```text
http://127.0.0.1:8000
http://127.0.0.1:8000/docs
```

## Local Frontend

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Frontend URL:

```text
http://127.0.0.1:5173
```

## Environment

Copy `.env.example` to `.env` and fill only the values you need locally. Never commit `.env`.

GitHub real mode requires:

```text
GITHUB_MODE=real
GITHUB_TOKEN=
GITHUB_OWNER=
GITHUB_DEFAULT_BRANCH=main
GITHUB_REPO_PREFIX=sfs-
```

Cloudflare real mode requires:

```text
CLOUDFLARE_MODE=real
CLOUDFLARE_API_TOKEN
CLOUDFLARE_ACCOUNT_ID=
```

## Template Library

The template library lives under `template_library/`.

```powershell
python template_library\scripts\download_templates.py
python template_library\scripts\normalize_templates.py
python run_template_quality_acceptance.py
```

Only `template_library/normalized/` and `template_library/meta/templates.index.json` are used by the builder. `template_library/raw/` is a local source cache and can be regenerated from `template_library/sources/templates.sources.json`.

## Publish A Generated Site

Generated websites are rendered to `generated_sites/{site_id}/dist/` and can be pushed to GitHub Pages by the backend deployment flow.

GitHub Pages is for generated static websites only. It does not run the Site Factory OS admin backend.

## Publish This Source Repository

Use:

```powershell
python publish_source_repo.py
```

This creates or updates `site-factory-os-source` and uploads source files while excluding secrets, databases, generated sites, reports, logs, dependency folders, and build output.

## Acceptance

Useful local checks:

```powershell
python run_template_quality_acceptance.py
python run_secret_scan.py
python check_github_token.py
python run_github_pages_real_acceptance.py
```

Reports are written locally and are excluded from source-repo publishing.
