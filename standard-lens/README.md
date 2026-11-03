# 标准镜 Standard Lens

商品标准查询与 AI 图片识别 Web 应用。

当前仓库完成 **Phase 0：项目骨架**、**Phase 1：标准基础数据模型和查询 API**、**Phase 2：标准版本关系、版本链 API 和前端详情页**、**Phase 3：标准数据同步模块**、**Phase 4：商品分类与标准关联**、**Phase 5：用户自备 AI Key 与 Provider 接口**、**Phase 6：图片识别接口**、**Phase 7：识别结果与标准库、商品分类匹配**，以及 **Phase 8：图片标准辅助核验**。

## 当前范围

已完成：

- Vue 3 + TypeScript + Vite 前端骨架，移动端优先，已接入 Vue Router、Pinia、Tailwind CSS、shadcn-vue 基础组件
- FastAPI + Pydantic 2 后端骨架，统一 `/api` 前缀，自动生成 OpenAPI 文档
- SQLAlchemy 2 + Alembic + MySQL 8 持久化接线
- `GET /api/health`：同时检查 API 进程与 MySQL 连接
- 首页调用健康检查，展示“服务正常 / 数据库未连接 / 后端离线”
- PWA manifest、Service Worker、应用图标
- Nginx、systemd、MySQL 初始化脚本
- Windows 一键启动脚本 `start-dev.bat`
- Phase 1：`standard` 表、`StandardNoNormalizer`、标准搜索与详情 API、后端单元/接口测试
- Phase 2：`standard_relation` 表、版本链 API、标准详情页与版本时间轴
- Phase 3：可替换的 `StandardDataSource`、std.samr.gov.cn 适配器、同步任务日志、管理员同步接口、每日增量定时任务
- Phase 4：`product_category` / `product_alias` / `standard_product_relation`、商品搜索与分组标准 API、前端商品搜索页
- Phase 5：用户自备 AI Provider 配置、sessionStorage/localStorage 本地保存、测试连接接口、统一 `VisionProvider` 与四类适配器
- Phase 6：`POST /api/v1/vision/analyze` 图片识别、10MB/JPEG/PNG/WebP 限制、2048px 内存压缩、严格 JSON 解析与标准号防猜测校验
- Phase 7：`POST /api/v1/vision/analyze-and-match` 识别结果与标准库/商品分类匹配、旧标准替代链提示、按状态分组排序
- Phase 8：`standard_requirement` 核验要求表、VISUAL/LABEL/DOCUMENT/LAB_TEST/MEASUREMENT 分级核验、图片辅助核验前端页、结果边界声明
- 离线标准目录：`backend/data/standards.csv`，后端首次启动且 `standard` 表为空时自动导入，之后再由定时任务增量更新

**当前未实现**：前端标准检索页（标准详情、商品搜索、AI 设置、图片辅助核验页已完成）。商品分类关联和标准核验要求目前通过 SQL/后续管理端维护。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite、Vue Router、Pinia、Tailwind CSS、shadcn-vue |
| 后端 | Python 3.12+、FastAPI、Pydantic 2、SQLAlchemy 2、Alembic、APScheduler |
| 数据库 | MySQL 8（utf8mb4） |
| 抓取/图片 | httpx、BeautifulSoup（同步）；Pillow（图片校验与内存压缩） |
| 部署 | Nginx（+ 可选 systemd） |
| PWA | vite-plugin-pwa（Workbox） |

## 目录结构

```
standard-lens/
  backend/
    app/
      api/routes/health.py     # GET /api/health
      api/routes/standards.py  # GET /api/v1/standards/...
      api/routes/products.py   # GET /api/v1/products/...
      api/routes/ai.py         # POST /api/v1/ai/test-connection
      api/routes/vision.py     # POST /api/v1/vision/analyze、analyze-and-match
      api/routes/admin.py      # POST /api/admin/sync/standards
      api/deps.py              # 管理员令牌校验
      core/config.py           # .env 配置
      db/                      # engine / session / Base
      ai/types.py              # Provider 枚举、通用结果
      ai/config.py             # 单次请求 AIConfig（SecretStr）
      ai/base.py               # VisionProvider 接口 / HTTP 基类
      ai/openai.py             # OpenAI / OpenAI Compatible
      ai/gemini.py             # Gemini
      ai/anthropic.py          # Anthropic
      vision/image.py          # 图片大小/格式校验、EXIF 方向、2048px 压缩
      vision/parser.py         # JSON 提取、结构校验、可见标准号交叉校验
      vision/service.py        # 上传读取、图片处理、AI 调用与 JSON 解析编排
      models/app_meta.py       # 基础设施表
      models/standard.py       # standard 表与状态枚举
      models/standard_relation.py  # 标准版本/关联关系
      models/product.py        # 商品分类、别名、标准关联
      models/requirement.py    # 标准核验要求与类型枚举
      models/sync_task.py      # 同步任务日志
      schemas/standard.py      # 标准 API 响应模型
      schemas/product.py       # 商品 API 响应模型
      schemas/ai.py            # AI API 响应模型
      schemas/vision.py        # 图片识别结构化响应模型
      schemas/vision_match.py  # 识别结果与标准库匹配响应模型
      schemas/sync.py          # 同步 API 响应模型
      services/standard_service.py
      services/product_service.py
      services/vision_match_service.py  # 标准号/商品分类匹配、旧标准提示、分组排序
      services/requirement_verification_service.py  # 按类型核验图片可见信息
      sync/base.py             # StandardDataSource 接口与 DTO
      sync/std_samr.py         # std.samr.gov.cn 适配器
      sync/upsert.py           # 标准/关系 upsert
      sync/service.py          # 全量/增量编排、任务日志
      sync/scheduler.py        # 每日定时任务
      utils/standard_no.py     # StandardNoNormalizer
      main.py                  # FastAPI 入口
    alembic/
      env.py
      versions/20261103_0001_create_app_meta.py
      versions/20261103_0002_create_standard_table.py
      versions/20261103_0003_create_standard_relation_table.py
      versions/20261103_0004_create_sync_task_table.py
      versions/20261103_0005_create_product_tables.py
      versions/20261103_0006_create_standard_requirement_table.py
    scripts/init_db.py         # 验证 / 创建数据库
    scripts/sync_all_standards.py    # 全量目录抓取
    scripts/export_standards_csv.py  # 导出标准目录 CSV
    scripts/import_standards_csv.py  # 导入标准目录 CSV
    data/standards.csv         # 首次启动的离线标准目录
    tests/                     # pytest 单元与接口测试（含数据源 fixtures）
    alembic.ini
    requirements.txt
    requirements-dev.txt
    .env.example
  frontend/
    src/
      api/client.ts            # 公共请求封装
      api/health.ts            # 健康检查请求
      api/standards.ts         # 标准详情 / 版本链接口
      api/products.ts          # 商品搜索 / 关联标准接口
      api/ai.ts                # AI 连接测试接口
      api/vision.ts            # 图片识别 + 标准辅助核验接口
      lib/standard-status.ts   # 标准状态标签与日期格式
      lib/product.ts           # 商品分组/关系类型标签
      lib/ai.ts                # Provider 元数据与本地存储键
      stores/health.ts         # Pinia 健康状态
      stores/standardDetail.ts # 标准详情与版本链状态
      stores/products.ts       # 商品搜索与分组标准状态
      stores/aiSettings.ts     # AI 配置、本地存储、测试连接
      stores/visionVerify.ts   # 图片选择、识别核验状态
      types/standard.ts
      types/product.ts
      types/ai.ts
      types/vision.ts
      views/HomeView.vue       # 首页
      views/StandardDetailView.vue  # /standards/:id 详情与时间轴
      views/ProductSearchView.vue   # /products 商品搜索与分组标准
      views/AISettingsView.vue      # /settings/ai AI 设置
      views/VisionVerifyView.vue    # /vision/verify 图片标准辅助核验
      components/ui/           # shadcn-vue 基础组件
      router/
    public/icons/              # PWA 图标
    scripts/generate-icons.py
    vite.config.ts             # /api 代理 + PWA
    .env.example
  deploy/
    nginx/standard-lens.conf
    mysql/init.sql
    systemd/standard-lens-api.service
  docs/
    architecture.md
  start-dev.bat
  README.md
```

