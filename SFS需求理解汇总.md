# Site Factory OS（SFS）需求理解汇总

生成时间：2026-04-29

本文档是我基于以下文件形成的当前需求理解：

- `项目需求.md`
- `error_code_dictionary.md`
- `工程工单.md`
- `必须要遵守的条约.md`
- `需求补充.md`

若后续需求补充与本文档冲突，应以后续最新补充为准。

---

## 1. 系统定位

Site Factory OS（SFS）不是普通 CMS、不是单站建站工具、不是简单 Telegram Bot，也不是部署脚本。

它的最终定位是：

```text
多语言网站工厂操作系统
= 多站点管理
+ 自动建站
+ CMS / 商品管理
+ 文件夹批量内容导入
+ 多语言发布
+ Web/PWA 拖拽建站
+ Telegram 快捷控制
+ GitHub + Cloudflare 自动部署
+ 任务审计
+ 错误追踪
+ 可回滚发布
```

核心目标：

```text
可扩展
可追踪
可回滚
可审计
不重复执行
不产生脏数据
```

优先级：

```text
正确性 > 可追踪 > 可恢复 > 可扩展 > 功能数量
```

---

## 2. 总体架构

系统必须遵守以下执行链路：

```text
Web / PWA 主控制台
        ↓
Telegram 快捷控制台
        ↓
FastAPI Gateway
        ↓
Task Engine 唯一执行入口
        ↓
Workflow Router
        ↓
Core Engines
        ↓
Integrations
        ↓
GitHub + Cloudflare
```

Web/PWA 是主操作系统，负责完整管理能力。

Telegram 是快捷遥控器，只能做状态查看、轻量操作、任务确认、错误提醒，不能绕过 Task Engine，不能直接执行高风险生产操作。

---

## 3. 技术栈与存储准绳

最新需求已明确覆盖早期 JSON 存储方案。

必须使用：

```text
Python 3.11+
FastAPI
SQLite
SQLAlchemy / SQLModel
```

数据存储规则：

```text
所有业务数据必须进入 SQLite
数据库文件：storage/site_factory_os.db
禁止使用 JSON 文件作为主业务存储
JSON 仅允许用于 config、日志导出、debug 数据
```

这意味着早期 `storage/*.json` 只能作为历史草案理解，真正实现时必须按 SQLite 表设计施工。

---

## 4. 全局强制规则

以下规则绝对不能违反：

```text
1. 所有写操作必须带 request_id
2. 所有写操作必须保证 request_id 幂等
3. 所有任务必须带 trace_id
4. 所有业务写入必须走 Task Engine
5. API 层禁止直接写业务数据
6. 禁止绕过 ValidateNode
7. 禁止绕过 RequestIdempotencyNode
8. 同一 site_id 禁止并发 build / deploy / bulk_import / publish
9. 所有错误必须使用 error_code_dictionary.md 中的 error_code
10. 所有错误必须结构化返回
11. 所有关键操作必须写 audit_logs
12. 所有 deploy 必须生成 deployment snapshot
13. 所有 rollback 必须基于 deployment snapshot
14. DNS / Cloudflare Zone / NS 修改不允许自动回滚
15. Bulk 必须 scan → validate → preview → execute
16. Bulk validate 阶段禁止写入业务表
17. Bulk retry 只能处理失败项
18. Bulk 禁止重跑成功数据
19. 所有模块必须可独立运行和测试
20. 禁止空函数、伪代码、只写结构不实现逻辑
```

---

## 5. API 设计准绳

最新补充要求统一 REST 风格。

所有 API 必须使用：

```text
/api/v1
```

禁止继续使用早期混乱接口风格，例如：

```text
/site/create
/site/list
/site/{site_id}/update
```

统一原则：

```text
统一 REST 风格
所有写操作必须带 request_id
所有异步或高风险操作返回 task_id
所有错误走 error_code
```

核心 API 分组包括：

```text
System API
Site API
Alias API
Domain / DNS API
Deploy API
CMS API
Product API
Payment API
Bulk API
I18n API
SEO API
DIY Builder API
Task API
Error API
Audit API
```

---

## 6. 错误系统理解

