# 架构说明（Phase 0–6）

## 总体结构

```
浏览器
  │
  ├─ 开发：Vite dev server :5173 ──/api 代理──> FastAPI :8000 ──> MySQL 8
  │
  └─ 生产：Nginx :80 ──静态文件──> frontend/dist
              └──────/api────────> FastAPI :8000 ──> MySQL 8
```

前端只通过相对路径 `/api/...` 访问后端：

- 开发环境由 Vite 代理到 `VITE_PROXY_TARGET`
- 生产环境由 Nginx 转发到 `127.0.0.1:8000`

这样不需要在前端硬编码后端地址，也避免生产环境跨域。

## 后端分层

| 目录 | 职责 |
| --- | --- |
| `app/api/routes/` | HTTP 路由，只做参数解析与响应组装 |
| `app/core/config.py` | `.env` 配置，唯一配置入口 |
| `app/db/` | engine、session、声明式 Base |
| `app/models/` | SQLAlchemy ORM 模型 |
| `app/schemas/` | Pydantic 响应模型 |
| `app/services/` | 查询与业务编排 |
| `app/sync/` | 数据源接口、适配器、同步编排、upsert、定时任务 |
| `app/ai/` | 用户 AI 配置、VisionProvider 接口与 Provider 适配器 |
| `app/vision/` | 图片校验/压缩、结构化 JSON 解析与标准号防猜测 |
| `app/api/deps.py` | 管理员令牌校验 |
| `app/utils/` | 无外部依赖的纯工具（标准号规范化） |
| `alembic/` | 数据库迁移 |
| `scripts/init_db.py` | 数据库存在性检查/创建 |
| `tests/` | pytest 单元与接口测试 |

`app/main.py` 创建 FastAPI 实例、注册 CORS 与路由，并在关闭时释放连接池。业务接口统一使用 `/api/v1` 前缀，`/api/health` 保持不带版本。

## 健康检查语义

`GET /api/health` 始终返回 HTTP 200（只要进程存活），通过响应体表达状态：

| 字段 | 含义 |
| --- | --- |
| `status=ok` | API 正常且 `SELECT 1` 成功 |
| `status=degraded` | API 正常，但数据库不可用 |
| `database.detail` | 数据库失败原因摘要 |

这样前端可以区分“后端没起来”和“后端起来了但数据库没配好”，本地调试时不需要猜。

## 数据库与迁移

- 字符集统一 `utf8mb4`，排序规则 `utf8mb4_0900_ai_ci`（MySQL 8）
- Alembic 从 `app.core.config` 读取 URL，不写入 `alembic.ini`，避免密码进入版本库
- `alembic/env.py` 显式导入 `app.models`，确保模型注册到 `Base.metadata`
- 新增模型的流程：

```bash
cd backend
python -m alembic revision --autogenerate -m "describe change"
python -m alembic upgrade head
```

Phase 0 创建 `app_meta` 表，用于验证 ORM + 迁移链路；Phase 1 新增 `standard` 表；Phase 2 新增 `standard_relation` 表；Phase 3 新增 `sync_task` 表；Phase 4 新增 `product_category`、`product_alias`、`standard_product_relation`。

## 标准数据模型与搜索

`standard` 表保存标准元数据，关键约束：

- `normalized_no` 唯一，作为标准号的内部匹配键
- `standard_no` 保留展示写法
- `status` 使用 MySQL `ENUM`：`UPCOMING`、`ACTIVE`、`REPLACED`、`ABOLISHED`、`UNKNOWN`
- 日期字段允许为空，来源和官方链接也允许为空

`StandardNoNormalizer` 的职责：

1. NFKC 折叠全角字符
2. 去除所有空白并转大写
3. 各类横线（em dash、en dash、全角连字符等）统一为 `-`
4. 输出 `PREFIX NUMBER-YEAR`，例如 `GB 4806.11-2023`
5. 无法识别时抛出 `ValueError`，`try_normalize()` 返回 `None`

搜索流程（`GET /api/v1/standards/search`）：

1. 尝试把 `q` 规范化
2. 组合三类条件：`standard_no` 精确（忽略大小写）、`normalized_no` 精确、`standard_name` 模糊
3. 使用 `case` 让标准号精确命中排在名称命中之前
4. 单独查询总数，再按 `limit/offset` 取当页数据