## 环境要求

- Python **3.12+**
- Node.js **20+**（含 npm）
- MySQL **8**
- Windows 10/11、macOS 或 Linux

检查：

```bash
python --version
node --version
npm --version
mysql --version
```

## 快速开始

### 1. 初始化 MySQL

推荐先用管理员账号执行初始化脚本（会创建数据库和专用用户）：

```bash
mysql -u root -p < deploy/mysql/init.sql
```

脚本中的默认密码是 `change_me`，请在 `deploy/mysql/init.sql` 和 `backend/.env` 中同步修改。

如果暂时没有建库权限，也可以让 DBA 创建数据库，或把 `backend/.env` 配成有权限的账号后执行：

```bash
cd backend
python -m scripts.init_db
```

### 2. 配置并启动后端

```bash
cd backend
cp .env.example .env          # Windows: copy .env.example .env
```

编辑 `backend/.env`，至少确认这几项：

```dotenv
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=standard_lens
MYSQL_PASSWORD=change_me
MYSQL_DATABASE=standard_lens
```

创建虚拟环境并安装依赖：

```bash
# Windows
py -3.12 -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3.12 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

检查数据库并执行迁移：

```bash
python -m scripts.init_db
python -m alembic upgrade head
```

Phase 1 新增了 `standard` 表；已有环境只需重新执行 `python -m alembic upgrade head`。

启动 API：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

验证：

- 健康检查：<http://127.0.0.1:8000/api/health>
- 接口文档：<http://127.0.0.1:8000/docs>

### 3. 启动前端

另开一个终端：

```bash
cd frontend
cp .env.example .env          # Windows: copy .env.example .env
npm install
npm run dev
```

打开 <http://localhost:5173>。Vite 会把 `/api` 代理到 `http://127.0.0.1:8000`，所以前端代码里始终使用相对路径 `/api/...`。

当 API 和 MySQL 都正常时，首页显示 **“服务正常”**；MySQL 不可用但 API 存活时显示 **“服务已启动，数据库未连接”**，并给出简短错误原因。

### 4. Windows 一键启动

双击项目根目录的 `start-dev.bat`。脚本会：

1. 检查 Python 3.12+、Node.js/npm（PATH 中没有时会尝试注册表安装位置和常见目录）
2. 首次运行时创建 `backend/.venv` 并安装后端依赖
3. 从 `.env.example` 生成 `.env`（不会覆盖已有文件）
4. 检查 MySQL、执行 `alembic upgrade head`
5. 在新窗口启动 FastAPI 与 Vite
6. 等待服务就绪后自动打开 <http://localhost:5173>

首次运行需要下载依赖，时间会久一些。数据库未配置好时脚本会给出警告，但前端仍会启动，此时页面显示“数据库未连接”。

> 更新 `backend/requirements.txt` 后，删除 `backend\.venv\.deps-ok` 再运行脚本，才会重新安装依赖。

## 配置说明

所有后端配置来自 `backend/.env`（由 `app/core/config.py` 读取）：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `APP_NAME` | 服务名 | `Standard Lens API` |
| `APP_ENV` | 环境标识 | `development` |
| `DEBUG` | 调试日志 | `true` |
| `BACKEND_HOST` / `BACKEND_PORT` | 建议监听地址 | `127.0.0.1` / `8000` |
| `CORS_ORIGINS` | 允许的前端来源，逗号分隔 | `http://localhost:5173,http://127.0.0.1:5173` |
| `MYSQL_HOST` / `MYSQL_PORT` | MySQL 地址 | `127.0.0.1` / `3306` |
| `MYSQL_USER` / `MYSQL_PASSWORD` | 数据库账号 | `standard_lens` / `change_me` |
| `MYSQL_DATABASE` | 数据库名 | `standard_lens` |
| `MYSQL_CHARSET` | 字符集 | `utf8mb4` |
| `DATABASE_URL` | 完整 SQLAlchemy URL，设置后覆盖 `MYSQL_*` | 空 |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | 连接池 | `5` / `10` |
| `DB_POOL_RECYCLE` | 连接回收秒数 | `3600` |
| `DB_CONNECT_TIMEOUT` | 连接超时秒数 | `3` |
| `ADMIN_SYNC_TOKEN` | 管理员同步令牌，`X-Admin-Token` 请求头使用 | `.env.example` 中为占位值，必须修改 |
| `SYNC_SOURCE` | 数据源适配器 | `std_samr` |
| `SYNC_SCHEDULER_ENABLED` | 是否启用每日定时同步 | `true` |
| `SYNC_RECOVER_STALE_TASKS` | 启动时是否把遗留 RUNNING 任务标记 FAILED | `true` |
| `SYNC_SCHEDULE_HOUR` / `SYNC_SCHEDULE_MINUTE` | 定时执行时间（服务器本地时间） | `2` / `0` |
| `SYNC_REQUEST_INTERVAL_SECONDS` | 请求限速间隔 | `1.0` |
| `SYNC_TIMEOUT_SECONDS` | 单次请求超时 | `20` |
| `SYNC_MAX_RETRIES` | 失败重试次数 | `3` |
| `SYNC_RETRY_BACKOFF_SECONDS` | 重试退避基数 | `1.0` |
| `SYNC_PAGE_SIZE` | 列表分页大小（最大 50） | `50` |
| `SYNC_MAX_ITEMS_PER_RUN` | 单次同步最多处理条数，`0` 表示不限 | `0` |
| `SYNC_UPDATE_MAX_PAGES` | 增量同步最多扫描页数 | `20` |
| `SYNC_OVERLAP_HOURS` | 增量同步回看小时数 | `24` |
| `SYNC_USER_AGENT` | 请求 User-Agent | `StandardLens/0.4` |
| `STANDARDS_CSV_BOOTSTRAP_ENABLED` | 标准表为空时，启动阶段自动导入 `backend/data/standards.csv` | `true` |
| `STANDARDS_CSV_PATH` | 可选，覆盖 CSV 路径 | `backend/data/standards.csv` |
| `AI_REQUEST_TIMEOUT_SECONDS` | 用户 AI 请求超时秒数 | `20` |

前端配置来自 `frontend/.env`：

| 变量 | 说明 |
| --- | --- |
| `VITE_API_BASE_URL` | 留空表示同源 `/api`；跨域部署时才需要填写完整地址 |
| `VITE_PROXY_TARGET` | Vite 开发代理目标，默认 `http://127.0.0.1:8000` |

`.env` 已被 `.gitignore` 忽略，不要提交真实密码。后续接入 AI Key 时，也只能放在后端 `.env` 或用户本地存储中。

