from sqlalchemy.orm import Session

from core.models import Domain, Site


READY_DOMAIN_STATUSES = {"verified", "dns_ready", "active", "github_bound", "ns_verified"}
RESERVED_TEST_DOMAINS = (".example.com", ".local.test", ".test")


def is_test_domain(domain: str | None) -> bool:
    domain = (domain or "").lower().strip()
    return not domain or domain == "example.com" or any(domain.endswith(suffix) for suffix in RESERVED_TEST_DOMAINS)


def github_pages_url(site: Site, owner: str | None = None) -> str:
    if site.github_pages_url and "mock." not in site.github_pages_url:
        return site.github_pages_url.rstrip("/") + "/"
    if owner and site.repo_name:
        return f"https://{owner}.github.io/{site.repo_name}/"
    if site.repo_name:
        return f"https://github.io/{site.repo_name}/"
    return ""


def verified_custom_domain(db: Session, site: Site) -> str:
    if is_test_domain(site.domain):
        return ""
    domains = db.query(Domain).filter(Domain.site_id == site.site_id).all()
    for row in domains:
        if row.domain != site.domain:
            continue
        if row.status in READY_DOMAIN_STATUSES and (row.ssl_status in {"active", "issued", "valid"} or row.status in {"active", "github_bound"}):
            return f"https://{row.domain.strip('/')}/"
    return ""


def resolve_public_url(db: Session, site: Site, owner: str | None = None) -> str:
    return verified_custom_domain(db, site) or github_pages_url(site, owner)
