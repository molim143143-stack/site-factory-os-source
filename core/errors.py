from dataclasses import dataclass, field
from typing import Any


ERROR_DEFS = {
    "SYSTEM_UNKNOWN_ERROR": ("CRITICAL", False, False, "unknown system error"),
    "SYSTEM_INVALID_INPUT": ("ERROR", False, False, "invalid input"),
    "SYSTEM_MISSING_FIELD": ("ERROR", False, False, "missing required field"),
    "SYSTEM_INVALID_FORMAT": ("ERROR", False, False, "invalid format"),
    "SYSTEM_TIMEOUT": ("ERROR", True, False, "operation timed out"),
    "SYSTEM_INTERNAL_EXCEPTION": ("CRITICAL", False, False, "internal exception"),
    "AUTH_UNAUTHORIZED": ("ERROR", False, True, "unauthorized"),
    "AUTH_FORBIDDEN": ("ERROR", False, True, "forbidden"),
    "AUTH_LOGIN_FAILED": ("ERROR", False, True, "login failed"),
    "INVALID_CREDENTIALS": ("ERROR", False, True, "invalid credentials"),
    "CAPTCHA_REQUIRED": ("WARNING", False, True, "captcha required"),
    "LOGIN_RATE_LIMITED": ("WARNING", False, True, "login rate limited"),
    "AUTH_TOKEN_EXPIRED": ("ERROR", False, True, "token expired"),
    "AUTH_TOKEN_INVALID": ("ERROR", False, True, "invalid token"),
    "MEMBERSHIP_EXPIRED": ("ERROR", False, True, "membership expired"),
    "MEMBERSHIP_REQUIRED": ("ERROR", False, True, "membership required"),
    "MEMBERSHIP_PLAN_LIMIT_REACHED": ("ERROR", False, True, "membership plan limit reached"),
    "MEMBERSHIP_FEATURE_NOT_ALLOWED": ("ERROR", False, True, "feature not allowed by membership"),
    "MEMBERSHIP_STATUS_INVALID": ("ERROR", False, True, "membership status invalid"),
    "LICENSE_CODE_INVALID": ("ERROR", False, True, "license code invalid"),
    "LICENSE_CODE_USED": ("ERROR", False, True, "license code used"),
    "LICENSE_CODE_EXPIRED": ("ERROR", False, True, "license code expired"),
    "LICENSE_CODE_DISABLED": ("ERROR", False, True, "license code disabled"),
    "CUSTOMER_PAYMENT_REQUIRED": ("WARNING", False, True, "customer payment required"),
    "CUSTOMER_SERVICE_REQUEST_PENDING": ("INFO", False, True, "customer service request pending"),
    "DEVICE_LIMIT_REACHED": ("ERROR", False, True, "device limit reached"),
    "SITE_NOT_FOUND": ("ERROR", False, False, "site not found"),
    "SITE_ALREADY_EXISTS": ("ERROR", False, False, "site already exists"),
    "SITE_INVALID_ID": ("ERROR", False, False, "invalid site id"),
    "SITE_INVALID_ALIAS": ("ERROR", False, False, "invalid alias"),
    "SITE_ALIAS_DUPLICATE": ("ERROR", False, False, "site alias duplicate"),
    "SITE_STATUS_INVALID": ("ERROR", False, False, "invalid site status"),
    "SITE_OPERATION_NOT_ALLOWED": ("ERROR", False, False, "site operation not allowed"),
    "CMS_ARTICLE_NOT_FOUND": ("ERROR", False, False, "article not found"),
    "CMS_ARTICLE_INVALID": ("ERROR", False, False, "invalid article"),
    "CMS_ARTICLE_EMPTY_CONTENT": ("ERROR", False, False, "article content is empty"),
    "CMS_PRODUCT_NOT_FOUND": ("ERROR", False, False, "product not found"),
    "CMS_PRODUCT_INVALID": ("ERROR", False, False, "invalid product"),
    "CMS_PRODUCT_PRICE_INVALID": ("ERROR", False, False, "product price invalid"),
    "CMS_PRODUCT_IMAGE_MISSING": ("ERROR", False, False, "product image missing"),
    "CMS_PRODUCT_ATTRIBUTE_INVALID": ("ERROR", False, False, "invalid product attribute"),
    "BULK_CONFIG_MISSING": ("ERROR", False, False, "bulk config missing"),
    "BULK_CONFIG_INVALID": ("ERROR", False, False, "bulk config invalid"),
    "BULK_SITE_NOT_FOUND": ("ERROR", False, False, "bulk site not found"),
    "BULK_FOLDER_INVALID": ("ERROR", False, False, "bulk folder invalid"),
    "BULK_PRODUCT_MISSING": ("ERROR", False, False, "bulk product missing"),
    "BULK_PRODUCT_INVALID_FORMAT": ("ERROR", False, False, "bulk product invalid format"),
    "BULK_PRODUCT_PRICE_INVALID": ("ERROR", False, False, "bulk product price invalid"),
    "BULK_PRODUCT_IMAGE_NOT_FOUND": ("ERROR", False, False, "bulk product image not found"),
    "BULK_ARTICLE_MISSING": ("ERROR", False, False, "bulk article missing"),
    "BULK_ARTICLE_INVALID_FORMAT": ("ERROR", False, False, "bulk article invalid format"),
    "BULK_LANGUAGE_NOT_SUPPORTED": ("ERROR", False, False, "bulk language not supported"),
    "BULK_IMAGE_FOLDER_MISSING": ("ERROR", False, False, "bulk image folder missing"),
    "BULK_IMAGE_INVALID": ("ERROR", False, False, "bulk image invalid"),
    "BULK_VALIDATION_FAILED": ("ERROR", False, False, "bulk validation failed"),
    "BULK_EXECUTION_FAILED": ("ERROR", True, False, "bulk execution failed"),
    "TASK_NOT_FOUND": ("ERROR", False, False, "task not found"),
    "TASK_ALREADY_EXISTS": ("ERROR", False, False, "task already exists"),
    "TASK_INVALID_TYPE": ("ERROR", False, False, "invalid task type"),
    "TASK_INVALID_STATUS": ("ERROR", False, False, "invalid task status"),
    "TASK_ALREADY_RUNNING": ("WARNING", True, False, "task already running"),
    "TASK_DUPLICATE_REQUEST_ID": ("INFO", False, False, "duplicate request id"),
    "TASK_RETRY_LIMIT_EXCEEDED": ("ERROR", False, False, "task retry limit exceeded"),
    "TASK_LOCKED_RESOURCE": ("WARNING", True, False, "resource is locked"),
    "DNS_DOMAIN_INVALID": ("ERROR", False, False, "invalid domain"),
    "DNS_ZONE_CREATE_FAILED": ("ERROR", True, False, "zone create failed"),
    "DNS_NS_NOT_CONFIGURED": ("WARNING", True, True, "nameserver not configured"),
    "DNS_NS_NOT_PROPAGATED": ("WARNING", True, True, "nameserver not propagated yet"),
    "DNS_BIND_FAILED": ("ERROR", True, False, "dns bind failed"),
    "DNS_VERIFICATION_FAILED": ("WARNING", True, True, "dns verification failed"),
    "DNS_OPERATION_REQUIRES_CONFIRMATION": ("WARNING", False, True, "dns operation requires confirmation"),
    "DEPLOY_REPO_CREATE_FAILED": ("ERROR", True, False, "repo create failed"),
    "DEPLOY_COMMIT_FAILED": ("ERROR", True, False, "commit failed"),
    "DEPLOY_PUSH_FAILED": ("ERROR", True, False, "push failed"),
    "DEPLOY_PAGE_NOT_READY": ("WARNING", True, False, "page not ready"),
    "DEPLOY_ROLLBACK_FAILED": ("ERROR", False, False, "rollback failed"),
    "DEPLOY_FAILED": ("ERROR", True, False, "deploy failed"),
    "TEMPLATE_NOT_FOUND": ("ERROR", False, False, "template not found"),
    "TEMPLATE_INVALID": ("ERROR", False, False, "template invalid"),
    "TEMPLATE_RENDER_FAILED": ("ERROR", True, False, "template render failed"),
    "I18N_LANGUAGE_NOT_SUPPORTED": ("ERROR", False, False, "language not supported"),
    "I18N_MISSING_TRANSLATION": ("WARNING", False, True, "missing translation"),
    "I18N_INVALID_FORMAT": ("ERROR", False, False, "i18n invalid format"),
    "PAYMENT_LINK_INVALID": ("ERROR", False, False, "payment link invalid"),
    "PAYMENT_PROVIDER_ERROR": ("ERROR", True, False, "payment provider error"),
    "PAYMENT_CONFIG_MISSING": ("ERROR", False, False, "payment config missing"),
}


@dataclass
class AppException(Exception):
    error_code: str
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    trace_id: str | None = None
    task_id: str | None = None
    site_id: str | None = None
    status_code: int = 400

    def payload(self) -> dict:
        severity, retryable, user_action_required, default_message = ERROR_DEFS.get(
            self.error_code,
            ERROR_DEFS["SYSTEM_UNKNOWN_ERROR"],
        )
        return {
            "error": {
                "code": self.error_code,
                "error_code": self.error_code,
                "message": self.message or default_message,
                "severity": severity,
                "priority": {"CRITICAL": "P0", "ERROR": "P1", "WARNING": "P2", "INFO": "P3"}.get(severity, "P4"),
                "retryable": retryable,
                "user_action_required": user_action_required,
                "details": self.details,
                "trace_id": self.trace_id,
                "request_id": self.request_id,
            }
        }


def require_fields(data: dict, fields: list[str], request_id: str | None = None, trace_id: str | None = None) -> None:
    missing = [field for field in fields if data.get(field) in (None, "")]
    if missing:
        raise AppException(
            "SYSTEM_MISSING_FIELD",
            details={"missing": missing},
            request_id=request_id,
            trace_id=trace_id,
        )