> 首次全量初始化由管理员手动触发（见下文“标准数据同步”）。定时任务只执行增量；未初始化时会跳过并记录日志。全量同步默认不限条数，受 1 秒/请求限速影响可能持续很久，建议先设置 `SYNC_MAX_ITEMS_PER_RUN=50` 做小规模验证。

## API

### `GET /api/health`

只要 API 进程存活就返回 HTTP 200，通过 `status` 区分整体状态。

```json
{
  "status": "ok",
  "service": "Standard Lens API",
  "version": "0.9.0",
  "environment": "development",
  "database": {
    "status": "ok",
    "latency_ms": 1.8,
    "detail": null
  },
  "checked_at": "2026-11-03T02:30:00+00:00",
  "latency_ms": 2.4
}
```

- `status`：`ok`（API + DB 正常）或 `degraded`（API 存活，DB 不可用）
- `database.status`：`ok` / `down`
- `database.detail`：数据库失败时的简短原因，便于本地排查

数据库不可用时：

```json
{
  "status": "degraded",
  "database": {
    "status": "down",
    "latency_ms": null,
    "detail": "无法连接 MySQL，请确认 MySQL 8 已启动，并检查 MYSQL_HOST / MYSQL_PORT。"
  }
}
```

### 标准数据模型

`standard` 表的核心字段：

| 字段 | 说明 |
| --- | --- |
| `standard_no` | 展示用标准号，保留原始写法 |
| `normalized_no` | 规范化标准号，**唯一索引**，用于精确匹配 |
| `standard_name` | 标准名称 |
| `standard_type` | 标准类型，如 `GB`、`GB/T`、`QB/T` |
| `status` | `UPCOMING` / `ACTIVE` / `REPLACED` / `ABOLISHED` / `UNKNOWN` |
| `publish_date` / `effective_date` / `expiry_date` | 发布、实施、失效日期 |
| `standard_year` | 标准年份 |
| `scope` | 适用范围 |
| `source` / `source_url` | 数据来源与官方链接 |
| `created_at` / `updated_at` | 创建、更新时间 |

标准号规范化由 `StandardNoNormalizer` 完成：

- 统一全角字符、大小写与空白
- `—`、`–`、`－` 等各种横线统一为 `-`
- 冒号年份分隔（如 ISO 风格）也统一为 `-`，作为内部匹配键
- 规范格式为 `PREFIX NUMBER-YEAR`

```text
gb4806.11-2023    -> GB 4806.11-2023
GB4806.11-2023    -> GB 4806.11-2023
GB 4806.11—2023   -> GB 4806.11-2023
ＧＢ４８０６．１１－２０２３ -> GB 4806.11-2023
```

### 标准关系

`standard_relation` 保存两个标准之间的有向关系：

| 字段 | 说明 |
| --- | --- |
| `source_standard_id` | 关系起点 |
| `target_standard_id` | 关系终点 |
| `relation_type` | `REPLACES` / `REPLACED_BY` / `AMENDS` / `AMENDED_BY` / `RELATED` |
| `created_at` | 创建时间 |

方向按字段名理解，例如 `source REPLACES target` 表示 source 是新版本；`source REPLACED_BY target` 表示 source 是旧版本。版本链接口会双向遍历，因此两种存法都能工作。

- `REPLACES` / `REPLACED_BY` / `AMENDS` / `AMENDED_BY` 属于版本谱系，参与版本链
- `RELATED` 是“相关标准”，不参与版本链，后续用于相关推荐
- 同一条边不能重复，标准不能关联自身

### `GET /api/v1/standards/search`

查询参数：

| 参数 | 说明 |
| --- | --- |
| `q` | 必填，标准号或标准名称，最长 200 字符 |
| `limit` | 1–100，默认 20 |
| `offset` | 默认 0 |

搜索规则：

1. 标准号精确匹配（忽略大小写）
2. `normalized_no` 匹配（支持不同空格、横线、全角写法）
3. 标准名称模糊匹配
4. 精确命中排在名称命中之前

```bash
curl "http://127.0.0.1:8000/api/v1/standards/search?q=gb4806.11-2023"
curl --get --data-urlencode "q=食品接触" "http://127.0.0.1:8000/api/v1/standards/search"
```

响应示例：

```json
{
  "query": "gb4806.11-2023",
  "normalized_query": "GB 4806.11-2023",
  "total": 1,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "standard_no": "GB 4806.11-2023",
      "normalized_no": "GB 4806.11-2023",
      "standard_name": "食品安全国家标准 食品接触用橡胶材料及制品",
      "standard_type": "GB",
      "status": "ACTIVE",
      "publish_date": "2023-09-06",
      "effective_date": "2024-04-01",
      "expiry_date": null,
      "standard_year": 2023,
      "source": "openstd",
      "source_url": "https://openstd.samr.gov.cn/"
    }
  ]
}
```

### `GET /api/v1/standards/{id}`

返回标准详情，在搜索摘要字段之外额外包含 `scope`、`created_at`、`updated_at`。ID 不存在时返回 `404`：

```json
{ "detail": "标准不存在" }
```

### `GET /api/v1/standards/{id}/versions`

返回该标准所在的完整版本链（JSON 数组），从新到旧排序。无论从链中的哪个标准发起请求，都会返回同一组版本。

排序规则：标准年份优先（缺失时依次使用 `effectiveDate`、`publishDate` 的年份），同年按生效日期倒序。

每个元素使用 camelCase 字段：
`id`、`standardNo`、`standardName`、`status`、`publishDate`、`effectiveDate`、`expiryDate`、`standardYear`、`isHistorical`、`isCurrent`、`isUpcoming`。

状态与标记规则：

| status | 含义 | 标记 |
| --- | --- | --- |
| `ACTIVE` | 当前现行 | `isCurrent=true` |
| `UPCOMING` | 已发布但尚未实施 | `isUpcoming=true` |
| `REPLACED` | 已被替代 | `isHistorical=true`，前端显示“旧标准” |
| `ABOLISHED` | 已废止 | `isHistorical=true`，前端显示“已废止” |
| `UNKNOWN` | 状态未知 | 三个标记均为 `false` |

**现行状态只由 `status` 决定，不以年份大小或排序位置推断。** 例如一个 2030 年被废止的标准不会因为年份最大而成为当前版本。

`effectiveDate` 字段始终返回，没有数据时为 `null`；前端会显示“未提供”。

响应示例：

```json
[
  {
    "id": 3,
    "standardNo": "GB 4806.11-2027",
    "standardName": "食品接触用橡胶材料及制品（2027）",
    "status": "UPCOMING",
    "publishDate": "2027-01-10",
    "effectiveDate": "2027-07-01",
    "expiryDate": null,
    "standardYear": 2027,
    "isHistorical": false,
    "isCurrent": false,
    "isUpcoming": true
  },
  {
    "id": 1,
    "standardNo": "GB 4806.11-2024",
    "standardName": "食品接触用橡胶材料及制品（2024）",
    "status": "ACTIVE",
    "publishDate": "2024-01-15",
    "effectiveDate": "2024-05-01",
    "expiryDate": null,
    "standardYear": 2024,
    "isHistorical": false,
    "isCurrent": true,
    "isUpcoming": false
  },
  {
    "id": 2,
    "standardNo": "GB 4806.11-2018",
    "standardName": "食品接触用橡胶材料及制品（2018）",
    "status": "REPLACED",
    "publishDate": "2018-01-01",
    "effectiveDate": "2018-07-01",
    "expiryDate": "2024-04-30",
    "standardYear": 2018,
    "isHistorical": true,
    "isCurrent": false,
    "isUpcoming": false
  }
]
```

