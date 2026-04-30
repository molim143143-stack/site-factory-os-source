error_code_dictionary.md
🧠 一、设计原则（必须写在文件开头）
1. 所有错误必须使用 error_code，不允许只返回 message
2. error_code 必须稳定，不可随意修改（向后兼容）
3. message 仅用于人类阅读，不参与逻辑判断
4. error_code 统一格式：

   <MODULE>_<CATEGORY>_<DETAIL>

5. 所有 API / Task / Bulk / DNS / CMS / System 错误必须使用本字典
6. 所有错误必须可被机器解析（前端 / Telegram / 自动重试）
🧱 二、统一错误返回结构（强制）
{
  "error_code": "BULK_PRODUCT_PRICE_INVALID",
  "message": "price must be numeric",
  "details": {
    "file": "site_001/product.txt",
    "line": 2
  },
  "trace_id": "trace_xxx",
  "request_id": "req_xxx"
}
🧩 三、模块分类（全局）
SYSTEM   系统级错误
AUTH     权限认证
SITE     网站管理
CMS      内容系统
BULK     批量导入
TASK     任务系统
DNS      域名/DNS
DEPLOY   部署系统
TEMPLATE 模板系统
I18N     多语言系统
PAYMENT  支付系统
🚨 四、SYSTEM（系统级错误）
SYSTEM_UNKNOWN_ERROR
SYSTEM_INVALID_INPUT
SYSTEM_MISSING_FIELD
SYSTEM_INVALID_FORMAT
SYSTEM_TIMEOUT
SYSTEM_INTERNAL_EXCEPTION
🔐 五、AUTH（权限）
AUTH_UNAUTHORIZED
AUTH_FORBIDDEN
AUTH_TOKEN_INVALID
AUTH_TOKEN_EXPIRED
🏗️ 六、SITE（网站管理）
SITE_NOT_FOUND
SITE_ALREADY_EXISTS
SITE_INVALID_ID
SITE_INVALID_ALIAS
SITE_ALIAS_DUPLICATE
SITE_STATUS_INVALID
SITE_OPERATION_NOT_ALLOWED
📝 七、CMS（内容系统）
CMS_ARTICLE_NOT_FOUND
CMS_ARTICLE_INVALID
CMS_ARTICLE_EMPTY_CONTENT

CMS_PRODUCT_NOT_FOUND
CMS_PRODUCT_INVALID
CMS_PRODUCT_PRICE_INVALID
CMS_PRODUCT_IMAGE_MISSING
CMS_PRODUCT_ATTRIBUTE_INVALID
📦 八、BULK（核心模块）
📁 结构类
BULK_CONFIG_MISSING
BULK_CONFIG_INVALID
BULK_SITE_NOT_FOUND
BULK_FOLDER_INVALID
📄 商品类
BULK_PRODUCT_MISSING
BULK_PRODUCT_INVALID_FORMAT
BULK_PRODUCT_PRICE_INVALID
BULK_PRODUCT_IMAGE_NOT_FOUND
📝 文章类
BULK_ARTICLE_MISSING
BULK_ARTICLE_INVALID_FORMAT
🌐 语言类
BULK_LANGUAGE_NOT_SUPPORTED
🖼️ 媒体类
BULK_IMAGE_FOLDER_MISSING
BULK_IMAGE_INVALID
🚨 通用
BULK_VALIDATION_FAILED
BULK_EXECUTION_FAILED
⚙️ 九、TASK（任务系统）
TASK_NOT_FOUND
TASK_ALREADY_EXISTS
TASK_INVALID_TYPE
TASK_INVALID_STATUS
TASK_ALREADY_RUNNING
TASK_DUPLICATE_REQUEST_ID
TASK_RETRY_LIMIT_EXCEEDED
TASK_LOCKED_RESOURCE
🌐 十、DNS（域名系统）
DNS_DOMAIN_INVALID
DNS_ZONE_CREATE_FAILED
DNS_NS_NOT_CONFIGURED
DNS_NS_NOT_PROPAGATED
DNS_BIND_FAILED
DNS_VERIFICATION_FAILED
DNS_OPERATION_REQUIRES_CONFIRMATION
🚀 十一、DEPLOY（部署）
DEPLOY_REPO_CREATE_FAILED
DEPLOY_COMMIT_FAILED
DEPLOY_PUSH_FAILED
DEPLOY_PAGE_NOT_READY
DEPLOY_ROLLBACK_FAILED
🎨 十二、TEMPLATE（模板）
TEMPLATE_NOT_FOUND
TEMPLATE_INVALID
TEMPLATE_RENDER_FAILED
🌍 十三、I18N（多语言）
I18N_LANGUAGE_NOT_SUPPORTED
I18N_MISSING_TRANSLATION
I18N_INVALID_FORMAT
💳 十四、PAYMENT（支付）
PAYMENT_LINK_INVALID
PAYMENT_PROVIDER_ERROR
PAYMENT_CONFIG_MISSING
🧠 十五、错误严重级别（建议增加）
INFO      可忽略
WARNING   非阻断
ERROR     任务失败
CRITICAL  系统级故障
🧩 十六、推荐扩展字段（强烈建议）
{
  "severity": "ERROR",
  "retryable": true,
  "user_action_required": false
}
示例：
{
  "error_code": "DNS_NS_NOT_PROPAGATED",
  "message": "nameserver not propagated yet",
  "severity": "WARNING",
  "retryable": true,
  "user_action_required": true
}
💥 十七、关键工程规则（必须执行）
1. 所有错误必须来自本字典（禁止随意拼写）
2. 前端 / Telegram 必须根据 error_code 做行为判断
3. retryable = true 才允许自动重试
4. user_action_required = true 必须提示用户操作（例如设置NS）
5. CRITICAL 错误必须记录日志 + 报警