from sqlalchemy import Column, Float, ForeignKey, Integer, Text, UniqueConstraint

from core.database import Base


class Site(Base):
    __tablename__ = "sites"

    site_id = Column(Text, primary_key=True)
    alias = Column(Text, nullable=False)
    description = Column(Text)
    site_type = Column(Text, nullable=False)
    domain = Column(Text)
    public_url = Column(Text)
    repo_name = Column(Text)
    repo_branch = Column(Text, default="main")
    github_pages_url = Column(Text)
    template_id = Column(Text)
    theme_id = Column(Text)
    default_language = Column(Text, default="en")
    fallback_language = Column(Text, default="en")
    status = Column(Text, nullable=False)
    created_by = Column(Text)
    updated_by = Column(Text)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)
    last_deploy_at = Column(Text)


class SiteAlias(Base):
    __tablename__ = "site_aliases"

    alias_id = Column(Text, primary_key=True)
    site_id = Column(Text, ForeignKey("sites.site_id"), nullable=False)
    alias = Column(Text, nullable=False, unique=True)
    keywords = Column(Text)
    created_at = Column(Text, nullable=False)


class Domain(Base):
    __tablename__ = "domains"

    domain_id = Column(Text, primary_key=True)
    site_id = Column(Text, ForeignKey("sites.site_id"), nullable=False)
    owner_user_id = Column(Text)
    is_public_pool = Column(Integer, default=0)
    domain_mode = Column(Text, default="custom_domain")
    parent_domain = Column(Text)
    full_domain = Column(Text)
    domain = Column(Text, nullable=False, unique=True)
    registrar = Column(Text, default="name.com")
    cloudflare_zone_id = Column(Text)
    ns1 = Column(Text)
    ns2 = Column(Text)
    status = Column(Text, nullable=False)
    ssl_status = Column(Text)
    last_checked_at = Column(Text)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)


class Task(Base):
    __tablename__ = "tasks"

    task_id = Column(Text, primary_key=True)
    request_id = Column(Text, nullable=False, unique=True)
    trace_id = Column(Text, nullable=False)
    task_type = Column(Text, nullable=False)
    site_id = Column(Text)
    status = Column(Text, nullable=False)
    progress = Column(Integer, default=0)
    current_node = Column(Text)
    payload_json = Column(Text)
    result_json = Column(Text)
    error_code = Column(Text)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retry = Column(Integer, default=3)
    created_by = Column(Text)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)
    finished_at = Column(Text)


class TaskLog(Base):
    __tablename__ = "task_logs"

    log_id = Column(Text, primary_key=True)
    task_id = Column(Text, ForeignKey("tasks.task_id"), nullable=False)
    node_name = Column(Text)
    status = Column(Text)
    message = Column(Text)
    error_code = Column(Text)
    details_json = Column(Text)
    created_at = Column(Text, nullable=False)


class ResourceLock(Base):
    __tablename__ = "resource_locks"
    __table_args__ = (UniqueConstraint("resource_type", "resource_id"),)

    lock_id = Column(Text, primary_key=True)
    resource_type = Column(Text, nullable=False)
    resource_id = Column(Text, nullable=False)
    task_id = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    locked_at = Column(Text, nullable=False)
    expires_at = Column(Text)


class Article(Base):
    __tablename__ = "articles"

    article_id = Column(Text, primary_key=True)
    site_id = Column(Text, ForeignKey("sites.site_id"), nullable=False)
    cover_image = Column(Text)
    tags_json = Column(Text)
    category = Column(Text)
    status = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)
    published_at = Column(Text)


class ArticleTranslation(Base):
    __tablename__ = "article_translations"
    __table_args__ = (UniqueConstraint("article_id", "language_code"),)

    translation_id = Column(Text, primary_key=True)
    article_id = Column(Text, ForeignKey("articles.article_id"), nullable=False)
    language_code = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    seo_title = Column(Text)
    seo_description = Column(Text)
    slug = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)


class Product(Base):
    __tablename__ = "products"

    product_id = Column(Text, primary_key=True)
    site_id = Column(Text, ForeignKey("sites.site_id"), nullable=False)
    price = Column(Float, nullable=False)
    currency = Column(Text, default="USD")
    images_json = Column(Text)
    attributes_json = Column(Text)
    payment_id = Column(Text)
    status = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)
    published_at = Column(Text)


class ProductTranslation(Base):
    __tablename__ = "product_translations"
    __table_args__ = (UniqueConstraint("product_id", "language_code"),)

    translation_id = Column(Text, primary_key=True)
    product_id = Column(Text, ForeignKey("products.product_id"), nullable=False)
    language_code = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
    description = Column(Text)
    seo_title = Column(Text)
    seo_description = Column(Text)
    slug = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)