### 前端标准详情页

访问 `/standards/{id}`，页面会同时加载标准详情和版本链，并展示：

- 标准号、名称、当前状态、发布/实施/失效日期、来源和官方链接
- 版本时间轴，从新到旧排列
- 当前现行（绿色）、即将实施（蓝色）、旧标准（琥珀色）、已废止（红色）标签
- 历史版本明确显示“旧标准，已被后续版本替代”或“已废止，不再作为现行标准”
- 每条版本都显示生效日期，缺失时显示“未提供”

### 商品分类与标准关联

新增三张表：

| 表 | 字段 |
| --- | --- |
| `product_category` | `id`、`parent_id`、`name`、`description` |
| `product_alias` | `id`、`category_id`、`alias`（同一分类内唯一） |
| `standard_product_relation` | `id`、`standard_id`、`product_category_id`、`relation_type`、`confidence`、`source_type`、`source_reference`、`review_status` |

`relation_type`：`DIRECT_APPLICABLE`、`MATERIAL`、`SAFETY`、`LABELING`、`TEST_METHOD`、`PACKAGING`、`GENERAL`、`POSSIBLE`。

`review_status`：`PENDING`、`APPROVED`、`REJECTED`。公开接口排除 `REJECTED`，保留 `PENDING` 并在响应中带上 `reviewStatus`，方便前端显示“待审核”。

`confidence` 为 0–1 的小数，可为空。`source_type` 目前可用 `MANUAL`、`OFFICIAL` 等字符串；`source_reference` 保存来源链接或说明。

### 标准核验要求

`standard_requirement` 保存从标准中拆出的可核验要求：

| 字段 | 说明 |
| --- | --- |
| `id` | 主键 |
| `standard_id` | 关联 `standard.id`，删除标准时级联删除 |
| `chapter` | 章节号或条款号，例如 `4.1`、`5.2.3` |
| `requirement_type` | `VISUAL` / `LABEL` / `DOCUMENT` / `LAB_TEST` / `MEASUREMENT` |
| `requirement_text` | 要求原文或摘要 |
| `verification_method` | 建议核验方式，例如“查看包装标签”“按标准方法测量” |

图片核验边界：

| 类型 | 图片可以做什么 |
| --- | --- |
| `VISUAL` | 允许 AI 辅助判断图片中可见的外观/结构信息；只能说明“图片中可见”，不能判定完整符合 |
| `LABEL` | 允许 AI 辅助判断标签、标准号、厂家、日期、材质等可见文字 |
| `DOCUMENT` | 只提示需要证书、检测报告或合规文件，不判断是否已具备 |
| `LAB_TEST` | 明确显示“无法通过图片判断”，需要实验室检测 |
| `MEASUREMENT` | 没有可靠测量信息时显示“无法判断”；照片中的数值不能替代规范测量 |

要求数据目前通过 SQL 或后续管理端维护。示例：

```sql
INSERT INTO standard_requirement (
    standard_id, chapter, requirement_type, requirement_text, verification_method
) VALUES
(1, '4.1', 'LABEL', '包装上应标注执行标准号。', '查看包装标签'),
(1, '4.2', 'VISUAL', '产品外观应清洁、无破损。', '目视检查，仅记录图片可见信息'),
(1, '5.1', 'LAB_TEST', '材料迁移量应符合限量要求。', '按标准方法进行实验室检测'),
(1, '5.2', 'DOCUMENT', '应提供符合性声明或检测报告。', '查验相关文件');
```

### `GET /api/v1/products/search?q=`

按商品分类名称或别名模糊搜索：

| 参数 | 说明 |
| --- | --- |
| `q` | 必填，名称或别名，最长 200 字符 |
| `limit` | 1–100，默认 20 |
| `offset` | 默认 0 |

响应字段为 camelCase：

```json
{
  "query": "奶瓶",
  "total": 1,
  "limit": 20,
  "offset": 0,
  "items": [
    {
      "id": 1,
      "name": "奶瓶",
      "description": "婴幼儿喂养用品",
      "parentId": null,
      "aliases": ["feeding bottle", "婴儿奶瓶"]
    }
  ]
}
```

### `GET /api/v1/products/{id}/standards`

返回商品分类及其关联标准，固定分组为 `current`、`upcoming`、`historical`、`related`：

| 分组 | 规则 |
| --- | --- |
| `current` | 非 `POSSIBLE` 关系且标准状态为 `ACTIVE` |
| `upcoming` | 非 `POSSIBLE` 关系且标准状态为 `UPCOMING` |
| `historical` | 非 `POSSIBLE` 关系且标准状态为 `REPLACED` / `ABOLISHED` |
| `related` | `POSSIBLE` 关系，或标准状态为 `UNKNOWN` |

同一标准有多条关联时只返回一条，按关系优先级选择：

`DIRECT_APPLICABLE` > `SAFETY` > `MATERIAL` > `LABELING` > `TEST_METHOD` > `PACKAGING` > `GENERAL` > `POSSIBLE`。`confidence` 用于数据质量记录和后续 AI 关联，不改变公开接口的分组优先级。

组内排序：实施日期从新到旧（空值靠后），再按标准年份和 ID 倒序。

每条标准返回：`id`、`standardNo`、`standardName`、`status`、`effectiveDate`、`expiryDate`、`relationType`、`reviewStatus`。

```json
{
  "product": {
    "id": 1,
    "name": "奶瓶",
    "description": "婴幼儿喂养用品",
    "parentId": null,
    "aliases": ["feeding bottle", "婴儿奶瓶"]
  },
  "current": [
    {
      "id": 12,
      "standardNo": "GB 4806.7-2023",
      "standardName": "食品接触用塑料材料及制品",
      "status": "ACTIVE",
      "effectiveDate": "2024-05-01",
      "expiryDate": null,
      "relationType": "DIRECT_APPLICABLE",
      "reviewStatus": "APPROVED"
    }
  ],
  "upcoming": [],
  "historical": [],
  "related": []
}
```

分类不存在时返回 `404 {"detail":"商品分类不存在"}`。

按当前分类 ID 查询，不自动递归子分类；子分类可以单独搜索和打开。

### 前端商品搜索页

访问 `/products`（首页右上角“商品查询”入口）：

- 输入商品名称或别名搜索
- 自动选中第一个分类并加载关联标准
- 按“当前现行 / 即将实施 / 历史版本 / 相关标准”分组展示
- 每条标准显示标准号、名称、状态、关系类型、生效/失效日期和待审核标记
- 点击标准进入 `/standards/{id}` 查看版本时间轴

### `POST /api/v1/ai/test-connection`

使用请求体中的用户配置测试 AI Provider 连通性。配置只在本次请求内使用，不落库、不写日志。

请求体（API Key 只放在 JSON body，不能放 URL/query）：

```json
{
  "provider": "openai",
  "apiBaseUrl": "https://api.openai.com/v1",
  "apiKey": "sk-user-key",
  "model": "gpt-4o-mini"
}
```

`provider` 取值：`openai`、`gemini`、`anthropic`、`openai_compatible`。OpenAI Compatible 必须填写 `apiBaseUrl`；其他 Provider 留空时使用默认地址，也可以覆盖为自定义 Base URL。

响应：

```json
{
  "ok": true,
  "provider": "openai",
  "model": "gpt-4o-mini",
  "message": "连接成功",
  "latencyMs": 123
}
```