错误必须统一来自 `error_code_dictionary.md`。

错误返回结构必须为：

```json
{
  "error": {
    "error_code": "XXX_XXX_XXX",
    "message": "human readable",
    "severity": "ERROR",
    "retryable": true,
    "user_action_required": false,
    "details": {},
    "trace_id": "trace_xxx",
    "request_id": "req_xxx"
  }
}
```

错误原则：

```text
error_code 用于机器判断
message 只给人类阅读
前端 / Telegram / 自动重试逻辑必须依赖 error_code
禁止随意新增或拼写 error_code
CRITICAL 错误必须记录日志并报警
retryable = true 才允许自动重试
user_action_required = true 必须提示用户操作
```

---

## 7. Task Engine 理解

Task Engine 是系统唯一执行入口。

任务必须包含：

```text
task_id
request_id
trace_id
task_type
site_id
status
progress
current_node
payload_json
result_json
error_code
retry_count
logs
```

幂等规则：

```text
if request_id 已存在:
    返回已有 task
    禁止创建新 task
```

状态机：

```text
pending → running → success
                ↘ failed → retrying → running
```

禁止：

```text
success → running
跳状态
同一 request_id 生成多个 task
同一 site_id 并发 build / deploy / bulk_import / publish
```

任务日志必须完整记录节点过程。

---

## 8. Deploy 与 Rollback 理解

每次 deploy 必须生成快照，快照是回滚和审计的核心依据。

每次部署必须记录：

```text
deploy_id
site_id
task_id
trace_id
request_id
deploy_type
status
repo_name
repo_branch
commit_id
previous_commit_id
manifest_hash
dist_path
live_url
created_by
created_at
finished_at
```

每次部署还必须记录文件级明细：

```text
file_path
content_hash
file_size
action: added / modified / deleted / unchanged
```

回滚规则：

```text
rollback 必须基于 deploy_id
rollback 必须使用 previous_commit_id
rollback 本身也是一次 deploy，deploy_type = rollback
rollback 成功后必须重新检测 GitHub Pages 部署状态
DNS / Cloudflare Zone / NS 修改不允许自动回滚
```

可回滚：

```text
GitHub deploy
CMS 发布
商品发布
模板渲染
```

半回滚：

```text
Bulk Import：不自动删除成功项，只允许 retry 失败项
```

不可自动回滚：

```text
Cloudflare zone 创建
NS 修改
域名绑定
DNS 记录修改
```

---

## 9. Bulk Import 理解

Bulk 是核心赚钱模块，必须严格实现，不允许简化。

标准流程：

```text
scan
↓
validate
↓
preview
↓
execute
```

强制规则：

```text
scan 只扫描
validate 只校验
preview 只预览
execute 才允许写入业务表
validate 必须全部通过才允许 execute
禁止边执行边报错
retry 只处理 failed items
成功项永不重跑
有成功变更才触发 deploy
无成功变更不 deploy
```

校验规则：

```text
config.json:
- site_id 必填
- template 必填
- site_type 必填

product:
- name 必填
- price 必须 float
- price > 0
- images 必须存在

article:
- title 必填
- content 必填

language:
- language_code 必须在 enabled_languages
```

Bulk Item 必须有稳定唯一标识：

```text
source_hash = sha256(site_id + item_type + source_file + source_line + normalized_content)
```

可 retry 状态：

```text
validation_failed
execute_failed
retry_failed
```

禁止 retry 状态：

```text
execute_success
retry_success
skipped
```

Retry 必须重新读取源文件、重新 parse、重新 validate，validate 通过后才 execute。

---

## 10. 核心业务模块

最终系统包含以下核心模块：

```text
F1 Build Engine 建站系统
F2 CMS Engine 内容与商品系统
F3 Site Manager 多网站管理系统
F3.1 Alias Engine 站点别名系统
F4 Bulk Import Engine 批量导入系统
F5 Template Engine 模板系统
F6 Deploy Engine 部署系统
F7 DNS & Domain Engine 域名系统
F8 Task Engine 任务系统
F9 Telegram Engine 快捷控制系统
F10 Web / PWA 主控制台
F11 Payment Engine 支付链接系统
F12 I18n Engine 多语言系统
F13 DIY Builder Engine 拖拽建站系统
F14 SEO Engine 多语言 SEO 系统
F15 Audit & Error Engine 审计与错误中心
```