名称模糊搜索会转义 `!`、`%`、`_`，避免用户输入被当作 SQL 通配符。Phase 1 不建立全文索引，数据量增大后再考虑 MySQL FULLTEXT 或搜索引擎。

## 版本关系与版本链

`standard_relation` 保存标准之间的有向关系，字段为 `source_standard_id`、`target_standard_id`、`relation_type`、`created_at`。方向按字段名理解：

- `source REPLACES target`：source 是新版本
- `source REPLACED_BY target`：source 是旧版本
- `AMENDS` / `AMENDED_BY`：修改关系，方向同理
- `RELATED`：相关标准，不是版本谱系

约束：

- 同一 `(source, target, relation_type)` 不能重复
- `source != target`
- 两个外键都指向 `standard.id`，删除标准时级联删除关系

版本链构建（`GET /api/v1/standards/{id}/versions`）：

1. 校验起始标准存在，不存在返回 404
2. 从起始 ID 做 BFS，双向遍历 `REPLACES`、`REPLACED_BY`、`AMENDS`、`AMENDED_BY`
3. `RELATED` 不参与遍历，避免把“相关标准”误当成版本
4. 使用 visited 集合处理环和重复边
5. 加载所有节点后按版本顺序排序；没有关系的标准返回只包含自身的链

排序键：

1. `standard_year`；为空时依次回退到 `effective_date`、`publish_date` 的年份
2. 同一年按 `effective_date` 倒序
3. 再按 `publish_date` 倒序、ID 倒序

状态标记由 `Standard` 的属性计算，只依赖 `status`：

| status | isCurrent | isUpcoming | isHistorical |
| --- | --- | --- | --- |
| `ACTIVE` | true | false | false |
| `UPCOMING` | false | true | false |
| `REPLACED` / `ABOLISHED` | false | false | true |
| `UNKNOWN` | false | false | false |

排序位置和年份大小不参与现行状态判断。响应的版本项使用 camelCase 序列化别名（`standardNo`、`effectiveDate` 等），`effectiveDate` 字段始终存在。

## 标准数据同步

### 适配器边界

`app/sync/base.py` 定义 `StandardDataSource`：

- `source_name()`
- `fetch_list()`：全量初始化
- `fetch_updates(since)`：增量
- `fetch_detail(item)`：详情与关系

同步服务只依赖该接口；第一个实现是 `StdSamrDataSource`（std.samr.gov.cn），列表使用 JSON 接口，详情使用 BeautifulSoup 解析 HTML。适配器负责请求超时、限速、指数退避重试和 User-Agent；同步服务不感知 HTTP 细节。

### 模式选择

| 请求模式 | 行为 |
| --- | --- |
| `auto` | 没有成功/部分成功的任务时全量，否则增量 |
| `full` | 强制全量 |
| `incremental` | 仅增量，未初始化时报错 |

首次全量由管理员调用 `POST /api/admin/sync/standards` 触发；每日 APScheduler 任务只做增量，未初始化时跳过。这样避免服务首次启动时自动发起 8 万条级别的长任务。

### 同步流程

1. 创建 `sync_task`（RUNNING）
2. 全量使用 `fetch_list()`；增量使用最后成功任务完成时间减去回看窗口
3. 逐条拉取详情；详情失败时保留列表元数据并计入 `failed_count`
4. 按 `normalized_no` upsert 标准
5. 收集替代关系；关系目标不在本次窗口内时，额外拉取一次目标详情更新其状态/废止日期，再写 `standard_relation`
6. 更新任务计数、状态、结束时间和错误摘要
7. 单条失败不终止整次同步；列表/传输致命错误标记 FAILED 或 PARTIAL

### 写入

`app/sync/upsert.py` 按方言使用：

- MySQL：`INSERT ... ON DUPLICATE KEY UPDATE`
- SQLite（测试）：`ON CONFLICT DO UPDATE`
- 其他方言：查询后更新/插入

可选字段使用 `COALESCE`，源数据缺失时保留已有值。关系写入是幂等的。

### 调度与并发

- APScheduler `BackgroundScheduler` 在 FastAPI lifespan 内启动/停止
- 每日 `SYNC_SCHEDULE_HOUR:SYNC_SCHEDULE_MINUTE`（服务器本地时间）
- 进程内 `threading.Lock` + `sync_task` RUNNING 检查防止并发
- 服务重启时把遗留 RUNNING 任务标记 FAILED
- systemd 固定单 worker；多 worker 需要拆出独立调度进程