- OpenAI / Gemini / OpenAI Compatible 通过 models 接口验证连通性
- Anthropic 发送一次最小 Messages 请求（`max_tokens=1`），兼容只提供 Messages、不提供 models 的网关；不保证具体模型一定可用
- 网络/认证失败返回 `ok: false` 和脱敏后的提示
- 配置格式错误返回 `422`，校验错误不会回显提交的 `apiKey`
- 该接口不需要管理员令牌；它不读取系统 Key，也不访问数据库

### `POST /api/v1/vision/analyze`

`multipart/form-data`：

| 字段 | 说明 |
| --- | --- |
| `image` | 图片文件，最大 10MB，支持 JPEG/PNG/WebP（HEIC 暂不支持） |
| `provider` | `openai` / `gemini` / `anthropic` / `openai_compatible` |
| `apiKey` | 用户自己的 API Key |
| `apiBaseUrl` | 可选，官方 Provider 留空使用默认地址 |
| `model` | 支持图片输入的多模态模型 |

图片会在内存中校验、纠正 EXIF 方向并压缩到最长边 2048，然后转成 JPEG 交给 AI；**不保存原图，不写入磁盘，不写日志**。

返回固定结构（camelCase）：

```json
{
  "product": {
    "name": "塑料奶瓶",
    "categoryGuess": "奶瓶",
    "confidence": 0.92
  },
  "materials": ["PP", "硅胶"],
  "usages": ["喂养"],
  "visibleText": [
    "GB 4806.7-2024",
    "生产日期 2024-05-01",
    "某某塑料制品有限公司"
  ],
  "visibleStandardNumbers": ["GB 4806.7-2024"],
  "productionDate": "2024-05-01",
  "manufacturer": "某某塑料制品有限公司"
}
```

- `visibleStandardNumbers` 会做格式规范化，并只保留同时出现在 `visibleText` 中的编号；不在可见文字中出现的编号会被丢弃，防止模型根据商品知识猜测
- 其他标签信息（成分、净含量、警示语等）放在 `visibleText`
- 413：图片超过 10MB 或像素过大
- 415：不是 JPEG/PNG/WebP，或图片损坏、HEIC
- 422：表单或 AI 配置校验失败（不回显 Key）
- 502：Provider 调用失败或模型没有返回合法 JSON

### `POST /api/v1/vision/analyze-and-match`

识别图片，并把识别结果与数据库中的标准、商品分类关联起来。表单字段与 `/vision/analyze` 完全相同，额外需要数据库连接。图片处理、AI 配置和日志规则也相同：不保存图片、不写 Key。

处理顺序：

1. 调用 AI 得到 `product`、`materials`、`usages`、`visibleStandardNumbers`
2. 对每个可见标准号做 `StandardNoNormalizer` 规范化，再按 `normalized_no` 精确查询 `standard` 表
3. 用商品名称、类别、材质、用途匹配 `product_category` 与 `product_alias`（最多 5 个分类）
4. 通过 `standard_product_relation` 查询匹配分类关联的标准，按状态分组
5. 查询检测标准的替代关系与版本链，生成旧标准提示

返回结构：

```json
{
  "imageAnalysis": {
    "product": {
      "name": "婴儿塑料奶瓶",
      "categoryGuess": "婴儿奶瓶",
      "confidence": 0.95
    },
    "materials": ["PP", "硅胶"],
    "usages": ["婴儿喂养"],
    "visibleText": ["GB 1000-2018", "生产日期 2024-05-01"],
    "visibleStandardNumbers": ["GB 1000-2018"],
    "productionDate": "2024-05-01",
    "manufacturer": "示例公司"
  },
  "detectedStandards": [
    {
      "id": 12,
      "standardNo": "GB 1000-2018",
      "standardName": "旧版塑料奶瓶标准",
      "status": "REPLACED",
      "statusLabel": "旧标准",
      "publishDate": "2018-01-01",
      "effectiveDate": "2018-07-01",
      "expiryDate": "2024-04-30",
      "relationType": "DETECTED",
      "isHistorical": true,
      "replacedBy": [
        {
          "id": 13,
          "standardNo": "GB 1000-2024",
          "standardName": "现行塑料奶瓶标准",
          "status": "ACTIVE",
          "statusLabel": "当前现行",
          "publishDate": "2024-01-01",
          "effectiveDate": "2024-05-01",
          "expiryDate": null,
          "relationType": "REPLACES",
          "isHistorical": false
        }
      ],
      "latestCurrent": [
        {
          "id": 13,
          "standardNo": "GB 1000-2024",
          "standardName": "现行塑料奶瓶标准",
          "status": "ACTIVE",
          "statusLabel": "当前现行",
          "publishDate": "2024-01-01",
          "effectiveDate": "2024-05-01",
          "expiryDate": null,
          "relationType": "LATEST_CURRENT",
          "isHistorical": false
        }
      ],
      "notice": "图片上的标准 GB 1000-2018 是旧标准，实施于 2018-07-01；当前替代标准：GB 1000-2024（当前现行）；当前最新现行标准：GB 1000-2024（当前现行）。"
    }
  ],
  "relatedStandards": {
    "current": [],
    "upcoming": [],
    "historical": [],
    "other": []
  },
  "imageStored": false,
  "matchedCategories": [
    {
      "id": 3,
      "name": "奶瓶",
      "description": null,
      "parentId": null,
      "aliases": ["婴儿奶瓶"],
      "score": 8.0,
      "matchedTerms": ["婴儿塑料奶瓶", "婴儿奶瓶"]
    }
  ],
  "unmatchedVisibleStandardNumbers": [],
  "standardVerification": [
    {
      "standardId": 12,
      "standardNo": "GB 1000-2018",
      "standardName": "旧版塑料奶瓶标准",
      "status": "REPLACED",
      "statusLabel": "旧标准",
      "effectiveDate": "2018-07-01",
      "replacementStandards": [
        {
          "id": 13,
          "standardNo": "GB 1000-2024",
          "standardName": "现行塑料奶瓶标准",
          "status": "ACTIVE",
          "statusLabel": "当前现行",
          "publishDate": "2024-01-01",
          "effectiveDate": "2024-05-01",
          "expiryDate": null,
          "relationType": "REPLACES",
          "isHistorical": false
        }
      ],
      "latestCurrent": [],
      "lifecycleNotice": "图片上的标准 GB 1000-2018 是旧标准……",
      "requirements": [
        {
          "requirementId": 1,
          "chapter": "4.1",
          "requirementType": "LABEL",
          "requirementText": "包装上应标注执行标准号。",
          "verificationMethod": "查看包装标签",
          "status": "OBSERVED",
          "statusLabel": "图片中可见",
          "imageCheckable": true,
          "evidence": ["可见标准号：GB 1000-2018"],
          "message": "AI 辅助：图片中可见上述信息；仅代表图片可见内容，不代表商品满足该标准的全部要求。"
        },
        {
          "requirementId": 2,
          "chapter": "5.1",
          "requirementType": "LAB_TEST",
          "requirementText": "材料迁移量应符合限量要求。",
          "verificationMethod": "按标准方法进行实验室检测",
          "status": "NOT_POSSIBLE",
          "statusLabel": "无法通过图片判断",
          "imageCheckable": false,
          "evidence": [],
          "message": "无法通过图片判断，需要按标准方法进行实验室检测。"
        }
      ],
      "observedCount": 1,
      "partialCount": 0,
      "notObservedCount": 0,
      "externalCheckCount": 1,
      "summary": "图片可核对 2 项要求：1 项在图片中可见，1 项需证书、实验或测量。"
    }
  ],
  "verificationNotice": "图片分析只能辅助核对可见信息，不能替代实验检测、检测报告或合规认证。"
}
```

