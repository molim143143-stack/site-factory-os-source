export type SiteStatus = "active" | "dns_pending" | "deploying" | "error" | "inactive" | "archived";
export type TaskStatus =
  | "pending"
  | "queued"
  | "running"
  | "waiting_confirm"
  | "retrying"
  | "success"
  | "failed"
  | "cancelled"
  | "rollback_running"
  | "rollback_success"
  | "rollback_failed";

export const sites = [
  { site_id: "site_001", alias: "墨西哥商城1号", domain: "mx-shop.ai", type: "shop", status: "active" as SiteStatus, dns: "active", last_deploy_at: "2026-04-29 10:45", repo: "sfs-site-001", template: "shop1", default_language: "en", languages: ["en", "es", "zh-CN"], github: "ready", errors: 0 },
  { site_id: "site_002", alias: "Brazil Landing", domain: "br-launch.io", type: "landing", status: "deploying" as SiteStatus, dns: "active", last_deploy_at: "2026-04-29 09:18", repo: "sfs-site-002", template: "landing1", default_language: "en", languages: ["en", "pt"], github: "deploying", errors: 0 },
  { site_id: "site_003", alias: "Tokyo Blog", domain: "tokyo-notes.dev", type: "blog", status: "active" as SiteStatus, dns: "active", last_deploy_at: "2026-04-28 22:15", repo: "sfs-site-003", template: "blog1", default_language: "en", languages: ["en", "ja"], github: "ready", errors: 1 },
  { site_id: "site_004", alias: "Urdu Catalog", domain: "urdu-catalog.com", type: "catalog", status: "dns_pending" as SiteStatus, dns: "pending_ns", last_deploy_at: "never", repo: "sfs-site-004", template: "catalog1", default_language: "en", languages: ["en", "ur-Latn"], github: "waiting", errors: 0 },
  { site_id: "site_005", alias: "Vietnam Shoes", domain: "vn-shoes.store", type: "shop", status: "active" as SiteStatus, dns: "active", last_deploy_at: "2026-04-27 18:12", repo: "sfs-site-005", template: "shop1", default_language: "en", languages: ["en", "vi"], github: "ready", errors: 0 },
  { site_id: "site_006", alias: "Hindi Offers", domain: "hi-offers.net", type: "landing", status: "error" as SiteStatus, dns: "ssl_error", last_deploy_at: "2026-04-27 12:08", repo: "sfs-site-006", template: "landing1", default_language: "en", languages: ["en", "hi"], github: "failed", errors: 3 },
  { site_id: "site_007", alias: "German Parts", domain: "de-parts.eu", type: "catalog", status: "active" as SiteStatus, dns: "active", last_deploy_at: "2026-04-26 21:32", repo: "sfs-site-007", template: "catalog1", default_language: "en", languages: ["en", "de"], github: "ready", errors: 0 },
  { site_id: "site_008", alias: "China Mini Mall", domain: "cn-mini.store", type: "shop", status: "inactive" as SiteStatus, dns: "active", last_deploy_at: "2026-04-25 15:05", repo: "sfs-site-008", template: "shop1", default_language: "en", languages: ["en", "zh-CN"], github: "ready", errors: 0 },
  { site_id: "site_009", alias: "LATAM Beauty", domain: "latam-beauty.shop", type: "shop", status: "active" as SiteStatus, dns: "active", last_deploy_at: "2026-04-29 08:11", repo: "sfs-site-009", template: "shop1", default_language: "en", languages: ["en", "es", "pt"], github: "ready", errors: 1 },
  { site_id: "site_010", alias: "AI Tools Hub", domain: "aitools-hub.ai", type: "blog", status: "active" as SiteStatus, dns: "active", last_deploy_at: "2026-04-28 20:40", repo: "sfs-site-010", template: "blog1", default_language: "en", languages: ["en"], github: "ready", errors: 0 },
  { site_id: "site_011", alias: "SEA Gadgets", domain: "sea-gadgets.store", type: "shop", status: "deploying" as SiteStatus, dns: "active", last_deploy_at: "2026-04-29 11:04", repo: "sfs-site-011", template: "shop2", default_language: "en", languages: ["en", "vi", "zh-CN"], github: "deploying", errors: 0 },
  { site_id: "site_012", alias: "Archive Demo", domain: "archive-demo.dev", type: "landing", status: "archived" as SiteStatus, dns: "inactive", last_deploy_at: "2026-04-20 09:00", repo: "sfs-site-012", template: "landing1", default_language: "en", languages: ["en"], github: "archived", errors: 0 }
];