### 同步日志

`sync_task` 记录 source、开始/结束时间、总数/成功/失败数、状态和错误摘要；状态为 RUNNING / SUCCESS / PARTIAL / FAILED。应用日志同时记录启动、单条失败和结束摘要。

### 已知限制

- 来源列表按发布日期倒序；只废止、且没有任何新标准引用它的旧标准，不会进入增量窗口，需要定期手动 `mode=full`
- 当前来源只暴露替代/被替代关系；AMENDS / RELATED 表结构支持，但该适配器暂时不会产生
- 不下载 PDF，仅保存元数据和官方 `source_url`

## 商品分类与标准关联

三张表：

- `product_category`：自关联 `parent_id`，名称和描述
- `product_alias`：分类别名，`(category_id, alias)` 唯一，用于搜索
- `standard_product_relation`：标准与分类的多对多关联，包含关系类型、置信度、来源和审核状态

关联关系字段：

- `relation_type`：DIRECT_APPLICABLE / MATERIAL / SAFETY / LABELING / TEST_METHOD / PACKAGING / GENERAL / POSSIBLE
- `confidence`：0–1 的 DECIMAL，可为空，数据库 CHECK 约束
- `source_type` / `source_reference`：来源类型与引用
- `review_status`：PENDING / APPROVED / REJECTED
- 唯一约束 `(standard_id, product_category_id, relation_type)`

### 商品搜索

`GET /api/v1/products/search?q=` 使用 `EXISTS` 子查询同时匹配分类名称和别名，避免 JOIN 造成重复行；别名通过 `selectinload` 批量加载。`q` 中的 LIKE 通配符会被转义。

### 关联标准分组

`GET /api/v1/products/{id}/standards` 排除 `REJECTED` 关联，保留 `PENDING` 并在响应中显示 `reviewStatus`。

同一标准有多条关联时，按以下优先级只保留一条：

`DIRECT_APPLICABLE` > `SAFETY` > `MATERIAL` > `LABELING` > `TEST_METHOD` > `PACKAGING` > `GENERAL` > `POSSIBLE`

`confidence` 用于数据质量记录和后续 AI 关联；公开接口分组先按关系类型优先级。

分组规则：

| 分组 | 规则 |
| --- | --- |
| current | 非 POSSIBLE 关系且标准 ACTIVE |
| upcoming | 非 POSSIBLE 关系且标准 UPCOMING |
| historical | 非 POSSIBLE 关系且标准 REPLACED / ABOLISHED |
| related | POSSIBLE 关系，或标准 UNKNOWN |

组内按 `effective_date` 倒序（空值靠后）、`standard_year` 倒序、ID 倒序。响应使用 camelCase 字段。

### 前端商品搜索页

`/products` 搜索分类名称/别名；选中分类后展示 current / upcoming / historical / related 四组标准，并链接到 `/standards/{id}`。首页提供“商品查询”入口。

## 用户 AI 配置

### 配置生命周期

`AIConfig` 是请求级 Pydantic 模型，字段为 `provider`、`apiBaseUrl`、`apiKey`、`model`：

- `apiKey` 使用 `SecretStr`，repr 不输出明文
- 前后端都不把配置写入数据库
- 前端默认存 sessionStorage，可切换 localStorage
- 每次测试/识别请求把配置放在 POST body 中
- 后端只在单次请求内创建 Provider 实例并读取配置，不缓存、不写日志

### Provider 接口

`app/ai/base.py` 定义 `VisionProvider`：

- `analyze_image(image, config)`：统一图片分析
- `test_connection(config)`：连通性测试

适配器：

- OpenAI / OpenAI Compatible：Chat Completions + data URL 图片
- Anthropic：Messages API + base64 image block；根路径 Base URL 自动补 `/v1`，同时发送 `x-api-key` 与 Bearer 认证头
- Gemini：generateContent + inline_data

图片识别接口 `POST /api/v1/vision/analyze` 已实现；前端图片上传与结果展示页面尚未实现。OpenAI/Gemini 使用 models 接口测试连接；Anthropic 使用最小 Messages 请求，并兼容根路径 Base URL 与 Bearer Token 网关。

### 安全处理