字段与规则：

- `detectedStandards`：图片中明确出现、且能在标准库中精确找到的标准；`relationType` 固定为 `DETECTED`
- 每个标准条目都包含 `standardNo`、`standardName`、`status`、`statusLabel`、`publishDate`、`effectiveDate`、`expiryDate`、`relationType`、`isHistorical`
- `replacedBy`：数据库中直接替代该标准的标准；`latestCurrent`：该标准版本链中的现行标准
- 旧标准（`REPLACED`）和已废止标准（`ABOLISHED`）的 `notice` 会说明图片上的标准、当前状态、当年实施日期、当前替代标准、当前最新现行标准
- `relatedStandards.current` 按 `effectiveDate` 从新到旧；`upcoming` 从近到远；`historical` 从新到旧；`other` 包含 `POSSIBLE` 关联或状态未知的标准
- `relationType`：`DETECTED` / `REPLACES` / `LATEST_CURRENT`，商品关联时为 `DIRECT_APPLICABLE`、`MATERIAL`、`SAFETY` 等
- `unmatchedVisibleStandardNumbers`：AI 看到但数据库没有的标准号；它们**不会**被补全或生成标准条目
- `standardVerification`：对每个检测标准读取 `standard_requirement` 并逐项核验；`requirements` 按章节自然排序
- `status` 取值：`OBSERVED`（图片中可见）、`PARTIAL`（部分可见，需人工核对）、`NOT_OBSERVED`（图片中未观察到）、`NEEDS_DOCUMENT`（需要证书/文档）、`NOT_POSSIBLE`（无法通过图片判断）、`CANNOT_VERIFY`（无法判断）
- 只有 `VISUAL` / `LABEL` 项会因图片证据标为 `OBSERVED` / `PARTIAL`；`DOCUMENT` / `LAB_TEST` / `MEASUREMENT` 的 `imageCheckable` 为 `false`
- `replacementStandards` 是直接替代标准；`latestCurrent` 是版本链中的现行标准；旧标准组同时保留 `lifecycleNotice`
- `verificationNotice` 固定返回核验边界声明；前端必须原样展示，不能用图片结果宣称商品完整符合标准
- 所有最终标准都来自数据库；AI 只负责从图片提取文本，不生成标准编号
- `imageStored` 固定为 `false`
- 503：标准库查询失败；500：识别成功但匹配或核验过程失败

### `POST /api/admin/sync/standards`（管理员）

创建同步任务并在后台线程执行，接口立即返回 `202`，不会等待整次同步结束。

请求头：

```text
X-Admin-Token: <backend/.env 中的 ADMIN_SYNC_TOKEN>
```

查询参数：

| 参数 | 说明 |
| --- | --- |
| `mode=auto` | 默认。没有成功同步记录时全量，否则增量 |
| `mode=full` | 强制全量 |
| `mode=incremental` | 仅增量；尚未初始化时返回 `400` |

```bash
curl -X POST "http://127.0.0.1:8000/api/admin/sync/standards?mode=auto" \
  -H "X-Admin-Token: change_me_admin_token"
```

```json
{
  "task_id": 12,
  "source": "std_samr",
  "status": "RUNNING",
  "mode": "full",
  "message": "同步任务已启动"
}
```

- 已有任务在运行时返回 `409`
- 未初始化就请求增量返回 `400`
- 缺少或错误令牌返回 `401`
- 未配置 `ADMIN_SYNC_TOKEN` 时返回 `503`

### 手工插入一条测试数据

即使没有同步任务，也可以先用 SQL 插入数据验证接口：

```sql
INSERT INTO standard (
    standard_no, normalized_no, standard_name, standard_type, status,
    publish_date, effective_date, standard_year, scope, source, source_url
) VALUES (
    'GB 4806.11-2024', 'GB 4806.11-2024',
    '食品安全国家标准 食品接触用橡胶材料及制品', 'GB', 'ACTIVE',
    '2024-01-15', '2024-05-01', 2024,
    '适用于食品接触用橡胶材料及制品。', 'openstd',
    'https://openstd.samr.gov.cn/'
);
```

再插入一个旧版本并建立替代关系（ID 以实际插入结果为准）：

```sql
INSERT INTO standard (
    standard_no, normalized_no, standard_name, standard_type, status,
    publish_date, effective_date, expiry_date, standard_year, source, source_url
) VALUES (
    'GB 4806.11-2018', 'GB 4806.11-2018',
    '食品安全国家标准 食品接触用橡胶材料及制品（2018）', 'GB', 'REPLACED',
    '2018-01-01', '2018-07-01', '2024-04-30', 2018, 'openstd',
    'https://openstd.samr.gov.cn/'
);

-- 新版本 REPLACES 旧版本（source 是 2024，target 是 2018）
-- 下面假设两条 INSERT 的 ID 分别为 1、2；有历史数据时请按实际 ID 调整
INSERT INTO standard_relation (source_standard_id, target_standard_id, relation_type)
VALUES (1, 2, 'REPLACES');
```

再插入商品分类、别名和一条已审核的直接关联：

```sql
INSERT INTO product_category (name, description)
VALUES ('奶瓶', '婴幼儿喂养用品');

INSERT INTO product_alias (category_id, alias)
VALUES (1, '婴儿奶瓶'), (1, 'feeding bottle');

INSERT INTO standard_product_relation (
    standard_id, product_category_id, relation_type,
    confidence, source_type, source_reference, review_status
) VALUES (
    1, 1, 'DIRECT_APPLICABLE',
    1.0000, 'MANUAL', NULL, 'APPROVED'
);
```

然后访问 `http://localhost:5173/standards/1` 查看版本时间轴，或访问 `http://localhost:5173/products` 搜索“奶瓶”（ID 以实际插入结果为准）。

## 标准数据同步

### 数据源接口

`app/sync/base.py` 定义可替换的数据源接口：

| 方法 | 作用 |
| --- | --- |
| `source_name()` | 稳定数据源标识，写入 `standard.source` / `sync_task.source` |
| `fetch_list()` | 全量初始化，逐页产出标准 |
| `fetch_updates(since)` | 增量同步，产出 `since` 之后发布/更新的标准 |
| `fetch_detail(item)` | 拉取单条标准详情、日期和替代关系 |

第一个适配器是 `StdSamrDataSource`：

- 来源：全国标准信息公共服务平台 <https://std.samr.gov.cn>
- 列表：JSON 接口 `gbQueryPage`，按发布日期倒序分页
- 详情：HTML 页面 `gbDetailed`，使用 BeautifulSoup 解析
- 解析标准号、名称、状态、发布/实施/废止日期、标准类型、替代/被替代关系和官方详情链接
- `source_url` 保存官方详情页地址
- **不下载、不重新托管标准 PDF**
- 请求使用 httpx，带连接/读取超时、限速、指数退避重试和自定义 User-Agent

> 使用前请确认目标站点当前的服务条款。本项目只保存标准元数据和官方链接，不下载或重新托管标准全文/PDF。

### 全量与增量