export const tasks = [
  { task_id: "task_001", request_id: "build_mx_001", trace_id: "trace_001", type: "build_site", site_id: "site_001", status: "success" as TaskStatus, progress: 100, current_node: "NotifyNode", retry_count: 0, error_code: "", node_logs: ["ValidateNode passed", "GitHub repo created", "Cloudflare zone created", "Deploy success"] },
  { task_id: "task_002", request_id: "deploy_br_001", trace_id: "trace_002", type: "deploy", site_id: "site_002", status: "running" as TaskStatus, progress: 72, current_node: "DeployNode", retry_count: 0, error_code: "", node_logs: ["Render complete", "Commit created", "Waiting Pages status"] },
  { task_id: "task_003", request_id: "bulk_latam_001", trace_id: "trace_003", type: "bulk_import", site_id: "site_009", status: "failed" as TaskStatus, progress: 44, current_node: "ValidateProductNode", retry_count: 1, error_code: "BULK_PRODUCT_IMAGE_NOT_FOUND", node_logs: ["Scan 28 files", "Validate failed at product.txt line 8"] },
  { task_id: "task_004", request_id: "dns_urdu_001", trace_id: "trace_004", type: "dns_check", site_id: "site_004", status: "waiting_confirm" as TaskStatus, progress: 30, current_node: "WaitNSVerifyNode", retry_count: 0, error_code: "DNS_NS_NOT_PROPAGATED", node_logs: ["Zone created", "NS not propagated"] },
  { task_id: "task_005", request_id: "publish_tokyo_001", trace_id: "trace_005", type: "cms_publish", site_id: "site_003", status: "success" as TaskStatus, progress: 100, current_node: "NotifyNode", retry_count: 0, error_code: "", node_logs: ["Article rendered", "Deploy snapshot saved"] },
  { task_id: "task_006", request_id: "rollback_hi_001", trace_id: "trace_006", type: "rollback", site_id: "site_006", status: "rollback_success" as TaskStatus, progress: 100, current_node: "RollbackDeployNode", retry_count: 0, error_code: "", node_logs: ["Previous commit found", "Rollback deployed"] },
  { task_id: "task_007", request_id: "i18n_sea_001", trace_id: "trace_007", type: "i18n_validate", site_id: "site_011", status: "retrying" as TaskStatus, progress: 56, current_node: "ScanMissingFieldsNode", retry_count: 2, error_code: "I18N_MISSING_TRANSLATION", node_logs: ["vi missing 4 fields", "retry queued"] },
  { task_id: "task_008", request_id: "payment_vn_001", trace_id: "trace_008", type: "payment_bind", site_id: "site_005", status: "queued" as TaskStatus, progress: 8, current_node: "TaskCreateNode", retry_count: 0, error_code: "", node_logs: ["Task queued"] }
];

export const errors = [
  { id: "err_001", level: "P1", site_id: "site_006", task_id: "task_006", error_code: "DEPLOY_PAGE_NOT_READY", message: "GitHub Pages did not become ready in time", severity: "ERROR", retryable: true, user_action_required: false, trace_id: "trace_006" },
  { id: "err_002", level: "P2", site_id: "site_009", task_id: "task_003", error_code: "BULK_PRODUCT_IMAGE_NOT_FOUND", message: "Product references missing image 8.jpg", severity: "ERROR", retryable: false, user_action_required: true, trace_id: "trace_003" },
  { id: "err_003", level: "P3", site_id: "site_011", task_id: "task_007", error_code: "I18N_MISSING_TRANSLATION", message: "Vietnamese product CTA missing", severity: "WARNING", retryable: false, user_action_required: true, trace_id: "trace_007" },
  { id: "err_004", level: "P2", site_id: "site_004", task_id: "task_004", error_code: "DNS_NS_NOT_PROPAGATED", message: "Cloudflare nameservers not detected", severity: "WARNING", retryable: true, user_action_required: true, trace_id: "trace_004" },
  { id: "err_005", level: "P4", site_id: "site_003", task_id: "task_005", error_code: "CMS_ARTICLE_EMPTY_CONTENT", message: "Draft article has empty localized body", severity: "INFO", retryable: false, user_action_required: true, trace_id: "trace_005" },
  { id: "err_006", level: "P0", site_id: "system", task_id: "task_sys", error_code: "SYSTEM_TIMEOUT", message: "Worker heartbeat delayed", severity: "CRITICAL", retryable: true, user_action_required: false, trace_id: "trace_sys" }
];