- 测试连接不落库、不写日志；Provider 错误只返回通用消息，不包含上游响应正文
- 图片识别接口不保存原图/压缩图，不写日志；图片只在内存中处理
- Gemini Key 放在 `x-goog-api-key` 请求头，不拼 URL
- HTTP 客户端有超时，禁止跟随重定向
- 全局 `RequestValidationError` 处理器移除 `input`/`ctx`，避免 422 回显 API Key
- AI 路由在返回 Provider 错误前，用实际 Key 再做一次替换脱敏
- 自定义 Base URL 带来的 SSRF 面在部署文档中提示；公网部署需要网关认证/限流或出口网络限制

## 图片识别

`POST /api/v1/vision/analyze` 使用 multipart/form-data，图片和用户 AI 配置在同一个请求中。

### 图片处理

- 流式读取，>10MB 返回 413
- Pillow 校验，支持 JPEG/PNG/WebP；GIF、HEIC 或损坏文件返回 415
- 像素上限 40MP
- EXIF 方向纠正，最长边缩到 2048，透明图铺白底
- 统一重编码为 JPEG，只在内存中保留
- AI 调用后清空图片引用；`UploadFile` 在 finally 关闭，Starlette 的临时 spool 文件随 close 清理

### 结构化 JSON

`app/schemas/vision.py`：

- `product.name` / `product.categoryGuess` / `product.confidence`
- `materials` / `usages`
- `visibleText` / `visibleStandardNumbers`
- `productionDate` / `manufacturer`

`app/vision/parser.py` 从模型文本中提取 JSON，允许代码块和前后说明，但最终必须验证通过；失败返回 502，不返回模型原文。

### 标准号防猜测

1. `visibleStandardNumbers` 的每项必须能被 `StandardNoNormalizer` 规范化
2. 规范化后的编号必须出现在 `visibleText` 的压缩文本中
3. 去重后返回

Prompt 明确禁止根据商品知识推测标准号；解析层的交叉校验是第二道防线。其他标签信息放在 `visibleText`。

## 前端结构

| 目录 | 职责 |
| --- | --- |
| `src/views/` | 页面（首页、标准详情页、商品搜索页、AI 设置页） |
| `src/components/ui/` | shadcn-vue 基础组件（Button、Card、Badge） |
| `src/api/` | fetch 封装、标准接口、商品接口、AI 测试接口 |
| `src/stores/` | Pinia 状态（健康检查、标准详情、商品搜索、AI 配置） |
| `src/types/` | 与后端响应对应的类型 |
| `src/lib/` | `cn()`、标准状态、商品分组、Provider 元数据 |
| `src/router/` | 路由（`/`、`/standards/:id`、`/products`、`/settings/ai`） |

首页展示健康状态和功能状态；`/standards/:id` 展示标准详情与版本时间轴；`/products` 展示商品搜索和四组关联标准；`/settings/ai` 管理浏览器本地的 AI 配置。前端标准号检索页仍未实现。

## PWA

- `vite-plugin-pwa` 使用 `autoUpdate` 策略
- 生产构建生成 `manifest.webmanifest`、`sw.js`
- 缓存范围仅限前端静态资源，`/api/` 不进入导航回退
- 图标由 `frontend/scripts/generate-icons.py` 生成并提交

## 阶段边界

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| Phase 0 | 骨架、健康检查、MySQL/Alembic、PWA、部署与启动脚本 | 已完成 |
| Phase 1 | `standard` 表、标准号规范化、搜索与详情 API、后端测试 | 已完成 |
| Phase 2 | `standard_relation` 表、版本链 API、标准详情页与版本时间轴 | 已完成 |
| Phase 3 | `StandardDataSource`、std.samr 适配器、upsert、sync_task、管理员同步接口、每日增量任务 | 已完成 |
| Phase 4 | 商品分类、别名、标准关联、商品搜索/分组标准 API、前端商品搜索页 | 已完成 |
| Phase 5 | 用户 AI 配置、Provider 适配器、连接测试、AI 设置页 | 已完成 |
| Phase 6 | 图片识别接口、图片压缩/内存处理、结构化 JSON、标准号防猜测 | 已完成（前端上传页未开放） |
| 后续 | 前端标准检索页、AI 图片上传/结果页、关联审核管理、同步任务管理页、全文检索 | 未开始 |
| 后续 | AI 识别结果与标准库比对 | 未开始 |
| 后续 | 历史记录、收藏、权限与运维增强 | 未开始 |

后续阶段新增业务表时，从 `app/models/` 和 Alembic 迁移开始，而不是直接改数据库。
