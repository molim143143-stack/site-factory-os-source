from sqlalchemy.orm import Session

from core.deploy_engine import DeployEngine
from core.errors import AppException
from core.models import Page
from core.site_manager import SiteManager
from core.utils import model_dict, new_id, now_iso, to_json


BLOCK_LIBRARY = [
    "Hero",
    "Text",
    "Heading",
    "Paragraph",
    "Image",
    "Button",
    "IconBlock",
    "Container",
    "GridLayout",
    "TopNav",
    "LogoBlock",
    "MenuBar",
    "Breadcrumbs",
    "SideNav",
    "Gallery",
    "ProductGrid",
    "ProductCard",
    "ProductList",
    "ProductDetail",
    "ArticleCard",
    "ArticleList",
    "CTA",
    "CTASection",
    "FAQ",
    "Contact",
    "BuyButton",
    "PaymentButton",
    "LanguageSwitcher",
    "Footer",
    "Copyright",
    "ContactInfo",
    "SocialLinks",
    "PolicyLinks",
    "CustomHtml",
    "FloatingButton",
    "ContactFloatBar",
    "PopupModal",
    "LinkButton",
    "WhatsAppButton",
    "TelegramButton",
    "WeChatButton",
    "FacebookButton",
    "InstagramButton",
    "AnnouncementBar",
    "FlashSale",
    "CountdownTimer",
    "CouponBanner",
    "VideoBlock",
    "EmbedBlock",
    "FormBlock",
    "ContactForm",
    "SubscribeForm",
    "SupportEntry",
    "ClaimCoupon",
    "InviteFriend",
    "MapBlock",
    "TrustBadge",
    "TrustBadges",
    "StatsCounter",
    "Testimonials",
    "BrandLogos",
    "SecurePayment",
    "Guarantee",
    "ReviewBlock",
    "ReviewsList",
    "RecommendedProducts",
    "PricingTable",
    "ImageText",
    "StepsFlow",
    "Timeline",
    "NoticeBar",
    "Tabs",
    "Accordion",
    "Spacer",
    "Divider",
    "HtmlBlock",
]

ACTION_SCHEMA = {
    "type": ["none", "external_url", "product", "article", "popup", "whatsapp", "telegram"],
    "target": "string",
    "open_mode": ["same_tab", "new_tab"],
    "tracking_id": "string",
}

BLOCK_SCHEMAS = {
    name: {
        "type": name,
        "content": {"title": "string", "text": "string", "label": "string"},
        "props": {"title": "string", "text": "string", "label": "string"},
        "style": {"background": "string", "color": "string", "spacing": "number"},
        "action": ACTION_SCHEMA,
        "translations": {"en": {"title": "string", "text": "string", "label": "string"}},
    }
    for name in BLOCK_LIBRARY
}
BLOCK_SCHEMAS["PopupModal"]["props"] = {"popup_id": "string", "trigger": "button|delay|scroll|mobile_bottom", "delay_ms": "number", "title": "string", "text": "string"}


class BuilderEngine:
    def __init__(self) -> None:
        self.sites = SiteManager()
        self.deploy = DeployEngine()

    def create_page(self, db: Session, site_id: str, data: dict) -> Page:
        self.sites.get_site(db, site_id)
        layout = data.get("layout", {"blocks": []})
        self._validate_layout(layout)
        now = now_iso()
        row = Page(
            page_id=new_id("page"),
            site_id=site_id,
            page_type=data.get("page_type", "custom"),
            slug=data.get("slug", "/"),
            status="draft",
            layout_json=to_json(layout),
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        db.commit()
        return row

    def update_page(self, db: Session, page_id: str, data: dict) -> Page:
        row = db.get(Page, page_id)
        if not row:
            raise AppException("SYSTEM_INVALID_INPUT", details={"page_id": page_id})
        if "layout" in data:
            self._validate_layout(data["layout"])
            row.layout_json = to_json(data["layout"])
        if "slug" in data:
            row.slug = data["slug"]
        row.updated_at = now_iso()
        db.commit()
        return row

    def publish_page(self, db: Session, *, task, page_id: str) -> dict:
        row = db.get(Page, page_id)
        if not row:
            raise AppException("SYSTEM_INVALID_INPUT", details={"page_id": page_id})
        row.status = "published"
        row.published_at = now_iso()
        db.commit()
        deployment = self.deploy.deploy(db, site_id=row.site_id, task_id=task.task_id, trace_id=task.trace_id, request_id=task.request_id, deploy_type="diy_publish")
        return {"page": model_dict(row), "deployment": model_dict(deployment)}

    def _validate_layout(self, layout: dict) -> None:
        if not isinstance(layout, dict) or not isinstance(layout.get("blocks", []), list):
            raise AppException("SYSTEM_INVALID_FORMAT", details={"field": "layout.blocks"})
        for block in layout.get("blocks", []):
            if not isinstance(block, dict) or not block.get("type"):
                raise AppException("SYSTEM_INVALID_FORMAT", details={"field": "layout.blocks.type"})
            if block.get("type") not in BLOCK_LIBRARY:
                raise AppException("SYSTEM_INVALID_FORMAT", details={"field": "layout.blocks.type", "type": block.get("type")})
            action = block.get("action") or block.get("props", {}).get("action")
            if action:
                legacy_type = "popup" if action.get("type") == "open_popup" else action.get("type", "none")
                if legacy_type not in ACTION_SCHEMA["type"] or action.get("open_mode", "same_tab") not in ACTION_SCHEMA["open_mode"] + ["modal"]:
                    raise AppException("SYSTEM_INVALID_FORMAT", details={"field": "action"})