export const deployments = [
  { deploy_id: "deploy_001", site_id: "site_001", commit_id: "commit_a91d", previous_commit_id: "commit_884a", status: "success", type: "site", live_url: "https://mx-shop.ai", created_at: "2026-04-29 10:45" },
  { deploy_id: "deploy_002", site_id: "site_002", commit_id: "commit_c711", previous_commit_id: "commit_2ab1", status: "running", type: "site", live_url: "https://br-launch.io", created_at: "2026-04-29 09:18" },
  { deploy_id: "deploy_003", site_id: "site_003", commit_id: "commit_211f", previous_commit_id: "commit_111e", status: "success", type: "publish_article", live_url: "https://tokyo-notes.dev", created_at: "2026-04-28 22:15" },
  { deploy_id: "deploy_004", site_id: "site_006", commit_id: "commit_rb22", previous_commit_id: "commit_991c", status: "rollback_success", type: "rollback", live_url: "https://hi-offers.net", created_at: "2026-04-27 12:08" },
  { deploy_id: "deploy_005", site_id: "site_011", commit_id: "commit_88be", previous_commit_id: "commit_62df", status: "failed", type: "bulk_import", live_url: "https://sea-gadgets.store", created_at: "2026-04-29 11:04" }
];

export const articles = [
  { id: "article_001", site_id: "site_001", title: "New Collection Launch", status: "published", language: "en", seo: "complete" },
  { id: "article_002", site_id: "site_003", title: "Tokyo AI Notes", status: "draft", language: "ja", seo: "missing description" },
  { id: "article_003", site_id: "site_009", title: "LATAM Promo Calendar", status: "published", language: "es", seo: "complete" },
  { id: "article_004", site_id: "site_010", title: "Best AI Tools 2026", status: "archived", language: "en", seo: "complete" },
  { id: "article_005", site_id: "site_011", title: "SEA Gadget Drop", status: "draft", language: "vi", seo: "missing title" }
];

export const products = [
  { id: "product_001", site_id: "site_001", name: "Neon Runner", price: 59.99, stock: "in_stock", status: "active", image: "1.jpg", payment: "stripe_mx" },
  { id: "product_002", site_id: "site_005", name: "VN Street Shoe", price: 42.0, stock: "low", status: "active", image: "2.jpg", payment: "paypal_vn" },
  { id: "product_003", site_id: "site_009", name: "Beauty Starter Kit", price: 29.9, stock: "in_stock", status: "draft", image: "3.jpg", payment: "stripe_latam" },
  { id: "product_004", site_id: "site_007", name: "Precision Gear", price: 88.5, stock: "out", status: "inactive", image: "4.jpg", payment: "none" },
  { id: "product_005", site_id: "site_011", name: "Mini Drone", price: 119.0, stock: "in_stock", status: "active", image: "5.jpg", payment: "stripe_sea" }
];

export const languageCompletion = [
  { code: "en", name: "English", completion: 100, enabled: true, missing: 0 },
  { code: "zh-CN", name: "中文", completion: 92, enabled: true, missing: 8 },
  { code: "es", name: "Español", completion: 86, enabled: true, missing: 14 },
  { code: "pt", name: "Português", completion: 72, enabled: true, missing: 21 },
  { code: "ur-Latn", name: "Romanized Urdu", completion: 51, enabled: true, missing: 38 },
  { code: "hi", name: "Hindi", completion: 64, enabled: true, missing: 30 },
  { code: "de", name: "Deutsch", completion: 94, enabled: true, missing: 6 },
  { code: "vi", name: "Tiếng Việt", completion: 68, enabled: true, missing: 25 },
  { code: "ja", name: "日本語", completion: 89, enabled: true, missing: 11 }
];

export const trendData = [
  { day: "Mon", tasks: 18, failed: 2, deploys: 8 },
  { day: "Tue", tasks: 24, failed: 1, deploys: 12 },
  { day: "Wed", tasks: 31, failed: 4, deploys: 16 },
  { day: "Thu", tasks: 28, failed: 3, deploys: 14 },
  { day: "Fri", tasks: 36, failed: 2, deploys: 19 },
  { day: "Sat", tasks: 22, failed: 1, deploys: 10 },
  { day: "Sun", tasks: 42, failed: 5, deploys: 21 }
];