---

## 11. 多语言理解

多语言是正式核心模块，不是附加功能。

规则：

```text
默认语言必须是 en
所有站点必须有 en
所有语言允许 fallback 到 en
必须支持语言完整度检测
发布前必须检查语言完整度
```

必须支持语言：

```text
en
zh-CN
es
pt
ur-Latn
hi
de
vi
ja
```

---

## 12. SEO 理解

SEO 必须支持多语言。

每个语言独立：

```text
title
description
slug
```

必须生成：

```text
hreflang
sitemap.xml
robots.txt
canonical
Open Graph
```

---

## 13. DIY Builder 理解

DIY Builder 是 Web/PWA 的正式核心能力。

页面必须存储为：

```text
page.json
```

必须支持：

```text
拖拽区块
排序
属性编辑
多语言字段编辑
手机 / 桌面预览
保存草稿
发布页面
发布后 Render → Deploy
回滚
```

常见模块包括：

```text
Hero
Text
Image
Gallery
ProductGrid
ProductCard
ArticleList
CTA
FAQ
Contact
PaymentButton
LanguageSwitcher
Footer
CustomHtml
```

---

## 14. 权限与高风险确认

高风险操作必须进入 `waiting_confirm`，需要人工确认。

高风险操作包括：

```text
删除站点
删除域名
修改 DNS
发布生产环境
回滚生产环境
清空数据
批量覆盖内容
禁用语言
删除模板
删除支付链接
批量导入
```

Telegram 不允许绕过确认流程。

---

## 15. SQLite 表设计理解

终版至少需要以下表：

```text
sites
site_aliases
domains
tasks
task_logs
resource_locks
articles
article_translations
products
product_translations
payments
pages
i18n_languages
media_files
bulk_jobs
bulk_items
bulk_errors
deployments
deployment_files
error_logs
audit_logs
```

阶段四还会扩展：

```text
page_versions
seo_records
templates
template_versions
users
roles
user_roles
confirmations
telegram_sessions
```

---

## 16. 四阶段实施理解

### 阶段一：底座 + SQLite + Task + Site + Domain + Deploy

目标：一次性打好终版地基，不做玩具版。

必须实现：

```text
FastAPI
SQLite
SQLAlchemy / SQLModel
/api/v1
统一错误结构
Task Engine
RequestIdempotencyNode
ValidateNode
Lock Manager
Audit Engine
Error Engine
Site Manager
Alias Engine
DNS Engine
Deploy Engine
Deploy Snapshot
Rollback 基础能力
```

必须完成表：

```text
sites
site_aliases
domains
tasks
task_logs
resource_locks
deployments
deployment_files
error_logs
audit_logs
```

禁止实现：

```text
CMS
Product
Payment
Bulk
I18n
SEO
DIY Builder
```

### 阶段二：CMS + Product + Payment + Publish

目标：实现内容和商品发布链路。

必须实现：

```text
CMS Engine
Product Engine
Payment Engine
Publish Engine
Render Engine 基础版
Media Engine 基础版
```

强制规则：

```text
文章支持 draft / published / archived
商品支持 draft / active / archived
product.price 必须 REAL 且 > 0
发布必须走 Task Engine
发布必须触发 Render → Deploy
禁止 API 层直接写 GitHub
```

### 阶段三：Bulk Import 核心模块

目标：实现文件夹批量导入、多站内容批量发布、失败报告和精确 retry。

必须实现：

```text
Bulk Engine
Bulk Parser
Bulk Validator
Bulk Executor
Bulk Reporter
Bulk Retry Engine
Bulk Preview Engine
```

强制规则：

```text
scan 只扫描
validate 只校验
preview 只预览
execute 才写入
retry 只重试 failed items
成功项永不重跑
execute 有成功变更才 deploy
```

### 阶段四：I18n + SEO + DIY Builder + Web/PWA + Telegram

目标：完成终版操作系统能力。