class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(Text, primary_key=True)
    site_id = Column(Text, ForeignKey("sites.site_id"), nullable=False)
    provider = Column(Text, nullable=False)
    payment_url = Column(Text, nullable=False)
    linked_product_id = Column(Text)
    button_text_json = Column(Text)
    status = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)


class Page(Base):
    __tablename__ = "pages"

    page_id = Column(Text, primary_key=True)
    site_id = Column(Text, ForeignKey("sites.site_id"), nullable=False)
    page_type = Column(Text, nullable=False)
    slug = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    layout_json = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)
    published_at = Column(Text)


class I18nLanguage(Base):
    __tablename__ = "i18n_languages"
    __table_args__ = (UniqueConstraint("site_id", "language_code"),)

    id = Column(Text, primary_key=True)
    site_id = Column(Text, ForeignKey("sites.site_id"), nullable=False)
    language_code = Column(Text, nullable=False)
    language_name = Column(Text, nullable=False)
    enabled = Column(Integer, default=1)
    is_default = Column(Integer, default=0)
    completion = Column(Integer, default=0)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)


class MediaFile(Base):
    __tablename__ = "media_files"

    media_id = Column(Text, primary_key=True)
    site_id = Column(Text, ForeignKey("sites.site_id"), nullable=False)
    file_name = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False)
    file_type = Column(Text)
    file_size = Column(Integer)
    content_hash = Column(Text)
    status = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)


class BulkJob(Base):
    __tablename__ = "bulk_jobs"

    bulk_job_id = Column(Text, primary_key=True)
    task_id = Column(Text, ForeignKey("tasks.task_id"), nullable=False)
    request_id = Column(Text, nullable=False, unique=True)
    trace_id = Column(Text, nullable=False)
    root_path = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    total_items = Column(Integer, default=0)
    success_items = Column(Integer, default=0)
    failed_items = Column(Integer, default=0)
    created_by = Column(Text)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)


class BulkItem(Base):
    __tablename__ = "bulk_items"
    __table_args__ = (UniqueConstraint("bulk_job_id", "source_hash"),)

    bulk_item_id = Column(Text, primary_key=True)
    bulk_job_id = Column(Text, ForeignKey("bulk_jobs.bulk_job_id"), nullable=False)
    site_id = Column(Text)
    item_type = Column(Text, nullable=False)
    operation = Column(Text, nullable=False)
    source_file = Column(Text, nullable=False)
    source_line = Column(Integer)
    source_hash = Column(Text, nullable=False)
    language_code = Column(Text)
    target_entity_id = Column(Text)
    status = Column(Text, nullable=False)
    error_code = Column(Text)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    last_attempt_at = Column(Text)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)


class BulkError(Base):
    __tablename__ = "bulk_errors"

    bulk_error_id = Column(Text, primary_key=True)
    bulk_job_id = Column(Text, ForeignKey("bulk_jobs.bulk_job_id"), nullable=False)
    bulk_item_id = Column(Text)
    error_code = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    file = Column(Text)
    line = Column(Integer)
    field = Column(Text)
    details_json = Column(Text)
    created_at = Column(Text, nullable=False)


class Deployment(Base):
    __tablename__ = "deployments"

    deploy_id = Column(Text, primary_key=True)
    site_id = Column(Text, ForeignKey("sites.site_id"), nullable=False)
    task_id = Column(Text, ForeignKey("tasks.task_id"), nullable=False)
    trace_id = Column(Text, nullable=False)
    request_id = Column(Text, nullable=False)
    deploy_type = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    commit_id = Column(Text)
    previous_commit_id = Column(Text)
    repo_name = Column(Text)
    repo_branch = Column(Text)
    manifest_hash = Column(Text)
    dist_path = Column(Text)
    live_url = Column(Text)
    rollback_from_deploy_id = Column(Text)
    created_by = Column(Text)
    created_at = Column(Text, nullable=False)
    finished_at = Column(Text)


class DeploymentFile(Base):
    __tablename__ = "deployment_files"

    file_id = Column(Text, primary_key=True)
    deploy_id = Column(Text, ForeignKey("deployments.deploy_id"), nullable=False)
    file_path = Column(Text, nullable=False)
    content_hash = Column(Text, nullable=False)
    file_size = Column(Integer)
    action = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)


