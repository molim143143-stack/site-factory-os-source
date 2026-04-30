# Template Library Spec

## Goal

The template library stores real open-source website templates from GitHub and exposes only inspected, normalized, available templates to the DIY Builder.

## Directory Layout

```text
template_library/
  sources/
    templates.sources.json
  raw/
    .gitkeep
    html/
  normalized/
    landing/
    saas/
    agency/
    blog/
    portfolio/
    docs/
    ecommerce/
  meta/
    templates.index.json
  previews/
  scripts/
  docs/
```

## Rules

- `raw/` stores original GitHub downloads and is never edited by user DIY changes.
- `normalized/` stores cleaned templates that can be read by Site Factory OS.
- `meta/templates.index.json` is the only template list exposed to the Web/PWA.
- Only templates with `status = available` can appear in the template picker.
- Fake seed templates, copied color variants, and one-block Hero templates are not allowed.

## Template Metadata

Each available template must record:

```json
{
  "repo_url": "",
  "repo_name": "",
  "stars": 0,
  "license": "",
  "framework": "",
  "category": "",
  "last_commit": "",
  "source_path": "",
  "local_raw_path": "",
  "normalized_path": "",
  "template_type": "static_template"
}
```

## Template Types

`static_template`

Preserves original HTML, CSS, and assets. Users can edit basic content, images, links, and SEO while keeping the original visual quality.

`builder_template`

Can be split into editable Site Factory blocks.

When in doubt, prefer `static_template` instead of breaking a good open-source design into poor fake blocks.

## Processing Flow

```text
GitHub repo
  -> template_library/raw/
  -> inspect metadata/license/static export suitability
  -> template_library/normalized/
  -> template_library/meta/templates.index.json
  -> DIY Builder template picker
```

## Commands

```powershell
python template_library\scripts\download_templates.py
python template_library\scripts\normalize_templates.py
python run_template_quality_acceptance.py
```

## Quality Acceptance

`run_template_quality_acceptance.py` checks:

- real GitHub repo URL
- stars threshold or approved flag
- license
- Header/Hero/Features/CTA/Footer
- HTML length
- CSS length
- block count
- preview existence
- publishable complete page
- no `example.com` or test-domain pollution
- no fake seed text
- low similarity between templates

Output:

```text
template_library_quality_report.json
reports/template_library_quality_report.json
```