- **首次初始化**：管理员调用同步接口，`mode=auto` 会自动选择全量
- **之后**：`mode=auto` 走增量；每日定时任务只执行增量
- 增量回看最近 `SYNC_OVERLAP_HOURS` 小时，默认 24 小时，避免边界漏数
- 每日定时任务在尚未完成首次初始化时不会自动跑全量，而是跳过并记录警告；先手动完成初始化
- 增量扫描最多 `SYNC_UPDATE_MAX_PAGES` 页，默认 20

### 批量目录同步（推荐首次使用）

完整目录约 8 万条。逐条抓详情页会持续很多小时，因此提供目录批量脚本：

```bash
cd backend
.venv/Scripts/python -m scripts.sync_all_standards
```

默认只读取列表页并 upsert 标准元数据，不抓详情页；每 200 条批量提交一次。已存在的标准会保留详情页补充的可选字段。预计约 30 分钟（1 秒/请求限速）。

需要同时补全废止日期和替代关系时：

```bash
.venv/Scripts/python -m scripts.sync_all_standards --details
```

`--details` 会为每条标准抓一次详情页，8 万条约需十几小时，适合分批执行：

```bash
.venv/Scripts/python -m scripts.sync_all_standards --details --limit 1000
```

`--interval` 可调整请求间隔，`--limit` 可限制本次条数。脚本会创建正常的 `sync_task` 记录，可通过任务 ID 查看进度。

### 离线 CSV 初始化

仓库内置一份标准目录 CSV：`backend/data/standards.csv`，用于新环境第一次启动时快速建立标准库，避免每位开发者都重新抓取数万条数据。

启动顺序：

1. 后端启动时检查 `standard` 表
2. 表为空：在导入 CSV 完成前不启动定时同步
3. 表非空：跳过 CSV，直接使用现有数据
4. CSV 导入完成后，再启动每日增量同步

配置：

- `STANDARDS_CSV_BOOTSTRAP_ENABLED=true`
- `STANDARDS_CSV_PATH` 可选，默认 `backend/data/standards.csv`

手工导出/导入：

```bash
cd backend
# 导出当前数据库全部标准
.venv/Scripts/python -m scripts.export_standards_csv

# 手工导入（幂等 upsert，按 normalized_no）
.venv/Scripts/python -m scripts.import_standards_csv
```

CSV 列为：`standard_no`、`normalized_no`、`standard_name`、`standard_type`、`status`、`publish_date`、`effective_date`、`expiry_date`、`standard_year`、`scope`、`source`、`source_url`。

CSV 只包含标准元数据，不包含条款正文、商品分类、商品关联或版本关系。版本关系仍通过详情同步补齐。

### 限速、重试与超时

- `SYNC_REQUEST_INTERVAL_SECONDS` 默认 1 秒/请求
- `SYNC_TIMEOUT_SECONDS` 默认 20 秒
- `SYNC_MAX_RETRIES` 默认 3 次（指数退避）
- 对 429、500、502、503、504、超时和传输错误重试；4xx（除 429）不重试

全量目录约 8 万条标准。管理接口的全量模式会逐条抓详情页，按 1 秒/请求计算会持续很久；首次初始化优先使用上面的 `scripts.sync_all_standards` 目录批量脚本，之后再按需分批补详情和关系。也可以先设置 `SYNC_MAX_ITEMS_PER_RUN=50` 做小规模验证。

### 写入与关系

- 标准按唯一 `normalized_no` 使用数据库 upsert：
  - MySQL：`INSERT ... ON DUPLICATE KEY UPDATE`
  - SQLite 测试：`ON CONFLICT DO UPDATE`
- 源数据缺失的可选字段不会覆盖数据库中已有值
- 替代关系幂等写入 `standard_relation`
- 新标准详情引用的旧版本如果不在本次增量窗口内，会额外拉取一次旧版本详情，更新其状态和废止日期后再写关系
- 当前来源提供 `REPLACES` / `REPLACED_BY`；`AMENDS` / `RELATED` 已在数据模型中支持，但该来源详情页未暴露这两类关系

### 同步日志

每次同步写入 `sync_task`：

| 字段 | 说明 |
| --- | --- |
| `source` | `std_samr` |
| `started_at` / `finished_at` | UTC 时间 |
| `total_count` / `success_count` / `failed_count` | 处理、成功、失败条数 |
| `status` | `RUNNING` / `SUCCESS` / `PARTIAL` / `FAILED` |
| `error_message` | 失败摘要（详情失败、关系目标缺失、达到上限等） |

计数按列表/增量返回的标准条数统计；为建立替代关系而额外刷新的历史版本不计入 `total_count`，其抓取失败会写入 `error_message`。

同时通过应用日志输出开始、失败、结束信息。单个标准详情失败不会中断整次同步；列表/传输致命错误会把任务标记为 `FAILED` 或 `PARTIAL`。查看最近任务：

```sql
SELECT id, source, status, total_count, success_count, failed_count,
       started_at, finished_at, error_message
FROM sync_task
ORDER BY id DESC
LIMIT 5;
```

### 增量限制

来源列表按发布日期倒序，因此“发布新标准”的增量能可靠覆盖。已有标准的纯状态变化（例如“即将实施 → 现行”“现行 → 废止”）不会产生新的发布日期，可能不在增量窗口内：

- 新标准引用旧版本时，会通过“关系目标刷新”更新旧版本状态和废止日期
- 如果标准只是单独废止、或被新标准引用但新标准发布日期已久远，建议每周或每月执行一次 `mode=full` 全量刷新

这是一项来源限制，不是同步任务失败；任务日志会记录本次处理的范围。

### 单进程说明

定时任务使用进程内 APScheduler，任务互斥锁也在进程内。systemd 示例因此固定 `--workers 1`；如果要多 worker 部署，请把调度器拆成独立进程并保持同步任务单实例。

## 用户 AI 配置

### Provider 与适配器

统一接口见 `app/ai/base.py`：

```python
class VisionProvider:
    async def analyze_image(self, image: bytes, config: AIConfig) -> VisionAnalysisResult: ...
    async def test_connection(self, config: AIConfig) -> ProviderTestResult: ...
```

适配器：

- `OpenAIProvider`：OpenAI Chat Completions，支持图片 data URL
- `OpenAICompatibleProvider`：OpenAI 兼容协议，自定义 Base URL
- `GeminiProvider`：Google Generative Language `generateContent`，`inline_data`
- `AnthropicProvider`：Messages API，base64 image block；兼容根路径 Base URL（自动补 `/v1`）和 Bearer Token 网关，同时发送 `x-api-key` 与 `Authorization: Bearer`

用户配置字段：`provider`、`apiBaseUrl`、`apiKey`、`model`。`AIConfig` 使用 `SecretStr` 保存 Key，repr/序列化不会输出明文。

`analyze_image` 已实现并通过 MockTransport 测试，但**暂未开放图片上传接口和识别结果页面**；当前只开放测试连接。

### 浏览器存储

- 默认 `sessionStorage`：只在当前标签页有效，关闭标签页清除
- 可选 `localStorage`：当前设备长期保留，公共电脑不建议使用
- 切换保存位置后，“保存配置”会写入目标存储并删除另一存储中的副本
- 保存只发生在浏览器，不调用后端
- API Key 输入框默认 `type=password`，可点击眼睛图标临时显示

### 后端安全边界