必须实现：

```text
I18n Engine
SEO Engine
Template Engine
DIY Builder Engine
Web/PWA 控制台
Telegram 快捷控制台
权限系统
高风险确认系统
```

强制规则：

```text
所有站点必须有 en
所有语言 fallback 到 en
发布前显示语言完整度
SEO 支持多语言 title / description / slug
自动生成 hreflang
自动生成 sitemap.xml
DIY Builder 保存 page.json
DIY 发布必须走 Render → Deploy
Telegram 只能做快捷操作，不能绕过 Task Engine
高风险操作必须二次确认
```

---

## 17. Agent 执行与交付要求

每次执行必须记录：

```markdown
## Execution Log

### Step: XXX
- Action:
- Input:
- Output:
- DB Changes:
- Files Changed:
- Error:
- Result:
```

每次代码修改必须说明：

```markdown
## Code Change

### 文件：
xxx.py

### 修改前：
原代码片段

### 修改后：
完整可替换代码

### 修改原因：
```

每个功能验收必须提供：

```text
curl 示例
输入数据
返回数据
数据库变化
日志输出
```

每个阶段完成后必须生成一份阶段报告，报告中必须体现：

```text
1. 本阶段完成了哪些工作
2. 涉及哪些模块、API、数据库表、核心流程
3. 是否严格按照用户需求完成
4. 是否满足根目录 验收标准.md
5. 每一条阶段验收项的通过 / 未通过状态
6. API 测试结果
7. SQLite 数据校验结果
8. task_logs / audit_logs / error_logs 校验结果
9. request_id 幂等测试结果
10. site_id 任务锁 / 并发测试结果
11. error_code 合法性测试结果
12. 当前遗留问题和未完成项
13. 禁止越界实现的自检结果
```

阶段报告必须以根目录 `验收标准.md` 为验收准绳，不能只写主观总结。

四个阶段全部结束后，必须额外回复一份完整测试流程，覆盖：

```text
阶段一：建站链路测试
阶段二：CMS / Product / Payment / Publish 测试
阶段三：Bulk scan / validate / preview / execute / retry 测试
阶段四：Task retry / cancel / rollback / audit / observability 测试
全链路：建站 → 内容发布 → Bulk → Deploy → Rollback → Error Retry
```

最终测试流程必须包含：

```text
curl 请求示例
预期返回结构
SQLite 查询语句
日志检查方式
错误场景验证
幂等验证
并发锁验证
回滚验证
最终 PASS / FAIL 判定标准
```

---

## 18. 当前最重要的纠偏点

根据最新补充，以下早期需求需要被修正：

```text
早期：storage/*.json 作为主存储
现在：SQLite 是唯一业务持久化，JSON 只能用于 config / export / debug

早期：/site/create、/task/{task_id} 等零散接口
现在：统一 /api/v1 REST API

早期：阶段一可用 mock + 简单 JSON MVP
现在：阶段一就必须按终版底座施工，包括 SQLite、Error、Audit、Lock、Deploy Snapshot、Rollback 基础能力

早期：部署只需 mock 成功
现在：每次 deploy 必须生成 deployment snapshot，rollback 必须基于 deploy_id
```

---

## 19. 我对最终交付的理解

最终系统必须成为：

```text
一个以 Web/PWA 为主控制台、
Telegram 为快捷控制台、
FastAPI 为网关、
Task Engine 为执行中心、
SQLite 为业务数据库、
GitHub + Cloudflare 为部署网络层的
多语言网站工厂系统。
```

它必须能完成：

```text
多站管理
自动建站
域名 / DNS 状态管理
GitHub Pages 部署
部署快照
回滚
CMS 文章发布
商品发布
支付链接绑定
Bulk 文件夹批量导入
Bulk 精确 retry
多语言发布
多语言 SEO
DIY 拖拽建站
Web/PWA 管理
Telegram 快捷控制
任务日志
错误追踪
审计记录
高风险操作确认
```

实现时不能为了短期跑通而写临时结构，不能先做 JSON 玩具版再迁移 SQLite，不能重复实现同一模块，也不能在后续阶段推翻前面阶段。
