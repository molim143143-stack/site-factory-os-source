import json
from pathlib import Path

from core.utils import sha256_text


def parse_kv_file(path: Path) -> dict:
    data: dict[str, object] = {}
    current_key: str | None = None
    lines = path.read_text(encoding="utf-8").splitlines()
    for idx, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("-") and current_key:
            data.setdefault(current_key, [])
            assert isinstance(data[current_key], list)
            data[current_key].append(line.lstrip("-").strip())
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            current_key = key.strip()
            value = value.strip()
            if value:
                data[current_key] = value
            else:
                data[current_key] = []
    data["_line_count"] = len(lines)
    return data


def load_site_folder(folder: Path) -> dict:
    config_path = folder / "config.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else None
    product_path = folder / "product.txt"
    article_path = folder / "article.txt"
    return {
        "folder": folder,
        "config_path": config_path,
        "config": config,
        "product_path": product_path,
        "product": parse_kv_file(product_path) if product_path.exists() else None,
        "article_path": article_path,
        "article": parse_kv_file(article_path) if article_path.exists() else None,
        "images_path": folder / "images",
    }


def source_hash(site_id: str, item_type: str, source_file: str, source_line: int | None, content: dict) -> str:
    normalized = json.dumps(content, ensure_ascii=False, sort_keys=True)
    return sha256_text(f"{site_id}|{item_type}|{source_file}|{source_line or 1}|{normalized}")