class ErrorLog(Base):
    __tablename__ = "error_logs"

    error_id = Column(Text, primary_key=True)
    trace_id = Column(Text)
    request_id = Column(Text)
    task_id = Column(Text)
    site_id = Column(Text)
    error_code = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(Text, nullable=False)
    retryable = Column(Integer, default=0)
    user_action_required = Column(Integer, default=0)
    details_json = Column(Text)
    created_at = Column(Text, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id = Column(Text, primary_key=True)
    trace_id = Column(Text, nullable=False)
    request_id = Column(Text)
    task_id = Column(Text)
    actor_id = Column(Text)
    action = Column(Text, nullable=False)
    resource_type = Column(Text)
    resource_id = Column(Text)
    before_json = Column(Text)
    after_json = Column(Text)
    ip_address = Column(Text)
    user_agent = Column(Text)
    created_at = Column(Text, nullable=False)


class SeoRecord(Base):
    __tablename__ = "seo_records"

    seo_id = Column(Text, primary_key=True)
    site_id = Column(Text, nullable=False)
    entity_type = Column(Text, nullable=False)
    entity_id = Column(Text, nullable=False)
    language_code = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text)
    slug = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)


class Template(Base):
    __tablename__ = "templates"

    template_id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    schema_json = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)


class Confirmation(Base):
    __tablename__ = "confirmations"

    confirmation_id = Column(Text, primary_key=True)
    task_id = Column(Text, nullable=False)
    action = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    confirmed_at = Column(Text)


class User(Base):
    __tablename__ = "users"

    user_id = Column(Text, primary_key=True)
    username = Column(Text, nullable=False, unique=True)
    email = Column(Text, unique=True)
    password_hash = Column(Text, nullable=False)
    telegram_handle = Column(Text)
    role = Column(Text, nullable=False, default="operator")
    status = Column(Text, nullable=False, default="active")
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)


class Membership(Base):
    __tablename__ = "memberships"

    membership_id = Column(Text, primary_key=True)
    user_id = Column(Text, ForeignKey("users.user_id"), nullable=False, unique=True)
    plan = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    started_at = Column(Text)
    expires_at = Column(Text)
    site_limit = Column(Integer, nullable=False)
    deploy_limit_per_day = Column(Integer, nullable=False)
    device_limit = Column(Integer, nullable=False)
    can_use_bulk_import = Column(Integer, default=0)
    can_use_telegram = Column(Integer, default=0)
    can_use_diy_builder = Column(Integer, default=0)
    can_use_i18n = Column(Integer, default=0)
    can_use_payment_links = Column(Integer, default=0)
    can_use_roles = Column(Integer, default=0)
    can_use_advanced_audit = Column(Integer, default=0)
    custom_limits_json = Column(Text)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)


class CustomerServiceRequest(Base):
    __tablename__ = "customer_service_requests"

    request_id = Column(Text, primary_key=True)
    user_id = Column(Text, ForeignKey("users.user_id"), nullable=False)
    target_plan = Column(Text, nullable=False)
    contact_method = Column(Text, nullable=False)
    contact_value = Column(Text, nullable=False)
    status = Column(Text, nullable=False)
    note = Column(Text)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)
    handled_by = Column(Text)


class LicenseCode(Base):
    __tablename__ = "license_codes"

    code = Column(Text, primary_key=True)
    plan = Column(Text, nullable=False)
    duration_days = Column(Integer, nullable=False)
    status = Column(Text, nullable=False)
    used_by = Column(Text)
    created_by = Column(Text)
    created_at = Column(Text, nullable=False)
    used_at = Column(Text)
    expires_at = Column(Text)


class DeviceBinding(Base):
    __tablename__ = "device_bindings"

    device_id = Column(Text, primary_key=True)
    user_id = Column(Text, ForeignKey("users.user_id"), nullable=False)
    device_fingerprint = Column(Text, nullable=False)
    label = Column(Text)
    status = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
    last_seen_at = Column(Text)


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(Text)
    ip = Column(Text)
    user_agent = Column(Text)
    success = Column(Integer, nullable=False)
    reason = Column(Text)
    created_at = Column(Text, nullable=False)


class LoginLock(Base):
    __tablename__ = "login_locks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scope = Column(Text, nullable=False)
    scope_value = Column(Text, nullable=False)
    locked_until = Column(Text, nullable=False)
    reason = Column(Text)
    created_at = Column(Text, nullable=False)


class LoginCaptcha(Base):
    __tablename__ = "login_captchas"

    captcha_id = Column(Text, primary_key=True)
    question = Column(Text, nullable=False)
    answer_hash = Column(Text, nullable=False)
    expires_at = Column(Text, nullable=False)
    created_at = Column(Text, nullable=False)
