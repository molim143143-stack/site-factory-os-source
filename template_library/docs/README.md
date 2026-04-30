# Site Factory Template Library

This directory stores third-party open-source website templates outside the main application code.

## Layout

- `raw/`: original GitHub downloads. Do not edit these files.
- `normalized/`: cleaned templates that Site Factory OS may read.
- `previews/`: preview descriptors generated from normalized templates.
- `meta/`: template metadata and the global `templates.index.json`.
- `scripts/`: download, scan, and normalize utilities.
- `sources/`: canonical GitHub source list.

## Workflow

1. Add a repository to `template_library/sources/templates.sources.json`.
2. Run `python template_library/scripts/download_templates.py`.
3. Run `python template_library/scripts/scan_templates.py`.
4. Run `python template_library/scripts/normalize_templates.py`.
5. Run `python run_template_quality_acceptance.py`.
6. Only templates under `normalized/` with status `available` and listed in `meta/templates.index.json` may be used by the builder.

Raw templates are never modified by user DIY edits. A user starts from the normalized schema; their page changes are saved as site/page data.

## Template Modes

- `static_template`: preserves the original HTML, CSS, and assets. Users may edit basic content, images, links, and SEO without damaging the source design.
- `builder_template`: can be split into editable Site Factory blocks.

The current high-quality open-source library prefers `static_template` when preserving visual quality is safer than forcing a template into simplified builder blocks.
