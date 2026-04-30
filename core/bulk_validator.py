from pathlib import Path

from sqlalchemy.orm import Session

from core.models import I18nLanguage, Site


class BulkValidator:
    def error(self, code: str, message: str, file: Path, line: int = 1, field: str | None = None) -> dict:
        return {"error_code": code, "message": message, "file": str(file), "line": line, "field": field}

    def validate_site_payload(self, db: Session, payload: dict) -> list[dict]:
        errors: list[dict] = []
        folder = payload["folder"]
        config = payload["config"]
        if config is None:
            return [self.error("BULK_CONFIG_MISSING", "config.json is required", payload["config_path"])]
        for field in ("site_id", "template", "site_type"):
            if not config.get(field):
                errors.append(self.error("BULK_CONFIG_MISSING", f"{field} is required", payload["config_path"], field=field))
        site_id = config.get("site_id")
        if site_id and not db.get(Site, site_id):
            errors.append(self.error("BULK_SITE_NOT_FOUND", "site_id not found", payload["config_path"], field="site_id"))
        language_code = config.get("language_code", "en")
        if site_id:
            enabled = (
                db.query(I18nLanguage)
                .filter(I18nLanguage.site_id == site_id, I18nLanguage.language_code == language_code, I18nLanguage.enabled == 1)
                .first()
            )
            if not enabled:
                errors.append(self.error("BULK_LANGUAGE_NOT_SUPPORTED", "language is not enabled", payload["config_path"], field="language_code"))
        if not payload["images_path"].exists():
            errors.append(self.error("BULK_IMAGE_FOLDER_MISSING", "images folder is required", payload["images_path"]))
        product = payload["product"]
        if product is None:
            errors.append(self.error("BULK_PRODUCT_MISSING", "product.txt is required", payload["product_path"]))
        else:
            if not product.get("name"):
                errors.append(self.error("BULK_PRODUCT_INVALID_FORMAT", "name is required", payload["product_path"], field="name"))
            try:
                price = float(product.get("price"))
                if price <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(self.error("BULK_PRODUCT_PRICE_INVALID", "price must be numeric and > 0", payload["product_path"], line=2, field="price"))
            images = product.get("images")
            if not isinstance(images, list) or not images:
                errors.append(self.error("BULK_PRODUCT_INVALID_FORMAT", "images are required", payload["product_path"], field="images"))
            elif payload["images_path"].exists():
                for image in images:
                    if not (payload["images_path"] / str(image)).exists():
                        errors.append(self.error("BULK_PRODUCT_IMAGE_NOT_FOUND", "image file not found", payload["product_path"], field="images"))
        article = payload["article"]
        if article is not None:
            if not article.get("title") or not article.get("content"):
                errors.append(self.error("BULK_ARTICLE_INVALID_FORMAT", "title and content are required", payload["article_path"]))
        return errors