- 测试连接接口只接收本次请求的配置，不写数据库、不缓存、不写日志
- 前端把配置放在 POST JSON body，不放在 URL/query
- Provider 错误只返回通用提示；不返回上游响应正文
- 全局 422 处理器移除了 Pydantic 错误中的 `input`/`ctx`，避免回显 API Key
- 请求使用超时、禁止跟随重定向
- Gemini 使用 `x-goog-api-key` 请求头，不把 Key 拼进 URL
- `AI_REQUEST_TIMEOUT_SECONDS` 控制后端请求超时

### 部署安全提示

- 生产环境必须使用 HTTPS；否则浏览器到后端的 Key 在传输中可见
- `localStorage` 中的 Key 可被同源 XSS 读取，建议优先 sessionStorage
- AI 测试接口允许用户填写任意 http(s) Base URL，后端会向该地址发起请求。这是自定义 Provider 的必要能力，但也构成 SSRF 面；公网部署时应在 Nginx/网关层限制访问、增加认证与限流，或通过出口网络策略限制可访问地址
- 使用 Provider 会产生费用，请确认用户自己的账号额度与服务条款

### 前端页面

访问 `/settings/ai`（首页右上角“AI 设置”入口）：

- Provider、Base URL、模型、API Key 表单
- Key 默认隐藏，可切换显示
- sessionStorage / localStorage 保存位置选择
- 测试连接与脱敏错误提示
- 保存/清除本地配置
- 页面明确提示 Key 不会保存到后端

### 图片辅助核验页

访问 `/vision/verify`（首页右上角“图片核验”入口）：

- 选择 JPEG/PNG/WebP 图片，最大 10MB；本地预览，不上传原图到持久存储
- 未配置 AI Provider 时引导到 `/settings/ai`
- 上传后调用 `POST /api/v1/vision/analyze-and-match`
- 按检测到的标准显示：包装执行标准、当前状态、当前替代标准、图片可检查项
- `OBSERVED` 使用 ✓ 图标，其余显示为 ? 并说明原因（部分可见、需文档、需实验、无法测量）
- 页面底部固定显示：“图片分析只能辅助核对可见信息，不能替代实验检测、检测报告或合规认证。”

## 图片识别

### 处理流程

1. 流式读取上传文件，超过 10MB 立即返回 413
2. Pillow 校验格式和像素数，拒绝损坏文件、GIF 和 HEIC
3. 纠正 EXIF 方向，最长边缩到 2048，透明图铺白底后重新编码为 JPEG
4. 处理结果只保留在内存中，调用用户配置的 Provider
5. AI 返回后立即去掉图片引用；没有原图或处理图的磁盘写入
6. 关闭 `UploadFile`（包括 Starlette 可能使用的临时 spool 文件）

### 结构化输出

`app/schemas/vision.py` 定义了固定响应结构：

- `product.name` / `product.categoryGuess` / `product.confidence`
- `materials` / `usages`
- `visibleText`
- `visibleStandardNumbers`
- `productionDate` / `manufacturer`

`app/vision/parser.py` 支持代码块包裹和前后说明文字，但最终必须解析出 JSON 对象；解析失败返回 502，不把模型原文返回给前端。

### 标准号防猜测

Prompt 明确要求 `visibleStandardNumbers` 只能来自图片中清晰可见的内容。解析阶段还会：

1. 用 `StandardNoNormalizer` 过滤不合法的编号并规范化
2. 要求编号规范化后出现在 `visibleText` 中
3. 去重

因此模型即使根据商品类型“猜”出一个常见标准号，只要没有出现在它自己识别出的可见文字中，就会被丢弃。这是保守策略，可能偶尔丢掉 OCR 结果不完整的真实编号，但不会主动引入不可见的标准号。

### 日志与存储

- 图片内容、API Key 不写日志
- AI Provider 错误只输出通用消息；路由层还会用实际 Key 做最后一遍替换脱敏
- 不写数据库、不保存原图或压缩图
- 上传接口和测试连接接口都不需要登录，公网部署需在网关层做认证/限流，并注意自定义 Base URL 的 SSRF 面（见部署文档）

### 前端

`/vision/verify` 已提供图片选择、AI 配置检查、识别/匹配结果和逐项核验展示；`/analyze` 仍只返回结构化识别结果，`/analyze-and-match` 额外返回标准匹配与 `standardVerification`。

## 测试与构建

```bash
# 后端测试（首次先安装测试依赖）
cd backend
.venv/Scripts/python -m pip install -r requirements-dev.txt
.venv/Scripts/python -m pytest

# 后端语法/导入检查
.venv/Scripts/python -c "from app.main import app"

# 生成迁移 SQL（不需要连数据库）
.venv/Scripts/python -m alembic upgrade head --sql

# 前端类型检查 + 生产构建
cd frontend
npm run typecheck
npm run build
```

> macOS / Linux 将 `.venv/Scripts/python` 换成 `.venv/bin/python`。

> 同步相关测试使用 `httpx.MockTransport` 和假数据源，不会访问真实站点；真实适配器只做过单条记录的只读验证。

PWA 的 Service Worker 只在生产构建中启用：

```bash
cd frontend
npm run build
npm run preview   # http://127.0.0.1:4173
```

## 部署（Nginx）

1. 构建前端并上传：

```bash
cd frontend
npm ci
npm run build

sudo mkdir -p /var/www/standard-lens
sudo rsync -a --delete dist/ /var/www/standard-lens/
```

2. 后端部署到 `/opt/standard-lens/backend`，创建虚拟环境、安装依赖、配置 `.env`，执行：

```bash
cd /opt/standard-lens/backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m alembic upgrade head
```

3. 在仓库根目录安装 systemd 服务并启动：

```bash
sudo cp deploy/systemd/standard-lens-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now standard-lens-api
```

4. 在仓库根目录安装 Nginx 配置：

```bash
sudo cp deploy/nginx/standard-lens.conf /etc/nginx/conf.d/
sudo nginx -t
sudo systemctl reload nginx
```

更多部署说明见 [deploy/README.md](deploy/README.md)。

## 常见问题

**页面显示“服务已启动，数据库未连接”**

API 正常，但 MySQL 健康检查失败。依次检查：

- MySQL 8 是否在运行
- `backend/.env` 中的账号密码是否正确
- 数据库是否已创建：`python -m scripts.init_db`
- 迁移是否执行：`python -m alembic upgrade head`
- 页面上的 `database.detail` 或后端窗口日志

**页面显示“无法连接后端服务”**

- 后端是否监听 `127.0.0.1:8000`
- 直接访问 <http://127.0.0.1:8000/api/health>
- 端口被占用时，修改 `.env` 与 `vite.config.ts` 中的端口，并同步 `start-dev.bat`

**`Access denied` / `Unknown database`**

用管理员账号执行 `deploy/mysql/init.sql`，或修改 `backend/.env` 使用有权限的账号。

**端口 8000 / 5173 被占用**

Windows 查看占用：

```bat
netstat -ano | findstr :8000
tasklist /FI "PID eq <PID>"
```

**`start-dev.bat` 提示找不到 Node.js**

安装 Node.js LTS 后重新打开终端/双击脚本；安装时勾选加入 PATH。

**PWA 无法安装**

Service Worker 只在 `npm run build` 后生效；除 `localhost` 外，PWA 安装要求 HTTPS。

## 下一阶段

- 前端标准检索页（商品搜索页、标准详情页已完成）
- 商品分类关联与标准核验要求的管理/审核页面
- 同步任务管理页、失败明细与重试队列
- 分类、关键词与全文检索优化
- 标准核验要求的批量导入与原文对照
- 收藏/历史记录、部署优化与权限

这些功能在当前代码中尚未实现。