export const statusDistribution = [
  { name: "Active", value: 7 },
  { name: "Deploying", value: 2 },
  { name: "DNS Pending", value: 1 },
  { name: "Error", value: 1 },
  { name: "Inactive", value: 1 }
];

export const payments = [
  { id: "pay_001", provider: "Stripe", site_id: "site_001", url: "https://buy.stripe.com/mx", product: "Neon Runner", status: "active", button: { en: "Buy Now", es: "Comprar" } },
  { id: "pay_002", provider: "PayPal", site_id: "site_005", url: "https://paypal.me/vn", product: "VN Street Shoe", status: "active", button: { en: "Pay Now", vi: "Thanh toán" } },
  { id: "pay_003", provider: "Stripe", site_id: "site_009", url: "https://buy.stripe.com/latam", product: "Beauty Starter Kit", status: "checking", button: { en: "Order", es: "Pedir" } },
  { id: "pay_004", provider: "PayPal", site_id: "site_011", url: "https://paypal.me/sea", product: "Mini Drone", status: "active", button: { en: "Buy", zh: "购买" } }
];

export const membershipPlans = [
  { plan: "Trial", price: "Manual", siteLimit: 1, bulk: false, telegram: false, diy: "Basic preview", i18n: "en only", deploys: "3 / day", devices: 1, duration: "1-3 days" },
  { plan: "Pro", price: "Contact support", siteLimit: 30, bulk: true, telegram: true, diy: "Full", i18n: "All languages", deploys: "100 / day", devices: 2, duration: "7 / 30 / 90 days" },
  { plan: "Enterprise", price: "Custom", siteLimit: "Unlimited", bulk: "Advanced", telegram: true, diy: "Full", i18n: "All languages", deploys: "Custom", devices: "Custom", duration: "Custom" }
];

export const currentMembership = {
  user_id: "user_001",
  username: "operator@sitefactory.ai",
  plan: "Pro",
  status: "active",
  expires_at: "2026-05-29 23:59",
  site_limit: 30,
  used_sites: 12,
  deployment_limit_per_day: 100,
  deployments_today: 21,
  device_limit: 2,
  bound_devices: 2,
  features: ["Bulk Import", "Telegram 快捷操作", "DIY Builder", "多语言", "支付链接管理"]
};

export const serviceRequests = [
  { request_id: "open_req_001", user_id: "user_001", target_plan: "pro", contact_method: "telegram", contact_value: "@operator", status: "pending", note: "用户想开通30天Pro", created_at: "2026-04-29 12:01", handled_by: "" },
  { request_id: "open_req_002", user_id: "user_002", target_plan: "enterprise", contact_method: "whatsapp", contact_value: "+65 9000 1000", status: "paid", note: "Enterprise 90 days", created_at: "2026-04-29 09:20", handled_by: "admin_001" },
  { request_id: "open_req_003", user_id: "user_003", target_plan: "pro", contact_method: "telegram", contact_value: "@bulk_master", status: "activated", note: "PRO-30D activated", created_at: "2026-04-28 18:44", handled_by: "admin_001" }
];

export const licenseCodes = [
  { code: "SFS-PRO-30D-X7K9Q2", plan: "pro", duration_days: 30, status: "unused", used_by: "", created_by: "admin_001", created_at: "2026-04-29 10:30", used_at: "" },
  { code: "SFS-PRO-7D-A1B2C3", plan: "pro", duration_days: 7, status: "used", used_by: "user_003", created_by: "admin_001", created_at: "2026-04-28 14:00", used_at: "2026-04-28 14:10" },
  { code: "SFS-ENT-30D-Z9Y8X7", plan: "enterprise", duration_days: 30, status: "disabled", used_by: "", created_by: "admin_002", created_at: "2026-04-27 11:15", used_at: "" }
];

export const bulkErrors = [
  { error_code: "BULK_PRODUCT_PRICE_INVALID", message: "price must be numeric and > 0", file: "site_009/product.txt", line: 2, severity: "ERROR" },
  { error_code: "BULK_PRODUCT_IMAGE_NOT_FOUND", message: "image file 8.jpg not found", file: "site_009/product.txt", line: 8, severity: "ERROR" },
  { error_code: "BULK_LANGUAGE_NOT_SUPPORTED", message: "language folder is not enabled", file: "site_004/i18n/fr/product.txt", line: 1, severity: "WARNING" }
];
